"""Product Hunt 데이터 수집기.

지난 N일 동안 출시된 상위 인기 서비스를 Product Hunt 공식 GraphQL API에서 가져온다.
API 토큰 발급: https://www.producthunt.com/v2/oauth/applications

환경변수:
  PRODUCTHUNT_TOKEN  -- Developer Token (Bearer)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

PH_ENDPOINT = "https://api.producthunt.com/v2/api/graphql"

_QUERY = """
query TopPosts($postedAfter: DateTime!, $first: Int!) {
  posts(order: VOTES, postedAfter: $postedAfter, first: $first) {
    edges {
      node {
        name
        tagline
        description
        votesCount
        commentsCount
        url
        website
        topics(first: 5) { edges { node { name } } }
      }
    }
  }
}
"""


def fetch_top_posts(days: int = 30, limit: int = 50) -> list[dict]:
    """최근 `days`일 동안 출시된 상위 `limit`개 서비스를 반환한다."""
    token = os.environ.get("PRODUCTHUNT_TOKEN")
    if not token:
        raise RuntimeError(
            "PRODUCTHUNT_TOKEN 이 설정되지 않았습니다. "
            "https://www.producthunt.com/v2/oauth/applications 에서 발급하세요."
        )

    posted_after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    resp = requests.post(
        PH_ENDPOINT,
        json={"query": _QUERY, "variables": {"postedAfter": posted_after, "first": limit}},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=60,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"Product Hunt API 오류: {payload['errors']}")

    posts: list[dict] = []
    for edge in payload["data"]["posts"]["edges"]:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
        posts.append(
            {
                "name": node["name"],
                "tagline": node["tagline"],
                "description": (node.get("description") or "")[:500],
                "votes": node["votesCount"],
                "comments": node["commentsCount"],
                "url": node["url"],
                "website": node.get("website"),
                "topics": topics,
            }
        )
    return posts


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_top_posts(), ensure_ascii=False, indent=2))
