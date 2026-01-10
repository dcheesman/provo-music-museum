"""
Data Model for Provo Music Museum - Velour Show Archive

This defines the clean data structures for Shows, Artists, and their relationships.
Data is stored as JSON files for portability and easy editing.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional
from pathlib import Path


@dataclass
class Artist:
    """Represents a musical artist or band."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""  # Canonical name (e.g., "The Moth & The Flame")
    aliases: list[str] = field(default_factory=list)  # Other names/spellings
    spotify_url: Optional[str] = None
    website: Optional[str] = None
    social_links: dict = field(default_factory=dict)  # {"instagram": "...", "twitter": "..."}
    notes: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Artist":
        return cls(**data)


@dataclass
class ShowArtist:
    """Links an artist to a show with billing information."""
    artist_id: str
    billing_order: int = 0  # 0 = headliner, 1 = first opener, etc.
    is_headliner: bool = False
    set_notes: Optional[str] = None  # e.g., "acoustic set", "CD release"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ShowArtist":
        return cls(**data)


@dataclass
class ShowMedia:
    """Media associated with a show (posters, videos, photos)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    media_type: str = ""  # "poster", "youtube", "photo"
    url: str = ""
    caption: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ShowMedia":
        return cls(**data)


@dataclass
class Show:
    """Represents a single show/event at Velour."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: Optional[str] = None  # ISO format: "2006-01-13"
    title: str = ""  # Raw title from calendar
    genre: Optional[str] = None
    description: Optional[str] = None
    venue: str = "Velour Live Music Gallery"

    # Parsed/cleaned data
    artists: list[ShowArtist] = field(default_factory=list)
    media: list[ShowMedia] = field(default_factory=list)

    # Metadata
    is_music_event: bool = True  # False for "Closed", "Flea Market", etc.
    event_type: str = "concert"  # "concert", "open_mic", "improv", "private", "closed"
    ticket_price: Optional[str] = None
    sold_out: bool = False

    # Processing metadata
    raw_artists_text: Optional[str] = None  # Original unparsed text
    parse_confidence: float = 1.0  # 0-1, how confident we are in the parse
    needs_review: bool = False
    review_notes: Optional[str] = None

    # Timestamps
    original_extracted_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d['artists'] = [a.to_dict() if isinstance(a, ShowArtist) else a for a in self.artists]
        d['media'] = [m.to_dict() if isinstance(m, ShowMedia) else m for m in self.media]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Show":
        artists = [ShowArtist.from_dict(a) if isinstance(a, dict) else a for a in data.get('artists', [])]
        media = [ShowMedia.from_dict(m) if isinstance(m, dict) else m for m in data.get('media', [])]
        data['artists'] = artists
        data['media'] = media
        return cls(**data)


class DataStore:
    """
    Manages the JSON file storage for shows and artists.

    Directory structure:
    data/
      clean/
        artists.json       - All artists
        shows.json         - All shows
        artist_index.json  - Name -> ID mapping for quick lookup
    """

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent / "data" / "clean"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.artists_file = self.base_path / "artists.json"
        self.shows_file = self.base_path / "shows.json"
        self.index_file = self.base_path / "artist_index.json"

        self._artists: dict[str, Artist] = {}
        self._shows: dict[str, Show] = {}
        self._artist_index: dict[str, str] = {}  # normalized_name -> artist_id

        self._load()

    def _load(self):
        """Load existing data from JSON files."""
        if self.artists_file.exists():
            with open(self.artists_file, 'r') as f:
                data = json.load(f)
                self._artists = {a['id']: Artist.from_dict(a) for a in data}

        if self.shows_file.exists():
            with open(self.shows_file, 'r') as f:
                data = json.load(f)
                self._shows = {s['id']: Show.from_dict(s) for s in data}

        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self._artist_index = json.load(f)

        # Rebuild index if missing
        if not self._artist_index and self._artists:
            self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the artist name -> ID index."""
        self._artist_index = {}
        for artist in self._artists.values():
            normalized = self._normalize_name(artist.name)
            self._artist_index[normalized] = artist.id
            for alias in artist.aliases:
                normalized_alias = self._normalize_name(alias)
                self._artist_index[normalized_alias] = artist.id

    def _normalize_name(self, name: str) -> str:
        """Normalize artist name for matching."""
        return name.lower().strip()

    def save(self):
        """Save all data to JSON files."""
        with open(self.artists_file, 'w') as f:
            json.dump([a.to_dict() for a in self._artists.values()], f, indent=2)

        with open(self.shows_file, 'w') as f:
            json.dump([s.to_dict() for s in self._shows.values()], f, indent=2)

        with open(self.index_file, 'w') as f:
            json.dump(self._artist_index, f, indent=2)

    # Artist operations
    def add_artist(self, artist: Artist) -> Artist:
        """Add a new artist."""
        self._artists[artist.id] = artist
        normalized = self._normalize_name(artist.name)
        self._artist_index[normalized] = artist.id
        for alias in artist.aliases:
            self._artist_index[self._normalize_name(alias)] = artist.id
        return artist

    def get_artist(self, artist_id: str) -> Optional[Artist]:
        """Get artist by ID."""
        return self._artists.get(artist_id)

    def find_artist_by_name(self, name: str) -> Optional[Artist]:
        """Find artist by name or alias."""
        normalized = self._normalize_name(name)
        artist_id = self._artist_index.get(normalized)
        if artist_id:
            return self._artists.get(artist_id)
        return None

    def get_or_create_artist(self, name: str, aliases: list[str] = None) -> Artist:
        """Get existing artist or create new one."""
        artist = self.find_artist_by_name(name)
        if artist:
            return artist

        # Check aliases too
        if aliases:
            for alias in aliases:
                artist = self.find_artist_by_name(alias)
                if artist:
                    # Add new alias if not present
                    if name not in artist.aliases and name != artist.name:
                        artist.aliases.append(name)
                        self._artist_index[self._normalize_name(name)] = artist.id
                    return artist

        # Create new artist
        artist = Artist(name=name, aliases=aliases or [])
        return self.add_artist(artist)

    def update_artist(self, artist: Artist):
        """Update an existing artist."""
        artist.updated_at = datetime.now().isoformat()
        self._artists[artist.id] = artist
        self._rebuild_index()

    def all_artists(self) -> list[Artist]:
        """Get all artists."""
        return list(self._artists.values())

    # Show operations
    def add_show(self, show: Show) -> Show:
        """Add a new show."""
        self._shows[show.id] = show
        return show

    def get_show(self, show_id: str) -> Optional[Show]:
        """Get show by ID."""
        return self._shows.get(show_id)

    def find_shows_by_date(self, date_str: str) -> list[Show]:
        """Find shows on a specific date."""
        return [s for s in self._shows.values() if s.date == date_str]

    def update_show(self, show: Show):
        """Update an existing show."""
        show.updated_at = datetime.now().isoformat()
        self._shows[show.id] = show

    def all_shows(self) -> list[Show]:
        """Get all shows sorted by date."""
        return sorted(self._shows.values(), key=lambda s: s.date or "")

    def shows_needing_review(self) -> list[Show]:
        """Get shows that need manual review."""
        return [s for s in self._shows.values() if s.needs_review]

    # Statistics
    def get_stats(self) -> dict:
        """Get statistics about the data."""
        shows = self.all_shows()
        music_shows = [s for s in shows if s.is_music_event]
        needs_review = [s for s in shows if s.needs_review]

        return {
            "total_shows": len(shows),
            "music_shows": len(music_shows),
            "non_music_events": len(shows) - len(music_shows),
            "needs_review": len(needs_review),
            "total_artists": len(self._artists),
            "date_range": {
                "earliest": shows[0].date if shows else None,
                "latest": shows[-1].date if shows else None
            }
        }

    # Artist connections
    def get_artist_connections(self, artist_id: str) -> dict[str, int]:
        """Get all artists this artist has played with and how many times."""
        connections = {}
        for show in self._shows.values():
            artist_ids = [a.artist_id for a in show.artists]
            if artist_id in artist_ids:
                for other_id in artist_ids:
                    if other_id != artist_id:
                        connections[other_id] = connections.get(other_id, 0) + 1
        return connections

    def get_artist_show_count(self, artist_id: str) -> int:
        """Get number of shows an artist has played."""
        return sum(1 for s in self._shows.values()
                   if any(a.artist_id == artist_id for a in s.artists))


# Utility functions for classification
NON_MUSIC_KEYWORDS = [
    "closed", "renovation", "private event", "flea market",
    "journal jam", "adult prom", "fashion show"
]

OPEN_MIC_KEYWORDS = ["open-mic", "open mic", "acoustic night"]

IMPROV_KEYWORDS = ["thrillionaires", "improv theater", "improv"]


def classify_event_type(title: str, description: str = "") -> tuple[bool, str]:
    """
    Classify whether this is a music event and what type.

    Returns: (is_music_event, event_type)
    """
    text = f"{title} {description}".lower()

    # Check for closed/non-music
    for keyword in NON_MUSIC_KEYWORDS:
        if keyword in text:
            return (False, "closed" if "closed" in text else "other")

    # Check for open mic
    for keyword in OPEN_MIC_KEYWORDS:
        if keyword in text:
            return (True, "open_mic")

    # Check for improv
    for keyword in IMPROV_KEYWORDS:
        if keyword in text:
            return (True, "improv")

    # Default to concert
    return (True, "concert")


if __name__ == "__main__":
    # Demo usage
    store = DataStore()

    # Create some test data
    artist = store.get_or_create_artist("Neon Trees", aliases=["The Neon Trees"])
    print(f"Created artist: {artist.name} (ID: {artist.id})")

    show = Show(
        date="2006-02-11",
        title="8pm» (indie-emo) Neon Trees",
        genre="indie-emo",
        event_type="concert"
    )
    show.artists.append(ShowArtist(artist_id=artist.id, is_headliner=True))
    store.add_show(show)

    store.save()
    print(f"\nStats: {store.get_stats()}")
