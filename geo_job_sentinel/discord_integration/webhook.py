from __future__ import annotations

from datetime import datetime
from typing import Iterable

import requests

from ..config_loader import load_config
from ..models import JobPosting, LocationType


def _location_type_emoji(location_type: LocationType) -> str:
    if location_type == LocationType.REMOTE:
        return "🌐 Remote"
    if location_type == LocationType.HYBRID:
        return "🏠/🏢 Hybrid"
    if location_type == LocationType.ONSITE:
        return "🏢 Onsite"
    return "❓ Unknown"


def _category_label(job: JobPosting) -> str:
    text = " ".join(
        [job.title.lower(), job.company.lower(), job.description_snippet.lower()]
    )
    url = (job.url or "").lower()

    government_markers = [" county", " city", " government", ".gov"]
    if any(m in text for m in government_markers) or any(m in url for m in [".gov", "county"]):
        return "🏛️ Government"

    return "📊 General GIS"


def _freshness_label(job: JobPosting) -> str:
    date_text = ""
    if job.raw_source:
        date_text = str(job.raw_source.get("date", "")).lower()

    if any(k in date_text for k in ["hour", "minute", "today"]):
        return "🟢 Fresh"
    if any(k in date_text for k in ["day", "yesterday"]):
        return "🔵 Standard"
    if date_text:
        return "🟠 Older"
    return "🔵 Standard"


def _competition_label(job: JobPosting) -> str:
    # Simple heuristic: remote/hybrid roles attract more applicants.
    if job.location_type in {LocationType.REMOTE, LocationType.HYBRID}:
        return "🟡 Medium (~50-100 applicants)"
    return "🟢 Low Competition (~10-30 applicants)"


def send_job_card(job: JobPosting) -> None:
    cfg = load_config()
    if not cfg.discord_webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL not configured")

    content = (
        f"**{job.title}**\n"
        f"{job.description_snippet[:280]}...\n\n"
        f"🏢 Company\n{job.company}\n"
        f"📍 Location\n{job.location}\n"
        f"🔍 Source\n{job.source}\n"
        f"📂 Category\n{_category_label(job)}\n"
        f"⏰ Freshness\n{_freshness_label(job)}\n"
        f"👥 Competition\n{_competition_label(job)}\n"
        f"🏷️ Type\n{_location_type_emoji(job.location_type)}\n\n"
        f"🔗 {job.url}"
    )

    payload = {
        "username": "GeoJob-Sentinel",
        "content": content,
    }

    resp = requests.post(cfg.discord_webhook_url, json=payload, timeout=20)
    resp.raise_for_status()


def send_summary(jobs: Iterable[JobPosting], stats: dict) -> None:
    cfg = load_config()
    if not cfg.discord_webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL not configured")

    jobs = list(jobs)
    lines = [
        "📊 **GeoJob-Sentinel Scan Summary**",
        f"New Jobs Found: **{stats.get('new_jobs', len(jobs))}**",
        f"Total Scanned: **{stats.get('total_scanned', len(jobs))}**",
        f"Duplicates Filtered: **{stats.get('duplicates_filtered', 0)}**",
    ]

    by_source = stats.get("by_source", {})
    if by_source:
        lines.append("Jobs by Source:")
        for source, count in by_source.items():
            lines.append(f"- {source}: {count}")

    payload = {
        "username": "GeoJob-Sentinel",
        "content": "\n".join(lines),
    }

    resp = requests.post(cfg.discord_webhook_url, json=payload, timeout=20)
    resp.raise_for_status()
