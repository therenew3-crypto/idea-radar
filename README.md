# 🚀 1인 사업 기회 리서치 대시보드

매일 자동으로 **온라인 사업 아이템을 발굴하고, 사업 판단이 가능한 수준까지 리서치**해 주는 대시보드입니다.

## 무엇을 하나요
| 단계 | 하는 일 | 소스 |
|---|---|---|
| **발굴** | Product Hunt 최근 30일 인기 서비스 분석 → 1인 개발자용 미개척 아이디어 Top 5 | Product Hunt API |
| **심층 리서치** | 각 아이디어마다 ↓ 5가지를 분석 | Claude |
| └ 📊 시장 규모 | TAM/SAM/SOM + 성장세 + 근거 | |
| └ 🎯 경쟁사 | 경쟁사별 요금제·강점·약점(=기회) | |
| └ 💰 요금제 | 업계 가격대·빈틈·우리 추천가 | |
| └ 👤 1인 창업 가능성 | 난이도·MVP기간·필요역량·수익화·해자·장단점·최대 리스크 | |
| └ ⚖️ 최종 판단 | 10점 점수 + 추천/보류 + 오늘의 첫걸음 | |

분석 두뇌는 **Claude API**, 자동 실행은 **GitHub Actions**(매일), 화면은 **정적 HTML**(GitHub Pages)입니다.

```
매일 새벽 → Product Hunt 수집 → Claude 발굴+심층분석 → docs/data/날짜.json 커밋 → 대시보드 자동 갱신
```

## ⚠️ 솔직한 한계
- **시장 규모·경쟁사·요금제는 Claude의 지식 기반 추정치**입니다. 실시간 데이터가 아니므로 의사결정 전 반드시 검증하세요. (대시보드에 `추정·검증필요` 배지로 표시)
- Product Hunt 수집만 실제 API로 정확합니다.

---

## 🔧 설치 (브라우저만으로, 약 15분)

### 1. API 키 2개 발급
| 키 | 발급처 |
|---|---|
| `PRODUCTHUNT_TOKEN` | https://www.producthunt.com/v2/oauth/applications → Developer Token |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com (소액 결제 등록 필요) |

### 2. GitHub Secrets 등록
저장소 **Settings → Secrets and variables → Actions → New repository secret** 에 위 2개를 등록.
(선택) **Variables** 탭에서 `CLAUDE_MODEL`(예: `claude-opus-4-8`), `DEEP_DIVE_COUNT`(예: `3`) 조정 가능.

### 3. 첫 실행
**Actions → "일일 사업 기회 분석" → Run workflow** 로 수동 실행하면 `docs/data/오늘날짜.json` 이 생성됩니다.
이후 매일 한국시간 오전 8시에 자동 실행됩니다.

### 4. 대시보드 켜기 (GitHub Pages)
**Settings → Pages → Source: Deploy from a branch → Branch: 현재 브랜치 / 폴더 `/docs` → Save**.
잠시 뒤 표시되는 주소가 대시보드입니다.

---

## 💻 로컬에서 테스트 (선택)
```bash
pip install -r requirements.txt
cp .env.example .env      # 값 채우기
set -a; source .env; set +a
python src/run.py         # docs/data/날짜.json 생성
python -m http.server -d docs 8000   # http://localhost:8000
```
API 키 없이 화면만 보려면, 포함된 샘플(`docs/data/2026-06-07.json`)이 그대로 렌더됩니다.

---

## 📁 구조
```
src/
  collect_producthunt.py   # Product Hunt 수집
  analyze.py               # 발굴(discover) + 심층분석(deep_dive)
  run.py                   # 파이프라인 오케스트레이터
docs/                      # GitHub Pages 정적 대시보드 (index.html / app.js / style.css)
  data/                    # 날짜별 분석 결과 JSON (자동 생성/커밋)
.github/workflows/daily.yml  # 매일 자동 실행
```

## 🛠 커스터마이즈
- **분석 깊이 vs 비용**: `CLAUDE_MODEL` = `claude-sonnet-4-6`(저렴) ↔ `claude-opus-4-8`(고품질)
- **아이디어 개수**: `DEEP_DIVE_COUNT` (기본 5) — 비용 줄이려면 3
- **수집 개수/기간**: `collect_producthunt.fetch_top_posts(days=30, limit=50)`
- **실행 시각**: `.github/workflows/daily.yml` 의 cron 수정
