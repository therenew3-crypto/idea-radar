"""Claude 분석 두뇌 — Product Hunt 데이터에서 사업 기회를 발굴하고,
각 기회를 '실제 사업 판단이 가능한' 수준으로 심층 리서치한다.

흐름:
  discover_ideas(posts) -> 미개척 아이디어 Top N (가벼운 1차 선별)
  deep_dive(idea)       -> 시장규모 / 경쟁사 / 요금제 / 1인창업 가능성 / 최종판단

API 키 발급: https://console.anthropic.com

환경변수:
  ANTHROPIC_API_KEY
  CLAUDE_MODEL   (선택, 기본 claude-sonnet-4-6. 더 깊은 분석은 claude-opus-4-8)
"""
from __future__ import annotations

import json
import os

import anthropic

# 환경변수가 비어 있어도(예: GitHub Actions의 미설정 variable -> "") 기본 모델로 대체.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"


def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY 가 설정되지 않았습니다. https://console.anthropic.com 에서 발급하세요."
        )
    return anthropic.Anthropic()


def _ask_json(system: str, user: str, max_tokens: int = 4500) -> dict:
    """Claude에게 JSON만 반환하도록 요청하고 파싱한다."""
    client = _client()
    msg = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")
    return json.loads(text)


# ---------------------------------------------------------------------------
# 1차 선별 — Product Hunt 기회 발굴
# ---------------------------------------------------------------------------
DISCOVER_SYSTEM = (
    "당신은 한국 시장을 잘 아는 1인 창업 전략가다. "
    "주어진 Product Hunt 데이터를 분석해, 1인 개발자가 도전할 만한 '미개척 기회'를 선별한다. "
    "반드시 유효한 JSON 객체 하나만 출력한다. 그 외 설명 텍스트는 금지."
)


def discover_ideas(posts: list[dict], n: int = 5) -> dict:
    user = f"""다음은 지난 30일간 Product Hunt 상위 서비스 데이터(JSON)다:

{json.dumps(posts, ensure_ascii=False)}

작업:
1. 각 서비스가 해결하려는 '문제'를 추출하고 공통 테마(클러스터)를 찾아라.
2. 한국 온라인 시장 기준으로, 1인 개발자가 구축할 만한 '미개척 서비스' 상위 {n}개를 순위로 골라라.

아래 JSON 스키마로만 답하라:
{{
  "common_themes": ["공통 테마 문장", ...],
  "top_ideas": [
    {{
      "rank": 1,
      "title": "아이디어 이름",
      "problem": "해결하는 문제 한 문장",
      "category": "카테고리(예: 생산성, 마케팅, 커머스)",
      "why_now": "왜 지금 기회인지 한 문장"
    }}
  ]
}}
정확히 {n}개의 아이디어를 포함하라."""
    return _ask_json(DISCOVER_SYSTEM, user, max_tokens=2500)


# ---------------------------------------------------------------------------
# 심층 리서치 — 사업 판단용 리포트
# ---------------------------------------------------------------------------
DEEPDIVE_SYSTEM = (
    "당신은 1인 창업가를 위한 냉정하고 현실적인 사업 분석가다. "
    "주어진 아이디어 하나에 대해 시장규모, 경쟁사, 요금제, 1인 창업 가능성, 최종 사업판단을 작성한다. "
    "중요: 너는 실시간 시장/리뷰 데이터에 접근할 수 없다. 따라서 시장규모와 경쟁사 정보는 "
    "네 지식 기반의 '추정치'이며 반드시 사용자가 검증해야 한다. 장밋빛 전망 대신 현실적 리스크를 "
    "솔직하게 지적하라. 반드시 유효한 JSON 객체 하나만 출력한다."
)


def deep_dive(idea: dict) -> dict:
    title = idea.get("title", "")
    problem = idea.get("problem", "")
    category = idea.get("category", "")
    user = f"""분석 대상 아이디어:
- 이름: {title}
- 해결 문제: {problem}
- 카테고리: {category}

이 아이디어를 한국 1인 창업가 관점에서 사업 판단이 가능하도록 심층 분석하라.
아래 JSON 스키마로만 답하라(모든 수치는 추정치임을 전제):

{{
  "title": "{title}",
  "one_liner": "이 서비스를 한 줄로 설명",
  "market": {{
    "tam": "전체 시장(추정, 숫자+근거)",
    "sam": "유효 시장(추정)",
    "som": "현실적으로 1인이 노릴 초기 시장(추정)",
    "growth_trend": "성장세 (상승/정체/하락 + 이유)",
    "reasoning": "이 추정의 근거 2~3문장",
    "needs_verification": true
  }},
  "competitors": [
    {{
      "name": "경쟁사명",
      "pricing": "요금제(추정)",
      "strengths": "강점",
      "weaknesses": "약점(=우리의 기회)"
    }}
  ],
  "pricing_analysis": {{
    "common_models": ["업계의 흔한 과금 방식", ...],
    "price_range": "경쟁사 가격대 요약",
    "gap": "가격/패키징의 빈틈",
    "our_suggested_pricing": "우리가 제안할 요금제(근거 포함)"
  }},
  "solo_founder": {{
    "build_difficulty": "쉬움|보통|어려움",
    "time_to_mvp": "MVP까지 예상 기간(예: 2~4주)",
    "required_skills": ["필요 역량", ...],
    "monetization": "어떻게 돈을 버는가",
    "moat": "방어 가능한 차별점(해자)",
    "pros": ["1인 창업가에게 유리한 점", ...],
    "cons": ["불리하거나 어려운 점", ...],
    "biggest_risk": "가장 큰 리스크 한 가지"
  }},
  "verdict": {{
    "score": 7,
    "recommendation": "추천|조건부 추천|보류",
    "summary": "최종 사업 판단 한 문단",
    "first_step": "오늘 당장 검증해볼 첫 행동"
  }}
}}

competitors는 3~5개. score는 1~10 정수(1인 창업 매력도). 냉정하게 평가하라."""
    return _ask_json(DEEPDIVE_SYSTEM, user, max_tokens=4500)
