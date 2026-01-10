# Provo Music Museum - Data Tools

Tools for cleaning, parsing, and managing Velour Live Music Gallery show data.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key (for LLM parsing)
export ANTHROPIC_API_KEY="your-key-here"
```

## Tools Overview

### 1. Data Model (`data_model.py`)

Defines the clean data structure:

- **Show**: Individual show/event with date, title, genre, artists
- **Artist**: Band or performer with canonical name and aliases
- **ShowArtist**: Links artists to shows with billing info
- **DataStore**: JSON file-based storage manager

Data is stored in `data/clean/`:
- `artists.json` - All artist records
- `shows.json` - All show records
- `artist_index.json` - Name-to-ID lookup index

### 2. LLM Parser (`llm_parser.py`)

Intelligent artist name parser using Claude API:

```python
from llm_parser import ArtistParser

parser = ArtistParser(api_key="...")
result = parser.parse("8pm» (indie) Band A w/ Band B & The Cs")

# result.artists = [ParsedArtist("Band A", headliner=True), ...]
# result.event_type = "concert"
# result.genre = "indie"
```

Key features:
- Distinguishes band names with "&" from artist separators
- Handles "w/" opener notation
- Removes metadata (prices, dates, "CD Release", etc.)
- Falls back to rule-based parsing when API unavailable

### 3. Migration Script (`migrate_data.py`)

Processes raw CSV data into clean format:

```bash
# Dry run (rule-based only, no save)
python migrate_data.py --dry-run --limit 100

# Full migration with LLM
python migrate_data.py --api-key YOUR_KEY

# Process specific date range
python migrate_data.py --start-date 2020-01-01 --end-date 2020-12-31
```

Options:
- `--csv PATH` - Source CSV file (defaults to most recent in exports/)
- `--dry-run` - Don't save results
- `--no-llm` - Use rule-based parsing only
- `--limit N` - Process only N shows
- `--save-interval N` - Save progress every N shows

### 4. Review Tool (`review_tool.py`)

Interactive tool for reviewing flagged shows:

```bash
# Interactive review
python review_tool.py

# Export review queue for external editing
python review_tool.py --export review_queue.json

# Import corrections
python review_tool.py --import corrections.json

# Show stats
python review_tool.py --stats
```

Commands during interactive review:
- `Enter` - Accept and continue
- `e` - Edit artists manually
- `t` - Change event type
- `n` - Mark as not a music event
- `s` - Skip (keep flagged)
- `q` - Quit and save

### 5. Website Export (`export_website_data.py`)

Exports data for the Astro website:

```bash
python export_website_data.py

# Custom output directory
python export_website_data.py --output /path/to/website/public/data
```

Generates:
- `artists.json` - Artist list with stats
- `shows.json` - Show list for timeline/search
- `network.json` - D3-compatible network graph
- `stats.json` - Overall statistics

## Typical Workflow

### Initial Setup
```bash
# 1. Run migration with rule-based parsing first
python migrate_data.py --no-llm

# 2. Review flagged entries
python review_tool.py --stats  # See how many need review

# 3. Export for review
python review_tool.py --export review_batch_1.json

# 4. (Edit review_batch_1.json manually or with LLM assistance)

# 5. Import corrections
python review_tool.py --import review_batch_1.json
```

### LLM-Assisted Processing
```bash
# Process with Claude API (costs money but more accurate)
export ANTHROPIC_API_KEY="sk-..."
python migrate_data.py --api-key $ANTHROPIC_API_KEY

# Or process in batches to control costs
python migrate_data.py --start-date 2006-01-01 --end-date 2006-12-31
```

### Website Deployment
```bash
# Export data to website
python export_website_data.py

# Build website
cd ../website
npm run build
```

## Data Quality Notes

The parser handles these common issues:
- "w/" artist separators
- Band names containing "&" (e.g., "Meg & Dia")
- "& the X" suffixes (e.g., "Joshua James & the Southern Boys")
- Price markers ($10, $8-$10)
- Date prefixes (8pm»)
- Genre prefixes ((indie-rock))
- CD/EP release markers
- Location info ((from CA), (touring))
- SOLD OUT markers

Shows flagged for review:
- Ambiguous "&" usage
- No artists extracted from apparent music events
- LLM parsing failures
- Low confidence parses

## API Costs

Using Claude API for parsing:
- ~1000 tokens per show (input + output)
- ~7000 shows = ~7M tokens
- Estimated cost: ~$20-30 with Claude Sonnet

Consider:
- Processing in batches
- Using rule-based for obvious cases
- Manual review for edge cases
