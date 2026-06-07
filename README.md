# 🚀 1인 사업 기회 대시보드

매일 자동으로 **온라인 사업 아이템을 발굴·디벨럽**해 주는 대시보드입니다.
ChatGPT에 매번 프롬프트를 치는 대신, 아래 흐름을 자동화했습니다.

| 단계 | 하는 일 | 데이터 소스 |
|---|---|---|
| **프롬프트1** | Product Hunt 상위 50개 분석 → 문제 공통점 → 1인 개발자용 미개척 아이디어 Top 5 | Product Hunt API |
| **프롬프트2** | 1순위 아이디어가 논의되는 Reddit 커뮤니티 5곳 + 미해결 문제 요약 | Reddit API |
| **프롬프트3** | 경쟁사·요금제·불만 분석 → 파고들 빈 공간 Top 3 → 차별화 기획 | Claude 지식 기반 *(검증 필요)* |

분석 두뇌는 **Claude API**, 자동 실행은 **GitHub Actions**(매일), 화면은 **정적 HTML**(GitHub Pages)입니다.

```
매일 새벽  →  데이터 수집(Python)  →  Claude 분석  →  docs/data/날짜.json 커밋  →  대시보드 자동 갱신
```

---

## ⚠️ 솔직한 한계
- **시장 규모 / 경쟁사 / 불만**은 LLM **추정치**입니다. 실제 의사결정 전 반드시 검증하세요. (대시보드에 `검증 필요` 배지로 표시됨)
- 경쟁사 리뷰는 공식 API가 없어 완전 자동화가 안 됩니다. 후보 발굴까지만 자동이고, 실제 리뷰 확인은 수동을 권장합니다.
- Product Hunt / Reddit 단계는 실제 API로 완전 자동화됩니다.

---

## 🔧 설치 (15분)

### 1. API 키 3개 발급
| 키 | 발급처 |
|---|---|
| `PRODUCTHUNT_TOKEN` | https://www.producthunt.com/v2/oauth/applications → Developer Token |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | https://www.reddit.com/prefs/apps → **script** 타입 앱 생성 |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |

### 2. GitHub Secrets 등록
저장소 **Settings → Secrets and variables → Actions → New repository secret** 에
위 4개 값을 동일한 이름으로 등록합니다.
(선택) 모델을 바꾸려면 **Variables** 탭에 `CLAUDE_MODEL` = `claude-opus-4-8` 추가.

### 3. GitHub Pages 켜기
**Settings → Pages → Source: Deploy from a branch → Branch: `main` / 폴더 `/docs`** 선택.
잠시 뒤 `https://<유저명>.github.io/<저장소명>/` 에서 대시보드가 열립니다.

### 4. 첫 실행
**Actions → "일일 사업 기회 분석" → Run workflow** 버튼으로 수동 실행하면
`docs/data/오늘날짜.json` 이 생성되고 대시보드에 반영됩니다.
이후에는 매일 한국시간 오전 8시에 자동 실행됩니다.

---

## 💻 로컬에서 테스트
```bash
pip install -r requirements.txt
cp .env.example .env      # 값 채우기
set -a; source .env; set +a
python src/run.py         # docs/data/날짜.json 생성

# 대시보드 미리보기
python -m http.server -d docs 8000   # http://localhost:8000
```

API 키 없이 화면만 보고 싶다면, 포함된 샘플(`docs/data/2026-06-07.json`)이 그대로 렌더됩니다.

---

## 📁 구조
```
src/
  collect_producthunt.py   # 프롬프트1 데이터 수집
  collect_reddit.py        # 프롬프트2 데이터 수집
  analyze.py               # 프롬프트1~3 Claude 분석
  run.py                   # 파이프라인 오케스트레이터
docs/                      # GitHub Pages 정적 대시보드
  index.html / app.js / style.css
  data/                    # 날짜별 분석 결과 JSON (자동 생성/커밋)
.github/workflows/daily.yml  # 매일 자동 실행
```

## 🛠 커스터마이즈 힌트
- **수집 개수/기간**: `collect_producthunt.fetch_top_posts(days=30, limit=50)` 인자 조정
- **분석 깊이 vs 비용**: `CLAUDE_MODEL` 을 `claude-sonnet-4-6`(저렴) ↔ `claude-opus-4-8`(고품질)
- **2순위 이하 아이디어까지 Reddit/경쟁사 분석**: `src/run.py` 의 `lead` 처리 루프를 확장
- **실행 시각**: `.github/workflows/daily.yml` 의 cron 수정
