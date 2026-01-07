from __future__ import annotations

from typing import Iterable, List


def build_boolean_query(ats_domains: Iterable[str], title_keywords: List[str]) -> str:
    """Build a Google-style Boolean query combining ATS domains and title keywords.

    Example output:
    (site:jobs.lever.co OR site:jobs.greenhouse.io) AND ("GIS Analyst" OR "Geospatial Analyst")
    """

    domains_clause = " OR ".join(f"site:{d}" for d in ats_domains)
    titles_clause = " OR ".join(title_keywords)

    return f"({domains_clause}) AND ({titles_clause})"
