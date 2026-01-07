from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Tuple

from ..config_loader import load_config
from ..models import JobPosting, classify_location_type
from ..query_builder import build_boolean_query
from .serper_client import SerperClient


def normalize_result(item: dict, source: str) -> JobPosting:
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
        location_type=location_type,
        raw_source=item,
    )


def run_gis_scan() -> Tuple[List[JobPosting], dict]:
    """Run a GIS-focused scan across configured ATS domains.

    Returns a list of JobPosting and a small stats dict.
    """

    cfg = load_config()
    query_cfg = cfg.base_queries.get("gis_default", {})
    title_keywords: Iterable[str] = query_cfg.get("title_keywords", [])

    boolean_query = build_boolean_query(cfg.ats_domains, list(title_keywords))

    client = SerperClient(api_key=cfg.serper_api_key)
    raw_results = client.search_jobs(boolean_query, num=50)

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
