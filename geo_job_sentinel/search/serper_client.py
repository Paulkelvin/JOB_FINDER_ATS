from __future__ import annotations

import os
from typing import Dict, List

import requests


class SerperClient:
    """Minimal Serper.dev Google Search client.

    Expects SERPER_API_KEY in the environment.
    """

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")

    def search_jobs(self, query: str, num: int = 20) -> List[Dict]:
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY not configured")

        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": num}
        resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("organic", [])
