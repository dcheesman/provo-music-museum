# Provo Music Museum - Velour Live Data Scraping Project

## Project Structure

```
Provo Music Museum/
├── data/
│   ├── raw/                    # Raw scraped data (before processing)
│   ├── processed/              # Cleaned and processed data
│   └── exports/                # Final datasets ready for analysis
├── scripts/
│   ├── analyze_velour_site.py      # Site analysis tool
│   ├── explore_velour_pages.py     # Page exploration
│   ├── velour_scraper.py           # Main scraper
│   ├── parse_velour_calendar.py    # Calendar parser
│   ├── create_final_dataset.py     # Data processor
│   ├── velour_historical_scraper.py # Historical data scraper
│   ├── velour_complete_scraper.py  # Complete scraper
│   └── requirements.txt            # Python dependencies
├── docs/
│   ├── README.md               # Project documentation
│   └── ARTIST_NETWORK_ANALYSIS.md  # Artist network analysis docs
├── webapp/                     # Interactive network visualization
│   ├── index.html              # Main HTML file
│   ├── style.css               # Styling
│   ├── app.js                  # D3.js visualization
│   └── README.md               # Web app documentation
├── logs/                       # Log files and debug data
├── venv/                       # Python virtual environment
└── provo music museum.txt      # Original project notes
```

## Current Status

### ✅ Completed
- Site analysis and structure discovery
- Basic scraper implementation
- Calendar data parsing
- Data cleaning and processing
- Multiple output formats (CSV, TSV, JSON)
- Project organization

### 📊 Data Collected
- **7,193 shows** total (all-time historical data from 2006-2025)
- **369 shows** from 2025 (complete year)
  - January: 29 shows
  - February: 35 shows
  - March: 31 shows
  - April: 26 shows
  - May: 28 shows
  - June: 27 shows
  - July: 29 shows
  - August: 31 shows
  - September: 28 shows
  - October: 31 shows
  - November: 32 shows
  - December: 42 shows
- Complete show information including dates, artists, genres
- Categorized events (regular shows, open mic, festivals, special events)
- Clean, analysis-ready dataset

### 🔧 Technical Issues Resolved
- ChromeDriver security quarantine issue
- Dynamic content loading (iframe handling)
- Calendar format parsing
- Data cleaning and standardization

### 📁 Key Files
- `data/exports/velour_complete_historical_20260102_205023.csv` - Complete historical dataset (CSV)
- `data/exports/velour_complete_historical_20260102_205023.json` - Complete historical dataset (JSON)
- `data/exports/velour_complete_historical_20260102_205023.tsv` - Complete historical dataset (TSV)
- `data/processed/velour_summary_report_20260102_205023.json` - Latest summary stats
- `data/processed/artists_*.csv` - Unique artists dataset
- `data/processed/artist_connections_*.csv` - Artist connection pairs
- `data/processed/artist_network_*.json` - Network graph data for visualization
- `scripts/update_2025_data.py` - Script to update data for remaining months
- `scripts/parse_artists_network.py` - Extract artists and build network
- `scripts/visualize_artist_network.py` - Create network visualizations
- `scripts/` - All Python scraping and processing scripts
- `docs/README.md` - Complete documentation
- `docs/ARTIST_NETWORK_ANALYSIS.md` - Artist network analysis documentation

## Data Updates

### Latest Update (January 2, 2026)
- ✅ Updated data for November and December 2025
- ✅ Added 16 new shows to the dataset
- ✅ Complete 2025 data now available (369 shows)
- ✅ Total dataset: 7,193 shows spanning 2006-2025
- ✅ Artist network analysis complete: 2,880 unique artists, 6,486 connections

### Updating Data
To update data for future months, run:
```bash
python scripts/update_2025_data.py
```

This script will:
- Scrape new months from the Velour Live calendar
- Merge with existing historical data
- Create updated datasets in CSV, JSON, and TSV formats
- Generate summary reports

### Artist Network Analysis
To parse artists and create network data:
```bash
python scripts/parse_artists_network.py
```

This will:
- Extract all artists from shows
- Create unique artist list (2,880 artists)
- Build network connections (6,486 connections)
- Generate datasets for analysis

To visualize the network:
```bash
python scripts/visualize_artist_network.py
```

**Note**: Requires `networkx` and `matplotlib`:
```bash
pip install networkx matplotlib
```

## Usage

### Running Scripts
```bash
# Activate virtual environment
source venv/bin/activate

# Run from project root
cd "/Users/deancheesman/Dropbox/Provo Music Museum"

# Run specific scripts
python scripts/velour_scraper.py
python scripts/create_final_dataset.py
```

### Data Access
- Complete historical dataset: `data/exports/velour_complete_historical_20260102_205023.tsv` (or .csv, .json)
- Summary report: `data/processed/velour_summary_report_20260102_205023.json`
- All exports: `data/exports/` directory

