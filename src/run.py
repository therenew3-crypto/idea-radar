"""일일 파이프라인 오케스트레이터.

흐름:
  1) Product Hunt 수집
  2) 미개척 아이디어 Top N 발굴 (1차 선별)
  3) 각 아이디어를 심층 리서치 (시장규모/경쟁사/요금제/1인창업 가능성/최종판단)
  4) 결과를 docs/data/YYYY-MM-DD.json 으로 저장하고 index.json 갱신

GitHub Actions 가 매일 실행한다. 각 단계는 일부 실패해도 파이프라인이 멈추지 않도록
graceful 하게 처리한다.

환경변수:
  DEEP_DIVE_COUNT  심층 분석할 아이디어 개수 (기본 5). 비용을 줄이려면 3 등으로.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import analyze
import collect_producthunt

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"
DEEP_DIVE_COUNT = int(os.environ.get("DEEP_DIVE_COUNT") or "5")
KST = timezone(timedelta(hours=9))


def _safe(label: str, fn, fallback):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — 한 단계 실패가 전체를 막지 않게
        print(f"[WARN] {label} 실패: {exc}")
        traceback.print_exc()
        if isinstance(fallback, dict):
            return {"error": str(exc), **fallback}
        return fallback


def _norm(title: str) -> str:
    """제목 정규화 — 공백/기호/대소문자 무시하고 비교용 키 생성."""
    return "".join(ch for ch in title.lower() if ch.isalnum())


def _seen_ideas(limit: int = 300) -> list[dict]:
    """과거 모든 스냅샷에서 제안된 아이디어(제목·문제)를 모은다. 중복 제외용."""
    seen: dict[str, dict] = {}  # norm-title -> {title, problem}
    # 최신 파일부터 (이름 역순) 스캔
    for p in sorted(DATA_DIR.glob("*.json"), reverse=True):
        if p.name == "index.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if d.get("sample"):  # 샘플 데이터는 제외
            continue
        for idea in d.get("ideas", []):
            title = (idea.get("title") or "").strip()
            if not title:
                continue
            seen.setdefault(_norm(title), {"title": title, "problem": (idea.get("problem") or "").strip()})
        if len(seen) >= limit:
            break
    return list(seen.values())[:limit]


def build_report() -> dict:
    now = datetime.now(timezone.utc)
    now_kst = now.astimezone(KST)
    report: dict = {
        # 매 실행마다 고유 id(UTC 타임스탬프) -> 같은 날 여러 번 돌려도 덮어쓰지 않고 누적
        "id": now.strftime("%Y%m%dT%H%M%SZ"),
        "generated_at": now.isoformat(),
        "date": now_kst.date().isoformat(),       # 한국 날짜
        "label": now_kst.strftime("%Y-%m-%d %H:%M"),  # 드롭다운 표시용 (KST)
        "warnings": [],
        "common_themes": [],
        "ideas": [],
    }

    # --- 1. Product Hunt 수집 ---
    posts = _safe("Product Hunt 수집", lambda: collect_producthunt.fetch_top_posts(), [])
    if not posts:
        report["warnings"].append("Product Hunt 데이터를 가져오지 못했습니다 (토큰 확인).")
    report["producthunt"] = {"raw_count": len(posts)}

    # --- 2. 아이디어 발굴 (과거 제안과 중복 제외) ---
    seen = _seen_ideas()
    print(f"[INFO] 과거 누적 아이디어 {len(seen)}개를 중복 제외 목록으로 전달")
    discovered = _safe(
        "아이디어 발굴",
        lambda: analyze.discover_ideas(posts, n=DEEP_DIVE_COUNT, seen=seen),
        {"common_themes": [], "top_ideas": []},
    )
    report["common_themes"] = discovered.get("common_themes", [])
    top_ideas = discovered.get("top_ideas", [])

    # 안전망: 과거 제목과 정확히/거의 같은 것은 한 번 더 걸러낸다
    seen_norm = {_norm(s.get("title", "")) for s in seen}
    fresh = [i for i in top_ideas if _norm(i.get("title", "")) not in seen_norm]
    dropped = len(top_ideas) - len(fresh)
    if dropped:
        report["warnings"].append(f"중복 아이디어 {dropped}개를 제외했습니다.")
    top_ideas = fresh

    if not top_ideas:
        report["warnings"].append("새로운 아이디어를 발굴하지 못했습니다 (Anthropic 키/모델 확인 또는 소재 고갈).")
        return report

    # --- 3. 각 아이디어 심층 리서치 ---
    for idea in top_ideas[:DEEP_DIVE_COUNT]:
        deep = _safe(
            f"심층분석: {idea.get('title','?')}",
            lambda i=idea: analyze.deep_dive(i),
            {},
        )
        # 발굴 단계의 메타데이터를 보존
        deep.setdefault("rank", idea.get("rank"))
        deep.setdefault("title", idea.get("title"))
        deep.setdefault("problem", idea.get("problem"))
        deep.setdefault("category", idea.get("category"))
        report["ideas"].append(deep)

    return report


def _rebuild_index() -> list[dict]:
    """data 폴더의 모든 스냅샷을 스캔해 최신순 목록(index.json)을 만든다."""
    entries: list[dict] = []
    for p in DATA_DIR.glob("*.json"):
        if p.name == "index.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        entries.append(
            {
                "id": p.stem,
                "label": d.get("label") or p.stem,
                "date": d.get("date") or p.stem[:10],
                "generated_at": d.get("generated_at") or "",
                "idea_count": len(d.get("ideas", [])),
            }
        )
    # generated_at(없으면 id) 기준 최신순
    entries.sort(key=lambda e: (e["generated_at"] or e["id"]), reverse=True)
    return entries


def write_report(report: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{report['id']}.json"  # 타임스탬프 기반 -> 누적 저장(덮어쓰지 않음)
    (DATA_DIR / fname).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    entries = _rebuild_index()
    (DATA_DIR / "index.json").write_text(
        json.dumps(
            {"entries": entries, "latest": entries[0]["id"] if entries else None},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[OK] {fname} 저장. 아이디어 {len(report.get('ideas', []))}개, 누적 스냅샷 {len(entries)}개.")


if __name__ == "__main__":
    write_report(build_report())
