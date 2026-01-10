#!/usr/bin/env python3
"""
Export data from the clean DataStore to JSON files for the Astro website.

This generates:
- artists.json - List of all artists with stats
- shows.json - List of all shows
- network.json - D3-compatible network graph data

Usage:
    python export_website_data.py
    python export_website_data.py --output /path/to/website/public/data
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from data_model import DataStore


def export_artists(store: DataStore, output_dir: Path):
    """Export artist data for the artists page."""
    artists = store.all_artists()
    shows = store.all_shows()

    # Calculate stats for each artist
    artist_data = []
    for artist in artists:
        # Find shows this artist played
        artist_shows = [
            s for s in shows
            if any(a.artist_id == artist.id for a in s.artists)
        ]

        if not artist_shows:
            continue

        years = [int(s.date[:4]) for s in artist_shows if s.date]
        if not years:
            continue

        artist_data.append({
            "id": artist.id,
            "name": artist.name,
            "aliases": artist.aliases,
            "showCount": len(artist_shows),
            "firstYear": min(years),
            "lastYear": max(years),
            "spotifyUrl": artist.spotify_url,
            "website": artist.website
        })

    # Sort by show count descending
    artist_data.sort(key=lambda x: x["showCount"], reverse=True)

    output_file = output_dir / "artists.json"
    with open(output_file, 'w') as f:
        json.dump(artist_data, f)

    print(f"Exported {len(artist_data)} artists to {output_file}")
    return artist_data


def export_shows(store: DataStore, output_dir: Path):
    """Export show data for the shows/timeline pages."""
    shows = store.all_shows()
    artists = {a.id: a for a in store.all_artists()}

    show_data = []
    for show in shows:
        if not show.is_music_event:
            continue

        show_artists = []
        for sa in show.artists:
            artist = artists.get(sa.artist_id)
            if artist:
                show_artists.append({
                    "id": artist.id,
                    "name": artist.name,
                    "isHeadliner": sa.is_headliner
                })

        show_data.append({
            "id": show.id,
            "date": show.date,
            "title": show.title,
            "genre": show.genre,
            "eventType": show.event_type,
            "artists": show_artists,
            "soldOut": show.sold_out,
            "ticketPrice": show.ticket_price
        })

    output_file = output_dir / "shows.json"
    with open(output_file, 'w') as f:
        json.dump(show_data, f)

    print(f"Exported {len(show_data)} shows to {output_file}")
    return show_data


def export_network(store: DataStore, output_dir: Path, min_connections: int = 2):
    """Export network data for D3 visualization."""
    artists = store.all_artists()
    shows = store.all_shows()

    # Build connection counts
    connections = defaultdict(lambda: defaultdict(int))

    for show in shows:
        if not show.is_music_event:
            continue

        artist_ids = [a.artist_id for a in show.artists]
        for i, aid1 in enumerate(artist_ids):
            for aid2 in artist_ids[i + 1:]:
                # Ensure consistent ordering
                key = tuple(sorted([aid1, aid2]))
                connections[key[0]][key[1]] += 1

    # Create nodes (only artists with connections)
    connected_artists = set()
    for aid1, targets in connections.items():
        for aid2, count in targets.items():
            if count >= min_connections:
                connected_artists.add(aid1)
                connected_artists.add(aid2)

    artist_map = {a.id: a for a in artists}
    nodes = []
    for aid in connected_artists:
        artist = artist_map.get(aid)
        if not artist:
            continue

        show_count = store.get_artist_show_count(aid)
        connection_count = sum(1 for targets in connections.values()
                               for t, c in targets.items()
                               if (aid in [t] or aid in connections) and c >= min_connections)

        nodes.append({
            "id": aid,
            "name": artist.name,
            "showCount": show_count,
            "connectionCount": connection_count
        })

    # Create links
    links = []
    for aid1, targets in connections.items():
        for aid2, count in targets.items():
            if count >= min_connections and aid1 in connected_artists and aid2 in connected_artists:
                links.append({
                    "source": aid1,
                    "target": aid2,
                    "weight": count
                })

    network_data = {
        "nodes": nodes,
        "links": links
    }

    output_file = output_dir / "network.json"
    with open(output_file, 'w') as f:
        json.dump(network_data, f)

    print(f"Exported network with {len(nodes)} nodes and {len(links)} links to {output_file}")
    return network_data


def export_stats(store: DataStore, output_dir: Path):
    """Export overall statistics."""
    stats = store.get_stats()
    shows = store.all_shows()

    # Shows by year
    shows_by_year = defaultdict(int)
    for show in shows:
        if show.date and show.is_music_event:
            year = show.date[:4]
            shows_by_year[year] += 1

    stats_data = {
        "totalShows": stats["total_shows"],
        "musicShows": stats["music_shows"],
        "totalArtists": stats["total_artists"],
        "dateRange": stats["date_range"],
        "showsByYear": dict(sorted(shows_by_year.items()))
    }

    output_file = output_dir / "stats.json"
    with open(output_file, 'w') as f:
        json.dump(stats_data, f, indent=2)

    print(f"Exported stats to {output_file}")
    return stats_data


def main():
    parser = argparse.ArgumentParser(description="Export data for website")
    parser.add_argument(
        '--output',
        default=None,
        help='Output directory for JSON files'
    )
    parser.add_argument(
        '--min-connections',
        type=int,
        default=2,
        help='Minimum connection count to include in network (default: 2)'
    )

    args = parser.parse_args()

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path(__file__).parent.parent / "website" / "public" / "data"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data store
    store = DataStore()

    if store.get_stats()["total_shows"] == 0:
        print("No data in store. Run migrate_data.py first.")
        sys.exit(1)

    # Export all data
    print(f"\nExporting data to {output_dir}\n")
    export_artists(store, output_dir)
    export_shows(store, output_dir)
    export_network(store, output_dir, args.min_connections)
    export_stats(store, output_dir)

    print("\nDone!")


if __name__ == "__main__":
    main()
