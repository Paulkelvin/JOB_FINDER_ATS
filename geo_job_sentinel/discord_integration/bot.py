from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import List

import discord
from discord.ext import commands

from ..config_loader import BASE_DIR, load_config
from ..search.pipeline import run_gis_scan
from .webhook import send_job_card, send_summary


def _config_paths() -> tuple[Path, Path]:
    ats_path = os.getenv("ATS_DOMAINS_CONFIG", "config/ats_domains.json")
    base_queries_path = os.getenv("BASE_QUERY_CONFIG", "config/base_queries.json")
    return BASE_DIR / ats_path, BASE_DIR / base_queries_path


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!geo ", intents=intents, help_command=None)

    ats_path, base_queries_path = _config_paths()

    @bot.command(name="add_ats")
    @commands.has_permissions(administrator=True)
    async def add_ats(ctx: commands.Context, domain: str):
        """Add a new ATS domain (e.g. jobs.exampleats.com)."""

        domain = domain.strip()
        ats_list: List[str] = _load_json(ats_path)
        if domain in ats_list:
            await ctx.reply(f"`{domain}` is already in the ATS list.")
            return

        ats_list.append(domain)
        _save_json(ats_path, ats_list)
        await ctx.reply(f"Added new ATS domain: `{domain}` (total {len(ats_list)})")

    @bot.command(name="list_ats")
    async def list_ats(ctx: commands.Context):
        ats_list: List[str] = _load_json(ats_path)
        preview = ", ".join(ats_list[:20])
        more = "" if len(ats_list) <= 20 else f" … (+{len(ats_list)-20} more)"
        await ctx.reply(f"Configured ATS domains ({len(ats_list)}): {preview}{more}")

    @bot.command(name="add_keyword")
    @commands.has_permissions(administrator=True)
    async def add_keyword(ctx: commands.Context, *, keyword: str):
        """Add a new GIS title keyword to the default search stack."""

        base_queries = _load_json(base_queries_path)
        cfg = base_queries.setdefault("gis_default", {})
        titles: List[str] = cfg.setdefault("title_keywords", [])

        # Ensure quotes for Boolean search
        if not (keyword.startswith("\"") and keyword.endswith("\"")):
            display = keyword
            keyword = f"\"{keyword}\""
        else:
            display = keyword.strip("\"")

        if keyword in titles:
            await ctx.reply(f"Keyword `{display}` already exists.")
            return

        titles.append(keyword)
        _save_json(base_queries_path, base_queries)
        await ctx.reply(f"Added keyword `{display}`. Total title keywords: {len(titles)}")

    @bot.command(name="list_keywords")
    async def list_keywords(ctx: commands.Context):
        base_queries = _load_json(base_queries_path)
        titles: List[str] = base_queries.get("gis_default", {}).get("title_keywords", [])
        await ctx.reply("Current GIS title keywords:\n" + "\n".join(titles))

    @bot.command(name="scan_now")
    @commands.has_permissions(administrator=True)
    async def scan_now(ctx: commands.Context):
        """Trigger an immediate GIS scan and send cards + summary."""

        await ctx.reply("Starting on-demand GIS scan… this may take a minute.")

        loop = asyncio.get_running_loop()
        jobs, stats = await loop.run_in_executor(None, run_gis_scan)

        for job in jobs:
            # Use webhook formatting for consistency
            send_job_card(job)

        send_summary(jobs, stats)

        await ctx.reply(f"Scan complete. Found {stats.get('new_jobs', len(jobs))} jobs.")

    @bot.command(name="config")
    async def show_config(ctx: commands.Context):
        cfg = load_config()
        await ctx.reply(
            "Current config:\n"
            f"Search provider: {cfg.search_provider}\n"
            f"ATS domains: {len(cfg.ats_domains)} configured\n"
            f"Database URL: {cfg.database_url}"
        )

    return bot


def run_bot() -> None:
    cfg = load_config()
    token = cfg.discord_bot_token
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN not configured")

    bot = create_bot()
    bot.run(token)


if __name__ == "__main__":  # pragma: no cover
    run_bot()
