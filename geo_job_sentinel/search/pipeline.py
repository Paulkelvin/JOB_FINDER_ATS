from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Tuple

from ..config_loader import load_config
from ..models import JobPosting, classify_location_type
from ..query_builder import build_boolean_query
from .serper_client import SerperClient


def normalize_result(item: dict, source: str, is_new_company: bool = False) -> JobPosting:
    title = item.get("title") or "Unknown title"
    snippet = item.get("snippet") or ""
    url = item.get("link") or item.get("url") or ""
    # Serper sometimes exposes rich results fields
    company = item.get("source") or "Unknown Company"
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
        '"GIS" OR "Geospatial" OR "Remote Sensing" '
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


def run_full_scan() -> Tuple[List[JobPosting], dict]:
    """Combine ATS-based GIS scan with discovery mode into one run."""

    ats_jobs, ats_stats = run_gis_scan()
    discovery_jobs, discovery_stats = run_discovery_scan()

    all_jobs = ats_jobs + discovery_jobs

    total_scanned = ats_stats.get("total_scanned", 0) + discovery_stats.get(
        "total_scanned", 0
    )
    duplicates_filtered = ats_stats.get("duplicates_filtered", 0) + discovery_stats.get(
        "duplicates_filtered", 0
    )

    by_source = ats_stats.get("by_source", {}).copy()
    for src, count in discovery_stats.get("by_source", {}).items():
        by_source[src] = by_source.get(src, 0) + count

    stats = {
        "new_jobs": len(all_jobs),
        "total_scanned": total_scanned,
        "duplicates_filtered": duplicates_filtered,
        "by_source": by_source,
    }

    return all_jobs, stats
