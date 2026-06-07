"""Reddit 데이터 수집기.

특정 문제/키워드가 논의되는 서브레딧과 인기 게시물을 Reddit 공식 API에서 가져온다.
앱 발급(script 타입): https://www.reddit.com/prefs/apps  -> client id / secret

userless OAuth(client_credentials)를 사용하므로 사용자 로그인 없이 읽기 전용 조회가 가능하다.

환경변수:
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USER_AGENT   (선택, 기본값 제공)
"""
from __future__ import annotations

import os

import requests

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"


def _user_agent() -> str:
    return os.environ.get("REDDIT_USER_AGENT", "idea-dashboard/0.1 by solo-founder")


def _get_token() -> str:
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 가 설정되지 않았습니다. "
            "https://www.reddit.com/prefs/apps 에서 script 앱을 만드세요."
        )
    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(cid, secret),
        headers={"User-Agent": _user_agent()},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "User-Agent": _user_agent()}


def find_communities(keywords: str, limit: int = 5) -> list[dict]:
    """키워드와 관련된 서브레딧 상위 `limit`개를 찾는다."""
    token = _get_token()
    resp = requests.get(
        f"{API_BASE}/api/subreddit_autocomplete_v2",
        params={"query": keywords, "limit": limit, "include_over_18": "false"},
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    out: list[dict] = []
    for child in resp.json().get("data", {}).get("children", []):
        d = child["data"]
        out.append(
            {
                "name": d.get("display_name_prefixed", "r/" + d.get("display_name", "")),
                "subscribers": d.get("subscribers"),
                "title": d.get("public_description", "")[:200],
            }
        )
    return out


def top_posts(subreddit: str, keywords: str, limit: int = 5) -> list[dict]:
    """서브레딧 내에서 키워드로 검색한 상위 추천 게시물을 가져온다."""
    token = _get_token()
    sub = subreddit.replace("r/", "").strip()
    resp = requests.get(
        f"{API_BASE}/r/{sub}/search",
        params={
            "q": keywords,
            "restrict_sr": "true",
            "sort": "top",
            "t": "year",
            "limit": limit,
        },
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    out: list[dict] = []
    for child in resp.json().get("data", {}).get("children", []):
        d = child["data"]
        out.append(
            {
                "title": d.get("title"),
                "score": d.get("score"),
                "num_comments": d.get("num_comments"),
                "selftext": (d.get("selftext") or "")[:800],
                "url": "https://reddit.com" + d.get("permalink", ""),
                "subreddit": "r/" + d.get("subreddit", sub),
            }
        )
    return out


def collect(keywords: str, n_communities: int = 5, posts_per_sub: int = 4) -> dict:
    """프롬프트2용 데이터: 커뮤니티 목록 + 각 커뮤니티의 인기 게시물."""
    communities = find_communities(keywords, limit=n_communities)
    posts: list[dict] = []
    for c in communities:
        try:
            posts.extend(top_posts(c["name"], keywords, limit=posts_per_sub))
        except requests.HTTPError:
            continue
    return {"keywords": keywords, "communities": communities, "posts": posts}


if __name__ == "__main__":
    import json
    import sys

    kw = sys.argv[1] if len(sys.argv) > 1 else "ai productivity tool"
    print(json.dumps(collect(kw), ensure_ascii=False, indent=2))
