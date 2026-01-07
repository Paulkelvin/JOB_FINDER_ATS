from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class LocationType(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


@dataclass
class JobPosting:
    id: str
    title: str
    company: str
    location: str
    source: str
    url: str
    description_snippet: str
    category: str = "General GIS"
    is_new_company: bool = False
    location_type: LocationType = LocationType.UNKNOWN
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    raw_source: Optional[dict] = None


def classify_location_type(title: str, description: str, location: str) -> LocationType:
    text = " ".join([title or "", description or "", location or ""]).lower()

    remote_markers = ["remote", "work from home", "wfh", "anywhere", "distributed"]
    hybrid_markers = ["hybrid", "flexible", "part-remote", "part time remote"]
    onsite_markers = ["onsite", "on-site", "on site", "office-based"]

    if any(m in text for m in remote_markers):
        if any(m in text for m in hybrid_markers):
            return LocationType.HYBRID
        return LocationType.REMOTE

    if any(m in text for m in hybrid_markers):
        return LocationType.HYBRID

    if any(m in text for m in onsite_markers):
        return LocationType.ONSITE

    # Heuristic: if there is a clear city/state but no remote markers, assume onsite
    if "," in location and "remote" not in location.lower():
        return LocationType.ONSITE

    return LocationType.UNKNOWN
