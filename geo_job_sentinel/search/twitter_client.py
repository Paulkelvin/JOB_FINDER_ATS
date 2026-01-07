from __future__ import annotations

from typing import Dict, List, Optional

import requests


class TwitterClient:
    """Minimal Twitter API v2 recent search client using a bearer token.

    This expects a bearer token with access to the recent search endpoint.
    """

    BASE_URL = "https://api.twitter.com/2/tweets/search/recent"

    def __init__(self, bearer_token: Optional[str]) -> None:
        if not bearer_token:
            raise RuntimeError("TWITTER_BEARER_TOKEN not configured")
        self.bearer_token = bearer_token

    def search_gis_jobs(self, query: str, max_results: int = 10) -> List[Dict]:
        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        params = {
            "query": query,
            "max_results": max(10, min(max_results, 50)),
            "tweet.fields": "created_at,public_metrics,entities",
            "expansions": "author_id",
            "user.fields": "name,username",
        }

        resp = requests.get(self.BASE_URL, headers=headers, params=params, timeout=30)

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:  # pragma: no cover
                detail = resp.text
            raise RuntimeError(f"Twitter error {resp.status_code}: {detail}")

        data = resp.json()

        tweets = data.get("data", [])
        users_index = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        # Attach author info to each tweet for downstream normalization
        for tweet in tweets:
            author = users_index.get(tweet.get("author_id"))
            if author:
                tweet["author"] = author

        return tweets
