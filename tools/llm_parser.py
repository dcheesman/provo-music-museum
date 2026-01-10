"""
LLM-Powered Artist Parser for Velour Show Data

Uses Claude API to intelligently parse artist names from show titles,
handling tricky cases like:
- "Between Sleep & Sound" (one band with & in name)
- "Band A & Band B" (two separate bands)
- "Joshua James & the Southern Boys" (one act)
- "Lady Venus & The Vixens" (one band)
"""

import os
import json
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedArtist:
    """Result of parsing an artist from show text."""
    name: str
    is_headliner: bool = False
    notes: Optional[str] = None  # "CD release", "acoustic", etc.
    confidence: float = 1.0


@dataclass
class ParseResult:
    """Complete result of parsing a show's artists."""
    artists: list[ParsedArtist]
    is_music_event: bool = True
    event_type: str = "concert"  # concert, open_mic, improv, closed, other
    genre: Optional[str] = None
    ticket_price: Optional[str] = None
    sold_out: bool = False
    confidence: float = 1.0
    needs_review: bool = False
    review_reason: Optional[str] = None


class ArtistParser:
    """
    Parses artist names from show titles using Claude API.
    Falls back to rule-based parsing if API unavailable.
    """

    def __init__(self, api_key: str = None, use_llm: bool = True):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.use_llm = use_llm and self.api_key is not None
        self._client = None

        if self.use_llm and self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                print("Warning: anthropic package not installed. Using rule-based parsing.")
                self.use_llm = False

    def parse(self, title: str, description: str = "", date: str = "") -> ParseResult:
        """
        Parse artists from show title and description.

        Args:
            title: Show title (e.g., "8pm» (indie-rock) Band A, Band B w/ Band C")
            description: Additional show description
            date: Show date for context

        Returns:
            ParseResult with parsed artists and metadata
        """
        # Quick classification for obvious non-music events
        text_lower = f"{title} {description}".lower()

        if self._is_closed_event(text_lower):
            return ParseResult(
                artists=[],
                is_music_event=False,
                event_type="closed",
                confidence=1.0
            )

        if self._is_open_mic(text_lower):
            return ParseResult(
                artists=[],
                is_music_event=True,
                event_type="open_mic",
                confidence=1.0
            )

        if self._is_improv(text_lower):
            return ParseResult(
                artists=[],
                is_music_event=True,
                event_type="improv",
                confidence=0.9
            )

        # Use LLM for complex parsing
        if self.use_llm and self._client:
            return self._parse_with_llm(title, description, date)

        # Fall back to rule-based parsing
        return self._parse_rules_based(title, description)

    def _is_closed_event(self, text: str) -> bool:
        """Check if this is a closed/non-event day."""
        keywords = ["closed for", "renovation", "private event", "flea market",
                    "journal jam", "adult prom", "fashion show"]
        return any(kw in text for kw in keywords)

    def _is_open_mic(self, text: str) -> bool:
        """Check if this is an open mic night."""
        return "open-mic" in text or "open mic" in text

    def _is_improv(self, text: str) -> bool:
        """Check if this is an improv/theater event."""
        return "thrillionaires" in text or "improv theater" in text

    def _parse_with_llm(self, title: str, description: str, date: str) -> ParseResult:
        """Use Claude to parse the artist names."""

        prompt = f"""Parse the artists from this concert listing at Velour Live Music Gallery.

SHOW DATE: {date or "Unknown"}
TITLE: {title}
DESCRIPTION: {description}

IMPORTANT PARSING RULES:
1. Some band names contain "&" or "and" as PART OF THE NAME (e.g., "Between Sleep & Sound", "Lady Venus & The Vixens", "Meg & Dia", "Uzi & Ari"). Keep these as single artists.
2. "&" or "and" BETWEEN artists separates them (e.g., "Band A & Band B" = two artists)
3. "w/" means "with" and introduces opening acts
4. Remove prefixes like "8pm»", "(genre)", "$10", "SOLD OUT"
5. Remove suffixes like "CD Release", "(touring)", "(from CA)", "(acoustic)"
6. The first artist mentioned is usually the headliner
7. "& the [Something]" usually means one act (e.g., "Joshua James & the Southern Boys" is ONE act)
8. Venue names like "Velour" and event names like "Cabaret Velour" are NOT artists
9. Calendar day numbers at the start (like "02", "13") should be stripped

Return a JSON object with this exact structure:
{{
  "artists": [
    {{"name": "Artist Name", "is_headliner": true, "notes": "optional notes like CD release"}},
    {{"name": "Second Artist", "is_headliner": false, "notes": null}}
  ],
  "genre": "genre if mentioned or null",
  "ticket_price": "price if mentioned or null",
  "sold_out": false,
  "confidence": 0.95,
  "needs_review": false,
  "review_reason": "reason if needs_review is true, else null"
}}

Set needs_review=true if:
- You're uncertain about whether an "&" is part of a name or separating artists
- The parsing is ambiguous
- There might be errors in the original text

Return ONLY the JSON, no other text."""

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            response_text = response.content[0].text.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            result = json.loads(response_text)

            # Convert to ParseResult
            artists = [
                ParsedArtist(
                    name=a["name"],
                    is_headliner=a.get("is_headliner", False),
                    notes=a.get("notes"),
                    confidence=result.get("confidence", 0.9)
                )
                for a in result.get("artists", [])
            ]

            return ParseResult(
                artists=artists,
                is_music_event=True,
                event_type="concert",
                genre=result.get("genre"),
                ticket_price=result.get("ticket_price"),
                sold_out=result.get("sold_out", False),
                confidence=result.get("confidence", 0.9),
                needs_review=result.get("needs_review", False),
                review_reason=result.get("review_reason")
            )

        except Exception as e:
            print(f"LLM parsing failed: {e}")
            # Fall back to rule-based
            result = self._parse_rules_based(title, description)
            result.needs_review = True
            result.review_reason = f"LLM parsing failed: {str(e)}"
            return result

    def _parse_rules_based(self, title: str, description: str) -> ParseResult:
        """Rule-based fallback parser."""

        # Combine title and description
        text = title
        if description and description != title:
            text = f"{title} {description}"

        # Extract genre
        genre_match = re.search(r'\(([^)]+(?:rock|pop|indie|folk|punk|emo|ska|blues|acoustic|electronic)[^)]*)\)', text, re.I)
        genre = genre_match.group(1) if genre_match else None

        # Extract price
        price_match = re.search(r'\$\d+(?:[/-]\$?\d+)?', text)
        ticket_price = price_match.group(0) if price_match else None

        # Check for sold out
        sold_out = "sold out" in text.lower()

        # Clean the text
        cleaned = self._clean_text(text)

        # Split into potential artists
        raw_artists = self._split_artists(cleaned)

        # Filter and create artist objects
        artists = []
        for i, name in enumerate(raw_artists):
            name = self._clean_artist_name(name)
            if name and len(name) > 1 and not self._is_noise(name):
                artists.append(ParsedArtist(
                    name=name,
                    is_headliner=(i == 0),
                    confidence=0.7  # Lower confidence for rule-based
                ))

        # Mark for review if we have potential issues
        needs_review = False
        review_reason = None

        if any("&" in a.name for a in artists):
            needs_review = True
            review_reason = "Contains '&' - verify if band name or separator"

        if len(artists) == 0 and not self._is_closed_event(text.lower()):
            needs_review = True
            review_reason = "No artists extracted from apparent music event"

        return ParseResult(
            artists=artists,
            is_music_event=True,
            event_type="concert",
            genre=genre,
            ticket_price=ticket_price,
            sold_out=sold_out,
            confidence=0.7,
            needs_review=needs_review,
            review_reason=review_reason
        )

    def _clean_text(self, text: str) -> str:
        """Remove prefixes, suffixes, and metadata from text."""
        # Remove time prefix
        text = re.sub(r'^\d*\s*\d{1,2}pm»?\s*', '', text)

        # Remove genre in parentheses at start
        text = re.sub(r'^\([^)]+\)\s*', '', text)

        # Remove prices
        text = re.sub(r'\$\d+(?:[/-]\$?\d+)?!?\s*', '', text)

        # Remove SOLD OUT
        text = re.sub(r'\bSOLD\s*OUT!?\b', '', text, flags=re.I)

        # Remove CD/EP release
        text = re.sub(r'\b(?:CD|EP)\s*[Rr]elease!?\b', '', text)

        # Remove touring/location info
        text = re.sub(r'\([^)]*(?:touring|from|CA|AK|NV|SLC|ID|WA|NM|NYC)[^)]*\)', '', text, flags=re.I)

        # Remove "formerly X"
        text = re.sub(r'\(formerly[^)]+\)', '', text, flags=re.I)

        # Remove acoustic/etc markers
        text = re.sub(r'\(acoustic\)', '', text, flags=re.I)

        return text.strip()

    def _split_artists(self, text: str) -> list[str]:
        """Split text into potential artist names."""
        # First split by " w/ " (with)
        parts = re.split(r'\s+w/\s*', text, flags=re.I)

        all_artists = []
        for part in parts:
            # Split by comma
            subparts = re.split(r',\s*', part)
            for subpart in subparts:
                # Split by " and " (but not "& the")
                if " and " in subpart.lower() and "& the" not in subpart.lower():
                    all_artists.extend(re.split(r'\s+and\s+', subpart, flags=re.I))
                else:
                    all_artists.append(subpart)

        return [a.strip() for a in all_artists if a.strip()]

    def _clean_artist_name(self, name: str) -> str:
        """Clean an individual artist name."""
        # Remove leading numbers (calendar artifacts)
        name = re.sub(r'^\d+\s*', '', name)

        # Remove trailing punctuation
        name = name.rstrip('.,;:!')

        # Remove quotes
        name = name.strip('"\'')

        # Normalize whitespace
        name = ' '.join(name.split())

        return name.strip()

    def _is_noise(self, name: str) -> bool:
        """Check if name is noise/not a real artist."""
        noise_terms = {
            'etc', 'art', 'old', 'by', 'if', 'er', 'rts', 'sdr', 'ned', 'apt',
            'ben', 'dan', 'reno', 'velour', 'cabaret', 'showcase', 'night',
            'music', 'featuring', 'poetry', 'open-mic', 'acoustic night'
        }
        return name.lower() in noise_terms or len(name) < 2


class BatchParser:
    """Process multiple shows with progress tracking and caching."""

    def __init__(self, api_key: str = None, cache_file: str = None):
        self.parser = ArtistParser(api_key=api_key)
        self.cache_file = cache_file
        self._cache = {}

        if cache_file and os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                self._cache = json.load(f)

    def parse_show(self, show_id: str, title: str, description: str = "",
                   date: str = "", use_cache: bool = True) -> ParseResult:
        """Parse a single show with caching."""

        cache_key = f"{show_id}:{title}:{description}"

        if use_cache and cache_key in self._cache:
            data = self._cache[cache_key]
            return self._dict_to_result(data)

        result = self.parser.parse(title, description, date)

        # Cache the result
        self._cache[cache_key] = self._result_to_dict(result)

        return result

    def save_cache(self):
        """Save cache to file."""
        if self.cache_file:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)

    def _result_to_dict(self, result: ParseResult) -> dict:
        """Convert ParseResult to dict for caching."""
        return {
            "artists": [
                {"name": a.name, "is_headliner": a.is_headliner,
                 "notes": a.notes, "confidence": a.confidence}
                for a in result.artists
            ],
            "is_music_event": result.is_music_event,
            "event_type": result.event_type,
            "genre": result.genre,
            "ticket_price": result.ticket_price,
            "sold_out": result.sold_out,
            "confidence": result.confidence,
            "needs_review": result.needs_review,
            "review_reason": result.review_reason
        }

    def _dict_to_result(self, data: dict) -> ParseResult:
        """Convert dict back to ParseResult."""
        artists = [
            ParsedArtist(
                name=a["name"],
                is_headliner=a.get("is_headliner", False),
                notes=a.get("notes"),
                confidence=a.get("confidence", 0.9)
            )
            for a in data.get("artists", [])
        ]
        return ParseResult(
            artists=artists,
            is_music_event=data.get("is_music_event", True),
            event_type=data.get("event_type", "concert"),
            genre=data.get("genre"),
            ticket_price=data.get("ticket_price"),
            sold_out=data.get("sold_out", False),
            confidence=data.get("confidence", 0.9),
            needs_review=data.get("needs_review", False),
            review_reason=data.get("review_reason")
        )


if __name__ == "__main__":
    # Test the parser with some examples
    parser = ArtistParser(use_llm=False)  # Use rule-based for testing

    test_cases = [
        "8pm» (indie-rock) Return To Sender, Taught Me, Between Sleep & Sound",
        "8pm» (indie) Lady Venus & The Vixens, The Handsome, Neon Trees (acoustic)",
        "8pm» Joshua James & the Southern Boys, Marcus Bently, Colin Moore",
        "Open-Mic Acoustic Night",
        "Closed for Renovations",
        "8pm» Neon Trees w/ The New Nervous and Pariah Poetic",
        "7pm» (touring indie-electronic) Shiny Toy Guns, Kill Hannah, Clear Static $10",
        "The Thrillionaires (Improv Theater)",
        "8pm» (emo-pop) Allred CD Release w/ The Trademark, Meg & Dia, Autumn Rhodes",
    ]

    print("Testing rule-based parser:\n")
    for title in test_cases:
        result = parser.parse(title)
        print(f"Title: {title}")
        print(f"  Event type: {result.event_type}")
        print(f"  Artists: {[a.name for a in result.artists]}")
        print(f"  Genre: {result.genre}")
        print(f"  Needs review: {result.needs_review} ({result.review_reason})")
        print()
