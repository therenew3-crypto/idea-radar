"""일일 파이프라인 오케스트레이터.

흐름:
  1) Product Hunt 수집 -> 프롬프트1 분석 (미개척 아이디어 Top 5)
  2) Top 아이디어 키워드로 Reddit 수집 -> 프롬프트2 분석 (미해결 문제)
  3) Top 아이디어로 프롬프트3 분석 (경쟁사 갭)
  4) 결과를 docs/data/YYYY-MM-DD.json 으로 저장하고 index.json 갱신

GitHub Actions 가 매일 실행한다. 각 소스는 키가 없거나 실패해도
파이프라인이 멈추지 않도록 graceful 하게 처리한다.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import date
from pathlib import Path

import analyze
import collect_producthunt
import collect_reddit

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"


def _safe(label: str, fn, fallback):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — 한 소스 실패가 전체를 막지 않게
        print(f"[WARN] {label} 실패: {exc}")
        traceback.print_exc()
        return {"error": str(exc), **fallback} if isinstance(fallback, dict) else fallback


def build_report() -> dict:
    today = date.today().isoformat()
    report: dict = {"date": today, "warnings": []}

    # --- 1. Product Hunt + 프롬프트1 ---
    posts = _safe("Product Hunt 수집", lambda: collect_producthunt.fetch_top_posts(), [])
    if not posts:
        report["warnings"].append("Product Hunt 데이터를 가져오지 못했습니다 (토큰 확인).")
    ph = _safe(
        "프롬프트1 분석",
        lambda: analyze.analyze_producthunt(posts),
        {"common_themes": [], "top_ideas": []},
    )
    report["producthunt"] = {"raw_count": len(posts), "analysis": ph}

    top_ideas = ph.get("top_ideas", [])
    lead = top_ideas[0] if top_ideas else None

    # --- 2. Reddit + 프롬프트2 (1순위 아이디어 기준) ---
    # Reddit 키가 없으면 이 단계를 통째로 건너뛴다 (Claude 호출 비용도 아낌).
    reddit_enabled = bool(
        os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET")
    )
    if not reddit_enabled:
        report["warnings"].append("Reddit 키가 없어 프롬프트2(커뮤니티 분석)는 건너뜁니다.")
        report["reddit"] = None
    elif lead:
        kw = lead.get("search_keywords") or lead.get("title", "")
        reddit_raw = _safe("Reddit 수집", lambda: collect_reddit.collect(kw), {})
        reddit_analysis = _safe(
            "프롬프트2 분석",
            lambda: analyze.analyze_reddit(reddit_raw, lead.get("title", "")),
            {"communities": [], "unsolved_problems": []},
        )
        report["reddit"] = {"target_idea": lead.get("title"), "analysis": reddit_analysis}
    else:
        report["warnings"].append("분석할 1순위 아이디어가 없어 Reddit 단계를 건너뜀.")
        report["reddit"] = None

    # --- 3. 경쟁사 갭 + 프롬프트3 ---
    if lead:
        comp = _safe(
            "프롬프트3 분석",
            lambda: analyze.analyze_competitors(lead.get("title", ""), lead.get("problem", "")),
            {"competitors": [], "top_complaints": []},
        )
        report["competitors"] = {"target_idea": lead.get("title"), "analysis": comp}
    else:
        report["competitors"] = None

    return report


def write_report(report: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{report['date']}.json"
    (DATA_DIR / fname).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # index.json — 날짜 목록(최신순) 유지
    dates = sorted(
        (p.stem for p in DATA_DIR.glob("*.json") if p.name != "index.json"),
        reverse=True,
    )
    (DATA_DIR / "index.json").write_text(
        json.dumps({"dates": dates, "latest": dates[0] if dates else None}, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] {fname} 저장 완료. 총 {len(dates)}일치 데이터.")


if __name__ == "__main__":
    write_report(build_report())
