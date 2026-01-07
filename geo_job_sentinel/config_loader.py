from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class AppConfig:
    discord_webhook_url: str
    discord_bot_token: str | None
    search_provider: str
    serper_api_key: str | None
    google_cse_id: str | None
    database_url: str
    ats_domains: List[str]
    base_queries: dict
    company_seeds: List[str]


def load_config() -> AppConfig:
    load_dotenv(BASE_DIR / ".env")

    ats_path = os.getenv("ATS_DOMAINS_CONFIG", "config/ats_domains.json")
    base_queries_path = os.getenv("BASE_QUERY_CONFIG", "config/base_queries.json")
    company_seeds_path = os.getenv("COMPANY_SEEDS_CONFIG", "config/company_seeds.json")

    with open(BASE_DIR / ats_path, "r", encoding="utf-8") as f:
        ats_domains = json.load(f)

    with open(BASE_DIR / base_queries_path, "r", encoding="utf-8") as f:
        base_queries = json.load(f)

    try:
        with open(BASE_DIR / company_seeds_path, "r", encoding="utf-8") as f:
            company_seeds = json.load(f)
    except FileNotFoundError:
        company_seeds = []

    return AppConfig(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN"),
        search_provider=os.getenv("SEARCH_PROVIDER", "serper"),
        serper_api_key=os.getenv("SERPER_API_KEY"),
        google_cse_id=os.getenv("GOOGLE_CSE_ID"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///jobs.sqlite3"),
        ats_domains=ats_domains,
        base_queries=base_queries,
        company_seeds=company_seeds,
    )
