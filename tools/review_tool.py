#!/usr/bin/env python3
"""
Interactive Review Tool for Velour Show Data

Allows manual review and correction of shows that need attention,
particularly those with ambiguous artist parsing.

Usage:
    # Review all flagged shows
    python review_tool.py

    # Review specific date range
    python review_tool.py --start-date 2006-01-01 --end-date 2006-12-31

    # Export review queue to JSON for external editing
    python review_tool.py --export review_queue.json

    # Import corrections from JSON
    python review_tool.py --import corrections.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from data_model import DataStore, Show, ShowArtist, Artist


class ReviewTool:
    """Interactive tool for reviewing and correcting show data."""

    def __init__(self):
        self.store = DataStore()
        self._current_index = 0

    def get_review_queue(self, start_date: str = None, end_date: str = None) -> list[Show]:
        """Get all shows that need review."""
        shows = self.store.shows_needing_review()

        if start_date:
            shows = [s for s in shows if s.date and s.date >= start_date]
        if end_date:
            shows = [s for s in shows if s.date and s.date <= end_date]

        return sorted(shows, key=lambda s: s.date or "")

    def display_show(self, show: Show, index: int = None, total: int = None):
        """Display a show for review."""
        header = f"\n{'=' * 60}"
        if index is not None and total is not None:
            header += f"\n[{index + 1}/{total}]"
        print(header)
        print(f"Date: {show.date}")
        print(f"Title: {show.title}")
        if show.description and show.description != show.title:
            print(f"Description: {show.description}")
        print(f"Event Type: {show.event_type}")
        print(f"Genre: {show.genre or 'N/A'}")

        print(f"\nParsed Artists ({len(show.artists)}):")
        for i, sa in enumerate(show.artists):
            artist = self.store.get_artist(sa.artist_id)
            name = artist.name if artist else f"[Unknown: {sa.artist_id}]"
            headliner = " (headliner)" if sa.is_headliner else ""
            notes = f" [{sa.set_notes}]" if sa.set_notes else ""
            print(f"  {i + 1}. {name}{headliner}{notes}")

        if show.raw_artists_text:
            print(f"\nRaw artists text: {show.raw_artists_text}")

        print(f"\nConfidence: {show.parse_confidence:.0%}")
        if show.review_notes:
            print(f"Review reason: {show.review_notes}")

        print("=" * 60)

    def interactive_review(self, shows: list[Show]):
        """Run interactive review session."""
        if not shows:
            print("No shows to review!")
            return

        print(f"\nStarting review of {len(shows)} shows")
        print("\nCommands:")
        print("  [Enter] - Accept and continue")
        print("  e - Edit artists")
        print("  t - Change event type")
        print("  n - Mark as not a music event")
        print("  s - Skip (keep flagged for review)")
        print("  q - Quit and save")
        print("  ? - Help")

        i = 0
        modified = 0

        while i < len(shows):
            show = shows[i]
            self.display_show(show, i, len(shows))

            cmd = input("\nAction: ").strip().lower()

            if cmd == '' or cmd == 'a':
                # Accept
                show.needs_review = False
                show.review_notes = None
                self.store.update_show(show)
                modified += 1
                i += 1

            elif cmd == 'e':
                # Edit artists
                self._edit_artists(show)
                modified += 1
                i += 1

            elif cmd == 't':
                # Change event type
                self._change_event_type(show)
                modified += 1
                i += 1

            elif cmd == 'n':
                # Not a music event
                show.is_music_event = False
                show.event_type = "other"
                show.artists = []
                show.needs_review = False
                self.store.update_show(show)
                modified += 1
                i += 1

            elif cmd == 's':
                # Skip
                i += 1

            elif cmd == 'q':
                # Quit
                break

            elif cmd == 'b' and i > 0:
                # Back
                i -= 1

            elif cmd == '?':
                self._show_help()

            else:
                print("Unknown command. Press ? for help.")

        # Save changes
        self.store.save()
        print(f"\nReview session complete. Modified {modified} shows.")

    def _edit_artists(self, show: Show):
        """Edit artists for a show."""
        print("\nEdit Artists:")
        print("  Enter artist names, one per line")
        print("  Prefix with * for headliner")
        print("  Add [notes] for set notes")
        print("  Empty line when done")
        print("  Example: *Neon Trees [CD release]")

        new_artists = []
        while True:
            line = input("  > ").strip()
            if not line:
                break

            is_headliner = line.startswith('*')
            if is_headliner:
                line = line[1:].strip()

            # Extract notes
            notes = None
            if '[' in line and line.endswith(']'):
                name, notes = line.rsplit('[', 1)
                name = name.strip()
                notes = notes.rstrip(']').strip()
            else:
                name = line

            if name:
                artist = self.store.get_or_create_artist(name)
                new_artists.append(ShowArtist(
                    artist_id=artist.id,
                    billing_order=len(new_artists),
                    is_headliner=is_headliner,
                    set_notes=notes
                ))

        if new_artists:
            show.artists = new_artists
            show.needs_review = False
            show.review_notes = None
            self.store.update_show(show)
            print(f"Updated with {len(new_artists)} artists")
        else:
            print("No changes made")

    def _change_event_type(self, show: Show):
        """Change the event type of a show."""
        print("\nEvent types:")
        print("  1. concert")
        print("  2. open_mic")
        print("  3. improv")
        print("  4. private")
        print("  5. closed")
        print("  6. other")

        choice = input("Select (1-6): ").strip()
        types = ['concert', 'open_mic', 'improv', 'private', 'closed', 'other']

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(types):
                show.event_type = types[idx]
                show.is_music_event = types[idx] not in ['closed', 'other', 'private']
                if not show.is_music_event:
                    show.artists = []
                show.needs_review = False
                self.store.update_show(show)
                print(f"Changed to: {types[idx]}")
        except ValueError:
            print("Invalid choice")

    def _show_help(self):
        """Show help text."""
        print("""
Commands:
  [Enter] or a - Accept the current parsing and continue
  e - Edit artists manually
  t - Change event type (concert, open_mic, etc.)
  n - Mark as not a music event
  s - Skip this show (keep flagged)
  b - Go back to previous show
  q - Quit and save all changes
  ? - Show this help

When editing artists:
  - Enter one artist name per line
  - Prefix with * to mark as headliner
  - Add [notes] for set notes like "CD release"
  - Press Enter on empty line when done
""")

    def export_review_queue(self, output_path: str, start_date: str = None, end_date: str = None):
        """Export review queue to JSON for external editing."""
        shows = self.get_review_queue(start_date, end_date)

        export_data = []
        for show in shows:
            artists_info = []
            for sa in show.artists:
                artist = self.store.get_artist(sa.artist_id)
                artists_info.append({
                    "name": artist.name if artist else "Unknown",
                    "is_headliner": sa.is_headliner,
                    "notes": sa.set_notes
                })

            export_data.append({
                "id": show.id,
                "date": show.date,
                "title": show.title,
                "description": show.description,
                "raw_artists_text": show.raw_artists_text,
                "current_parse": artists_info,
                "event_type": show.event_type,
                "is_music_event": show.is_music_event,
                "review_reason": show.review_notes,
                "corrected_artists": None,  # Fill this in with corrections
                "corrected_event_type": None
            })

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported {len(export_data)} shows to {output_path}")

    def import_corrections(self, input_path: str):
        """Import corrections from JSON file."""
        with open(input_path, 'r') as f:
            corrections = json.load(f)

        imported = 0
        for item in corrections:
            show_id = item.get('id')
            show = self.store.get_show(show_id)
            if not show:
                print(f"Warning: Show {show_id} not found")
                continue

            # Apply event type correction
            if item.get('corrected_event_type'):
                show.event_type = item['corrected_event_type']
                show.is_music_event = item['corrected_event_type'] not in ['closed', 'other', 'private']

            # Apply artist corrections
            if item.get('corrected_artists'):
                show.artists = []
                for i, artist_info in enumerate(item['corrected_artists']):
                    if isinstance(artist_info, str):
                        name = artist_info
                        is_headliner = i == 0
                        notes = None
                    else:
                        name = artist_info.get('name')
                        is_headliner = artist_info.get('is_headliner', i == 0)
                        notes = artist_info.get('notes')

                    artist = self.store.get_or_create_artist(name)
                    show.artists.append(ShowArtist(
                        artist_id=artist.id,
                        billing_order=i,
                        is_headliner=is_headliner,
                        set_notes=notes
                    ))

            show.needs_review = False
            show.review_notes = None
            self.store.update_show(show)
            imported += 1

        self.store.save()
        print(f"Imported corrections for {imported} shows")


def main():
    parser = argparse.ArgumentParser(description="Review and correct show data")
    parser.add_argument('--start-date', help='Filter by start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Filter by end date (YYYY-MM-DD)')
    parser.add_argument('--export', metavar='FILE', help='Export review queue to JSON')
    parser.add_argument('--import-file', metavar='FILE', dest='import_file',
                        help='Import corrections from JSON')
    parser.add_argument('--stats', action='store_true', help='Show review statistics')

    args = parser.parse_args()

    tool = ReviewTool()

    if args.stats:
        queue = tool.get_review_queue(args.start_date, args.end_date)
        stats = tool.store.get_stats()
        print(f"\nData Store Statistics:")
        print(f"  Total shows: {stats['total_shows']}")
        print(f"  Total artists: {stats['total_artists']}")
        print(f"  Needs review: {stats['needs_review']}")
        print(f"\nFiltered review queue: {len(queue)} shows")
        return

    if args.export:
        tool.export_review_queue(args.export, args.start_date, args.end_date)
        return

    if args.import_file:
        tool.import_corrections(args.import_file)
        return

    # Interactive review
    shows = tool.get_review_queue(args.start_date, args.end_date)
    tool.interactive_review(shows)


if __name__ == "__main__":
    main()
