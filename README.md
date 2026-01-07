# GeoJob-Sentinel

Automated GIS job scanner that searches ATS platforms using Google/Serper, classifies roles (remote/hybrid/onsite), and sends job cards + daily summaries to Discord.

## Quick start

1. Create a .env from .env.example and fill in:
   - DISCORD_WEBHOOK_URL (incoming webhook for job cards + summaries)
   - DISCORD_BOT_TOKEN (for the command bot)
   - SERPER_API_KEY (recommended search provider)
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run a one-off scan and send cards + summary:
   - `python -m scripts.run_scan_once`
4. Run the Discord bot for dynamic config (in another process):
   - `python -m scripts.run_bot`
   - Commands (prefix `!geo `) include:
     - `!geo add_ats jobs.exampleats.com`
     - `!geo list_ats`
     - `!geo add_keyword GIS Engineer`
     - `!geo list_keywords`
     - `!geo scan_now`
5. Run the daily scheduler (Railway-friendly long-running process):
   - `python -m scripts.run_scheduler`
   - Uses DAILY_SUMMARY_HOUR_UTC from .env (default 18) for one daily GIS scan.

### Railway

On Railway you can:

- Create a service with the start command `python -m scripts.run_scheduler` for daily scans.
- Optionally add another service for the Discord bot with `python -m scripts.run_bot`.

