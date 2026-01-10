# Velour Live Music Gallery - Show Data Scraper

This project scrapes show data from the Velour Live Music Gallery website (https://velourlive.com) for data visualization and analysis purposes.

## Overview

The system successfully extracts show information from the Velour Live calendar, including:
- Show dates and times
- Artist names and lineups
- Genres and descriptions
- Event types (regular shows, open mic nights, festivals, special events)

## Files Created

### Data Files
- `velour_final_dataset_20251011_143729.csv` - Main dataset in CSV format
- `velour_final_dataset_20251011_143729.tsv` - Dataset in TSV format (as requested)
- `velour_final_dataset_20251011_143729.json` - Dataset in JSON format
- `velour_summary_report_20251011_143729.json` - Summary statistics and metadata

### Scripts
- `analyze_velour_site.py` - Initial site analysis tool
- `explore_velour_pages.py` - Page exploration and link discovery
- `velour_scraper.py` - Main Selenium-based scraper
- `parse_velour_calendar.py` - Calendar data parser
- `velour_complete_scraper.py` - Comprehensive scraper for multiple months
- `create_final_dataset.py` - Data cleaning and final dataset creation

### Configuration
- `requirements.txt` - Python dependencies
- `venv/` - Virtual environment

## Dataset Summary

**Total Shows:** 122  
**Date Range:** October 1-31, 2025  
**Venue:** Velour Live Music Gallery  

### Event Types
- Regular Shows: 77
- Festivals: 33 (including FilmQuest Film Festival)
- Open Mic Nights: 9
- Special Events: 3 (including GOTH PROM)

### Genres Represented
- Rock/Indie: 6 shows
- Indie-Jazz/Rock: 3 shows
- Pop: 3 shows
- Indie/Art-Rock: 3 shows
- Alt/Rock: 3 shows
- Indie/Post-Punk: 3 shows
- Alt-Indie: 3 shows
- Unknown: 98 shows (various events without genre classification)

## Technical Approach

### 1. Site Analysis
- Analyzed the website structure and identified that show data is loaded in an iframe
- Discovered the calendar is located at `/calendar/index.php`
- Confirmed the site uses minimal JavaScript, making Selenium scraping effective

### 2. Data Extraction
- Used Selenium WebDriver to handle dynamic content loading
- Implemented robust parsing to extract individual shows from calendar format
- Created multiple extraction methods to handle different data patterns

### 3. Data Processing
- Cleaned and standardized show data
- Categorized events by type (open mic, festival, special event, regular show)
- Extracted genre information from show descriptions
- Parsed artist lineups and supporting acts

### 4. Data Export
- Created multiple output formats (CSV, TSV, JSON)
- Generated comprehensive summary statistics
- Included metadata for data provenance and quality assessment

## Usage

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Install ChromeDriver (if not already installed)
brew install chromedriver
```

### Running the Scraper
```bash
# Activate virtual environment
source venv/bin/activate

# Run the complete scraper
python velour_complete_scraper.py

# Or run individual components
python velour_scraper.py
python parse_velour_calendar.py
python create_final_dataset.py
```

## Data Structure

Each show record contains:
- `date`: ISO date format (YYYY-MM-DD)
- `day`, `month`, `year`: Individual date components
- `title`: Show title or headliner name
- `genre`: Musical genre (when available)
- `artists`: Supporting acts and openers
- `description`: Full show description
- `venue`: Venue name (Velour Live Music Gallery)
- `is_open_mic`: Boolean flag for open mic nights
- `is_festival`: Boolean flag for festival events
- `is_special_event`: Boolean flag for special events
- `extracted_at`: Timestamp of data extraction

## Challenges and Solutions

### Challenge 1: Dynamic Content Loading
**Problem:** Show data was loaded in an iframe, not directly accessible
**Solution:** Used Selenium to switch to iframe context and extract content

### Challenge 2: Calendar Format Parsing
**Problem:** Raw calendar data was in a complex table format
**Solution:** Created a robust parser that identifies day numbers and associates show descriptions

### Challenge 3: Data Quality
**Problem:** Inconsistent formatting and missing genre information
**Solution:** Implemented data cleaning and categorization logic

## Future Enhancements

1. **Multi-Month Scraping:** Extend to scrape multiple months/years
2. **Historical Data:** Access archived calendar data
3. **Real-time Updates:** Set up automated periodic scraping
4. **Enhanced Parsing:** Improve genre detection and artist extraction
5. **Data Validation:** Add data quality checks and validation rules

## Data Visualization Opportunities

The scraped data is ready for various visualizations:
- Timeline of shows by date
- Genre distribution charts
- Artist frequency analysis
- Event type breakdowns
- Monthly show patterns
- Venue capacity analysis (if available)

## Notes

- The scraper respects the website's structure and implements appropriate delays
- Data extraction was performed on October 11, 2025
- The dataset represents October 2025 shows from Velour Live Music Gallery
- All data is publicly available information from the venue's website

## Contact

For questions about this scraping system or the data, please refer to the project documentation or contact the development team.
