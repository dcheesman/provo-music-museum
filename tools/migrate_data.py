#!/usr/bin/env python3
"""
Data Migration Script for Velour Show Archive

Processes the raw CSV data and creates a clean dataset with properly
parsed artists using the LLM parser.

Usage:
    # Dry run (no LLM, just rule-based parsing)
    python migrate_data.py --dry-run

    # Full migration with LLM parsing
    python migrate_data.py --api-key YOUR_KEY

    # Process specific date range
    python migrate_data.py --start-date 2006-01-01 --end-date 2006-12-31

    # Resume from cache
    python migrate_data.py --resume
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_model import DataStore, Show, ShowArtist, classify_event_type
from llm_parser import ArtistParser, BatchParser, ParseResult


def load_raw_data(csv_path: str) -> list[dict]:
    """Load raw show data from CSV."""
    shows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty dates or duplicate header rows
            if not row.get('date') or row.get('date') == 'date':
                continue
            shows.append(row)
    return shows


def process_show(raw: dict, parser: ArtistParser, store: DataStore) -> Show:
    """Process a single raw show into a clean Show object."""

    # Parse the show text
    title = raw.get('title', '')
    description = raw.get('description', '')
    date = raw.get('date', '')

    result = parser.parse(title, description, date)

    # Validate date range (Velour opened in 2006)
    needs_review = result.needs_review
    review_notes = result.review_reason
    if date:
        try:
            year = int(date[:4])
            if year < 2006 or year > 2026:
                needs_review = True
                review_notes = f"Date outside valid range (2006-2026): {date}"
        except (ValueError, IndexError):
            needs_review = True
            review_notes = f"Invalid date format: {date}"

    # Create Show object
    show = Show(
        date=date if date else None,
        title=title,
        genre=result.genre or raw.get('genre'),
        description=description if description != title else None,
        venue=raw.get('venue', 'Velour Live Music Gallery'),
        is_music_event=result.is_music_event,
        event_type=result.event_type,
        ticket_price=result.ticket_price,
        sold_out=result.sold_out,
        raw_artists_text=raw.get('artists', ''),
        parse_confidence=result.confidence,
        needs_review=needs_review,
        review_notes=review_notes,
        original_extracted_at=raw.get('extracted_at')
    )

    # Link artists
    for parsed_artist in result.artists:
        # Get or create artist in the store
        artist = store.get_or_create_artist(parsed_artist.name)

        # Create show-artist link
        show_artist = ShowArtist(
            artist_id=artist.id,
            billing_order=0 if parsed_artist.is_headliner else len(show.artists) + 1,
            is_headliner=parsed_artist.is_headliner,
            set_notes=parsed_artist.notes
        )
        show.artists.append(show_artist)

    return show


def migrate(
    csv_path: str,
    api_key: str = None,
    dry_run: bool = False,
    start_date: str = None,
    end_date: str = None,
    limit: int = None,
    use_llm: bool = True,
    save_interval: int = 100
):
    """
    Run the migration process.

    Args:
        csv_path: Path to raw CSV data
        api_key: Anthropic API key for LLM parsing
        dry_run: If True, don't save results
        start_date: Only process shows after this date
        end_date: Only process shows before this date
        limit: Maximum number of shows to process
        use_llm: Whether to use LLM for parsing
        save_interval: Save progress every N shows
    """
    print(f"Loading raw data from: {csv_path}")
    raw_shows = load_raw_data(csv_path)
    print(f"Loaded {len(raw_shows)} raw shows")

    # Filter by date range
    if start_date:
        raw_shows = [s for s in raw_shows if s.get('date', '') >= start_date]
    if end_date:
        raw_shows = [s for s in raw_shows if s.get('date', '') <= end_date]

    if limit:
        raw_shows = raw_shows[:limit]

    print(f"Processing {len(raw_shows)} shows")

    # Initialize parser and store
    parser = ArtistParser(api_key=api_key, use_llm=use_llm and not dry_run)
    store = DataStore()

    # Process shows
    processed = 0
    errors = 0
    needs_review_count = 0

    start_time = time.time()

    for i, raw in enumerate(raw_shows):
        try:
            show = process_show(raw, parser, store)
            store.add_show(show)
            processed += 1

            if show.needs_review:
                needs_review_count += 1

            # Progress update
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                print(f"Processed {i + 1}/{len(raw_shows)} shows ({rate:.1f}/sec)")

            # Periodic save
            if not dry_run and (i + 1) % save_interval == 0:
                store.save()
                print(f"  Saved progress at {i + 1} shows")

        except Exception as e:
            errors += 1
            print(f"Error processing show {raw.get('date', 'unknown')}: {e}")

    # Final save
    if not dry_run:
        store.save()

    # Print summary
    elapsed = time.time() - start_time
    stats = store.get_stats()

    print("\n" + "=" * 50)
    print("MIGRATION COMPLETE")
    print("=" * 50)
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"Shows processed: {processed}")
    print(f"Errors: {errors}")
    print(f"Needs review: {needs_review_count}")
    print(f"\nFinal stats:")
    print(f"  Total shows: {stats['total_shows']}")
    print(f"  Music shows: {stats['music_shows']}")
    print(f"  Non-music events: {stats['non_music_events']}")
    print(f"  Total artists: {stats['total_artists']}")
    print(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")

    if dry_run:
        print("\n(DRY RUN - no data was saved)")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Migrate Velour show data")
    parser.add_argument(
        '--csv',
        default=None,
        help='Path to raw CSV file'
    )
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving (rule-based parsing only)'
    )
    parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Use rule-based parsing instead of LLM'
    )
    parser.add_argument(
        '--start-date',
        help='Only process shows after this date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        help='Only process shows before this date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of shows to process'
    )
    parser.add_argument(
        '--save-interval',
        type=int,
        default=100,
        help='Save progress every N shows'
    )

    args = parser.parse_args()

    # Find CSV file
    csv_path = args.csv
    if not csv_path:
        # Look for most recent export
        exports_dir = Path(__file__).parent.parent / "data" / "exports"
        csv_files = sorted(exports_dir.glob("velour_complete_historical_*.csv"), reverse=True)
        if csv_files:
            csv_path = str(csv_files[0])
            print(f"Using most recent export: {csv_path}")
        else:
            print("Error: No CSV file found. Specify with --csv")
            sys.exit(1)

    # Use API key from args or environment
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")

    migrate(
        csv_path=csv_path,
        api_key=api_key,
        dry_run=args.dry_run,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit,
        use_llm=not args.no_llm,
        save_interval=args.save_interval
    )


if __name__ == "__main__":
    main()
