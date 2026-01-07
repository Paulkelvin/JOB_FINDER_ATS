from __future__ import annotations

from geo_job_sentinel.search.pipeline import run_full_scan
from geo_job_sentinel.discord_integration.webhook import send_job_card, send_summary


def main() -> None:
    jobs, stats = run_full_scan()

    # Limit number of individual job cards per run to avoid hitting
    # Discord webhook rate limits.
    max_cards = 15
    for job in jobs[:max_cards]:
        send_job_card(job)

    send_summary(jobs, stats)


if __name__ == "__main__":
    main()
