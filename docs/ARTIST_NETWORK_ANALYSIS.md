# Velour Live Artist Network Analysis

## Overview

This document describes the artist network analysis system for the Velour Live Music Gallery dataset. The system extracts all artists/bands from show data, creates a network graph showing which bands have played together, and provides tools for analysis and visualization.

## Data Structure

### Artists Dataset (`artists_YYYYMMDD_HHMMSS.csv`)

Contains information about each unique artist/band:

- `artist_name`: Display name of the artist
- `normalized_name`: Normalized (lowercase) name for matching
- `total_shows`: Number of shows the artist has played
- `connection_count`: Number of other artists this artist has played with
- `years_active`: List of years the artist performed
- `first_year`: First year the artist performed
- `last_year`: Last year the artist performed
- `years_span`: Number of years between first and last performance

### Artist Connections Dataset (`artist_connections_YYYYMMDD_HHMMSS.csv`)

Contains pairs of artists who have played together:

- `artist1`: First artist name
- `artist1_normalized`: Normalized name
- `artist2`: Second artist name
- `artist2_normalized`: Normalized name
- `shows_together`: Number of shows where both artists performed

### Network Data (`artist_network_YYYYMMDD_HHMMSS.json`)

JSON structure containing nodes and edges for network visualization:

```json
{
  "nodes": [
    {
      "id": "normalized_name",
      "label": "Display Name",
      "size": 10,
      "shows": 10
    }
  ],
  "edges": [
    {
      "source": "artist1_normalized",
      "target": "artist2_normalized",
      "weight": 3,
      "shows_together": 3
    }
  ],
  "metadata": {
    "total_nodes": 3134,
    "total_edges": 7226,
    "total_shows": 7193
  }
}
```

## Current Statistics

Based on the latest analysis:

- **Total Unique Artists/Bands**: 3,134
- **Total Artist Connections**: 7,226
- **Shows with Artists Extracted**: 2,295 out of 7,193 total shows

### Top Artists by Show Count

1. Cory Mon - 45 shows
2. Boots to the Moon - 28 shows
3. Code Hero - 25 shows
4. Desert Noises - 23 shows
5. Mia Grace - 23 shows
6. Kathleen Frewin - 22 shows
7. Neon Trees - 21 shows
8. Kid Theodore - 20 shows
9. The Devil Whale - 20 shows
10. Timmy The Teeth - 20 shows

### Top Artist Connections

1. Echo ↔ Shake: 9 shows together
2. Old ↔ Young: 8 shows together
3. Cory Mon ↔ Jeff Stone: 6 shows together
4. Robert ↔ the Carrolls: 6 shows together
5. The Flame ↔ The Moth: 6 shows together

## Usage

### Parse Artists and Create Network

```bash
cd "/Users/deancheesman/Dropbox/Provo Music Museum"
source venv/bin/activate
python scripts/parse_artists_network.py
```

This will:
- Load the complete historical dataset
- Extract all artists from shows
- Create unique artist list
- Build network connections
- Save datasets (CSV, JSON) to `data/processed/`

### Visualize Network

```bash
python scripts/visualize_artist_network.py
```

This will:
- Load the network data
- Create network visualizations
- Save PNG files to `data/visualizations/`

**Note**: Requires `networkx` and `matplotlib`:
```bash
pip install networkx matplotlib
```

## Artist Extraction Logic

The parser extracts artists from multiple sources:

1. **Artists Field**: Direct artist listings
2. **Title Field**: Headliner and opener information
3. **Description Field**: Fallback for additional artist info

### Parsing Rules

- Separators: commas, "and", "&", "w/"
- Cleans parenthetical info: "(formerly X)", "(from Y)", "(CD release)"
- Normalizes names: case-insensitive matching
- Filters invalid entries: generic terms, metadata, single characters

### Example Parsing

Input: `"8pm» (indie-rock) Headliner w/ Opener1, Opener2"`
- Extracts: `["Headliner", "Opener1", "Opener2"]`

Input: `"Ferrin, Kaytlin Numbers, Avintaquin"`
- Extracts: `["Ferrin", "Kaytlin Numbers", "Avintaquin"]`

## Network Analysis

The network graph can be used for:

1. **Community Detection**: Find groups of artists who frequently play together
2. **Centrality Analysis**: Identify key artists in the network
3. **Path Analysis**: Find connections between any two artists
4. **Temporal Analysis**: Track how the network changes over time

## Future Enhancements

- [ ] Improve artist name normalization (handle variations)
- [ ] Add genre-based network analysis
- [ ] Create interactive web visualization
- [ ] Add temporal network analysis (network evolution over time)
- [ ] Export to Gephi format for advanced visualization
- [ ] Add artist similarity metrics

## Files Generated

All files are saved with timestamps in `data/processed/`:

- `artists_YYYYMMDD_HHMMSS.csv` - Artist dataset
- `artist_connections_YYYYMMDD_HHMMSS.csv` - Connection pairs
- `artist_network_YYYYMMDD_HHMMSS.json` - Network graph data
- `artist_network_summary_YYYYMMDD_HHMMSS.json` - Summary statistics

Visualizations are saved in `data/visualizations/`:

- `artist_network_full.png` - Full network (filtered)
- `artist_network_top50.png` - Top 50 artists network

