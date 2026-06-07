"""Claude API 분석 두뇌 — 프롬프트 1~3을 구조화된 JSON 출력으로 구현한다.

API 키 발급: https://console.anthropic.com

환경변수:
  ANTHROPIC_API_KEY
  CLAUDE_MODEL   (선택, 기본 claude-sonnet-4-6 — 일일 실행 비용 절감용.
                  더 깊은 분석을 원하면 claude-opus-4-8 로 변경)
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


def _ask_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    """Claude에게 JSON만 반환하도록 요청하고 파싱한다."""
    client = _client()
    msg = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text").strip()
    # 코드펜스 제거
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")
    return json.loads(text)


# ---------------------------------------------------------------------------
# 프롬프트 1 — Product Hunt 기회 분석
# ---------------------------------------------------------------------------
PROMPT1_SYSTEM = (
    "당신은 한국 시장을 잘 아는 1인 창업 전략가다. "
    "주어진 Product Hunt 데이터를 분석해 1인 개발자가 만들 수 있는 미개척 기회를 찾는다. "
    "반드시 유효한 JSON 객체 하나만 출력한다. 그 외 설명 텍스트는 금지."
)


def analyze_producthunt(posts: list[dict]) -> dict:
    user = f"""다음은 지난 30일간 Product Hunt 상위 서비스 데이터(JSON)다:

{json.dumps(posts, ensure_ascii=False)}

작업:
1. 각 서비스가 해결하려는 '문제'를 추출하라.
2. 문제들의 공통 테마(클러스터)를 찾아라.
3. 한국 온라인 시장 기준으로, 1인 개발자가 구축하기 쉬운 '미개척 서비스' 상위 5개를 순위로 제시하라.

아래 JSON 스키마로만 답하라:
{{
  "common_themes": ["공통 테마 문장", ...],
  "top_ideas": [
    {{
      "rank": 1,
      "title": "아이디어 이름",
      "problem": "해결하는 문제 한 문장",
      "why_untapped": "왜 미개척인지",
      "market_size_estimate": "시장 규모 추정 (한국 기준, 추정치임을 명시)",
      "solo_dev_difficulty": "쉬움|보통|어려움",
      "search_keywords": "이 문제를 Reddit에서 검색할 영어 키워드"
    }}
  ]
}}
정확히 5개의 아이디어를 포함하라. market_size_estimate는 LLM 추정치다."""
    return _ask_json(PROMPT1_SYSTEM, user)


# ---------------------------------------------------------------------------
# 프롬프트 2 — Reddit 미해결 문제 요약
# ---------------------------------------------------------------------------
PROMPT2_SYSTEM = (
    "당신은 사용자 리서치 분석가다. Reddit 게시물에서 사람들이 여전히 해결하지 못한 "
    "진짜 페인포인트를 추출한다. 유효한 JSON 객체 하나만 출력한다."
)


def analyze_reddit(reddit_data: dict, idea_title: str) -> dict:
    user = f"""아이디어: "{idea_title}"

다음은 관련 Reddit 커뮤니티와 인기 게시물 데이터(JSON)다:

{json.dumps(reddit_data, ensure_ascii=False)}

작업: 사람들이 어떤 문제를 '해결하지 못하고' 있는지 요약하라.

아래 JSON 스키마로만 답하라:
{{
  "communities": [{{"name": "r/...", "why_relevant": "관련 이유"}}],
  "unsolved_problems": ["미해결 문제 요약 문장", ...],
  "frequent_complaints": ["자주 나오는 불만", ...],
  "opportunity_signal": "여기서 보이는 기회 한 문장"
}}"""
    return _ask_json(PROMPT2_SYSTEM, user)


# ---------------------------------------------------------------------------
# 프롬프트 3 — 경쟁사 갭 분석
# ---------------------------------------------------------------------------
PROMPT3_SYSTEM = (
    "당신은 경쟁 분석 전문가다. 주어진 아이디어 영역의 기존 경쟁사, 요금제, 사용자 불만을 "
    "분석해 '파고들 수 있는 빈 공간'을 찾는다. "
    "주의: 너는 실시간 리뷰 데이터에 접근할 수 없으므로 네 지식 기반 추정임을 명시하고, "
    "각 항목에 'needs_verification: true' 를 둔다. 유효한 JSON 객체 하나만 출력한다."
)


def analyze_competitors(idea_title: str, problem: str) -> dict:
    user = f"""아이디어: "{idea_title}"
해결 문제: {problem}

작업:
1. 주요 경쟁사 3~5곳과 대략적 요금제를 제시하라.
2. 사용자들이 자주 제기하는 가장 큰 불만 3가지를 추정하라.
3. 그 불만(=빈 공간)을 메우는 우리 서비스 차별화 기획을 제안하라.

아래 JSON 스키마로만 답하라:
{{
  "competitors": [
    {{"name": "경쟁사", "pricing": "요금제 추정", "positioning": "포지셔닝"}}
  ],
  "top_complaints": [
    {{"complaint": "가장 큰 불만", "gap": "여기서 생기는 빈 공간"}}
  ],
  "our_wedge": "우리가 파고들 차별화 기획 한 문단",
  "needs_verification": true
}}
top_complaints는 정확히 3개. 모두 추정치이며 실제 리뷰로 검증이 필요하다."""
    return _ask_json(PROMPT3_SYSTEM, user)
