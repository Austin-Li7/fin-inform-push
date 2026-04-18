from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from fin_inform_push.demo_data import BRIEFING_WINDOWS, build_demo_articles
from fin_inform_push.macro_fetch import latest_macro_metrics
from fin_inform_push.obsidian import ObsidianConfig, publish_markdown_to_obsidian
from fin_inform_push.pipeline import build_briefing_note, render_markdown
from fin_inform_push.research_fetch import latest_research_items
from fin_inform_push.sources import DEFAULT_FEEDS, fetch_articles


def resolve_date_label(raw_date: str | None, now_fn=datetime.now) -> str:
    if raw_date:
        return raw_date
    return now_fn().strftime("%Y-%m-%d")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Obsidian-ready financial intelligence notes."
    )
    parser.add_argument("--demo", action="store_true", help="Generate demo briefing notes.")
    parser.add_argument("--live", action="store_true", help="Fetch live RSS feeds.")
    parser.add_argument("--date", help="Date label for generated notes. Defaults to today.")
    parser.add_argument(
        "--output-dir",
        default="demo_output",
        help="Directory where generated markdown files will be stored.",
    )
    parser.add_argument(
        "--obsidian",
        action="store_true",
        help="Also push generated notes into Obsidian Local REST API.",
    )
    parser.add_argument(
        "--obsidian-base-url",
        default=os.environ.get("OBSIDIAN_BASE_URL", "https://127.0.0.1:27124"),
        help="Base URL for Obsidian Local REST API.",
    )
    parser.add_argument(
        "--obsidian-api-key",
        default=os.environ.get("OBSIDIAN_API_KEY"),
        help="API key for Obsidian Local REST API. Defaults to OBSIDIAN_API_KEY.",
    )
    parser.add_argument(
        "--obsidian-folder",
        default=os.environ.get("OBSIDIAN_FOLDER", "Macro Briefings"),
        help="Vault folder where generated notes will be written.",
    )
    args = parser.parse_args()

    if args.demo == args.live:
        raise SystemExit("Choose exactly one mode: --demo or --live.")
    if args.obsidian and not args.obsidian_api_key:
        raise SystemExit("Set --obsidian-api-key or OBSIDIAN_API_KEY before using --obsidian.")

    date_label = resolve_date_label(args.date)
    output_dir = Path(args.output_dir) / date_label
    output_dir.mkdir(parents=True, exist_ok=True)

    articles = build_demo_articles() if args.demo else fetch_articles(DEFAULT_FEEDS)
    macro_metrics = latest_macro_metrics(live=args.live)
    research_items = latest_research_items(live=args.live)
    obsidian_config = (
        ObsidianConfig(
            base_url=args.obsidian_base_url,
            api_key=args.obsidian_api_key,
            folder=args.obsidian_folder,
        )
        if args.obsidian
        else None
    )
    for window in BRIEFING_WINDOWS:
        note = build_briefing_note(
            articles,
            window,
            date_label,
            macro_metrics=macro_metrics,
            research_items=research_items,
        )
        markdown = render_markdown(note)
        target = output_dir / f"{window.slug}.md"
        target.write_text(markdown, encoding="utf-8")
        print(target)
        if obsidian_config is not None:
            remote_path = publish_markdown_to_obsidian(
                date_label,
                window.slug,
                markdown,
                obsidian_config,
            )
            print(f"obsidian://{remote_path}")


if __name__ == "__main__":
    main()
