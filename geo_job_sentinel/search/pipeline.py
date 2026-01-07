from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Tuple

from ..config_loader import load_config
from ..models import JobPosting, classify_location_type
from ..query_builder import build_boolean_query
from .serper_client import SerperClient
from .twitter_client import TwitterClient


def normalize_result(item: dict, source: str, is_new_company: bool = False) -> JobPosting:
    title = item.get("title") or "Unknown title"
    snippet = item.get("snippet") or ""
    url = item.get("link") or item.get("url") or ""
    # Serper or other sources sometimes expose rich results fields
    company = item.get("source") or item.get("company") or "Unknown Company"
    location = item.get("location") or item.get("city") or "Unknown"

    location_type = classify_location_type(title, snippet, location)

    return JobPosting(
        id=url or f"{title}-{datetime.utcnow().isoformat()}",
        title=title,
        company=company,
        location=location,
        source=source,
        url=url,
        description_snippet=snippet,
        is_new_company=is_new_company,
        location_type=location_type,
        raw_source=item,
    )


def run_gis_scan() -> Tuple[List[JobPosting], dict]:
    """Run a GIS-focused scan across configured ATS domains only."""

    cfg = load_config()
    query_cfg = cfg.base_queries.get("gis_default", {})
    title_keywords: Iterable[str] = query_cfg.get("title_keywords", [])

    boolean_query = build_boolean_query(cfg.ats_domains, list(title_keywords))

    client = SerperClient(api_key=cfg.serper_api_key)
    raw_results = client.search_jobs(boolean_query, num=10)

    jobs: List[JobPosting] = []
    seen_ids: set[str] = set()

    for item in raw_results:
        job = normalize_result(item, source="Serper/Google")
        if job.id in seen_ids:
            continue
        seen_ids.add(job.id)
        jobs.append(job)

    stats = {
        "new_jobs": len(jobs),
        "total_scanned": len(raw_results),
        "duplicates_filtered": len(raw_results) - len(jobs),
        "by_source": {"Serper/Google": len(jobs)},
    }

    return jobs, stats


def run_discovery_scan() -> Tuple[List[JobPosting], dict]:
    """Broader "discovery" scan to surface new / unknown companies.

    This intentionally does *not* restrict to ATS domains; it searches the
    wider web for GIS-related hiring pages and flags results as new companies.
    """

    cfg = load_config()

    discovery_query = (
        '"GIS" OR "Geospatial" OR "Remote Sensing" OR "spatial data" '
        '"we are hiring" OR "we\'re hiring" OR "careers" OR "join our team"'
    )

    client = SerperClient(api_key=cfg.serper_api_key)
    raw_results = client.search_jobs(discovery_query, num=10)

    jobs: List[JobPosting] = []
    seen_ids: set[str] = set()

    for item in raw_results:
        job = normalize_result(item, source="Discovery/Serper", is_new_company=True)
        if job.id in seen_ids:
            continue
        seen_ids.add(job.id)
        jobs.append(job)

    stats = {
        "new_jobs": len(jobs),
        "total_scanned": len(raw_results),
        "duplicates_filtered": len(raw_results) - len(jobs),
        "by_source": {"Discovery/Serper": len(jobs)},
    }

    return jobs, stats


def run_company_seed_scan() -> Tuple[List[JobPosting], dict]:
    """Scan specific company domains seeded from config/company_seeds.json.

    This lets you feed in domains from startup lists, GIS communities, etc.
    """

    cfg = load_config()
    if not cfg.company_seeds:
        return [], {"new_jobs": 0, "total_scanned": 0, "duplicates_filtered": 0, "by_source": {}}

    client = SerperClient(api_key=cfg.serper_api_key)

    jobs: List[JobPosting] = []
    seen_ids: set[str] = set()
    total_scanned = 0

    for domain in cfg.company_seeds:
        domain = domain.strip()
        if not domain:
            continue

        query = (
            f'"GIS" OR "Geospatial" OR "Remote Sensing" OR "spatial" '
            f'site:{domain}'
        )

        raw_results = client.search_jobs(query, num=5)
        total_scanned += len(raw_results)

        for item in raw_results:
            job = normalize_result(
                item,
                source="Discovery/SeedCompanies",
                is_new_company=True,
            )
            if job.id in seen_ids:
                continue
            seen_ids.add(job.id)
            jobs.append(job)

    stats = {
        "new_jobs": len(jobs),
        "total_scanned": total_scanned,
        "duplicates_filtered": total_scanned - len(jobs),
        "by_source": {"Discovery/SeedCompanies": len(jobs)},
    }

    return jobs, stats


def run_twitter_scan() -> Tuple[List[JobPosting], dict]:
    """Scan X (Twitter) for GIS job-related tweets.

    Uses the recent search endpoint with GIS keywords and hiring language.
    """

    cfg = load_config()
    if not cfg.twitter_bearer_token:
        return [], {"new_jobs": 0, "total_scanned": 0, "duplicates_filtered": 0, "by_source": {}}

    client = TwitterClient(bearer_token=cfg.twitter_bearer_token)

    query = (
        "(GIS OR geospatial OR \"geographic information systems\" OR \"remote sensing\" "
        "OR \"spatial data\") (hiring OR \"we're hiring\" OR job OR jobs OR role) "
        "-is:retweet -is:reply lang:en"
    )

    raw_tweets = client.search_gis_jobs(query, max_results=20)

    jobs: List[JobPosting] = []
    seen_ids: set[str] = set()

    for tweet in raw_tweets:
        text = tweet.get("text", "")
        author = tweet.get("author", {}) or {}
        company = author.get("name") or author.get("username") or "Unknown Company"

        # Try to pull a URL from entities if present
        url = ""
        entities = tweet.get("entities") or {}
        urls = entities.get("urls") or []
        if urls:
            url = urls[0].get("expanded_url") or urls[0].get("url") or ""

        job_dict = {
            "title": text.split("\n")[0][:120] or "GIS-related tweet",
            "snippet": text,
            "link": url or f"https://twitter.com/{author.get('username', '')}/status/{tweet.get('id')}",
            "company": company,
            "location": "Unknown",
        }

        job = normalize_result(job_dict, source="Twitter", is_new_company=True)
        if job.id in seen_ids:
            continue
        seen_ids.add(job.id)
        jobs.append(job)

    stats = {
        "new_jobs": len(jobs),
        "total_scanned": len(raw_tweets),
        "duplicates_filtered": len(raw_tweets) - len(jobs),
        "by_source": {"Twitter": len(jobs)},
    }

    return jobs, stats


def run_full_scan() -> Tuple[List[JobPosting], dict]:
    """Combine ATS-based scan, broad discovery, seed-company scan, and Twitter."""

    ats_jobs, ats_stats = run_gis_scan()
    discovery_jobs, discovery_stats = run_discovery_scan()
    seed_jobs, seed_stats = run_company_seed_scan()
    twitter_jobs, twitter_stats = run_twitter_scan()

    all_jobs = ats_jobs + discovery_jobs + seed_jobs + twitter_jobs

    # Cross-source deduplication by URL (or id fallback).
    unique_jobs: List[JobPosting] = []
    seen_keys: set[str] = set()
    for job in all_jobs:
        key = job.url or job.id
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_jobs.append(job)

    total_scanned = (
        ats_stats.get("total_scanned", 0)
        + discovery_stats.get("total_scanned", 0)
        + seed_stats.get("total_scanned", 0)
        + twitter_stats.get("total_scanned", 0)
    )
    duplicates_filtered = total_scanned - len(unique_jobs)

    by_source = ats_stats.get("by_source", {}).copy()
    for stats in (discovery_stats, seed_stats, twitter_stats):
        for src, count in stats.get("by_source", {}).items():
            by_source[src] = by_source.get(src, 0) + count

    stats = {
        "new_jobs": len(unique_jobs),
        "total_scanned": total_scanned,
        "duplicates_filtered": duplicates_filtered,
        "by_source": by_source,
    }

    return unique_jobs, stats
