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
        # Use a conservative number of results for reliability
        payload = {"q": query, "num": min(max(num, 1), 10)}
        resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)

        if resp.status_code >= 400:
            # Surface Serper error details so we can debug in logs
            try:
                detail = resp.json()
            except Exception:  # pragma: no cover - best-effort logging
                detail = resp.text
            raise RuntimeError(f"Serper error {resp.status_code}: {detail}")

        data = resp.json()
        return data.get("organic", [])
