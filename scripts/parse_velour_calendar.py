#!/usr/bin/env python3
"""
Velour Calendar Parser
Parses the raw calendar data to extract individual shows with proper dates and details
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

class VelourCalendarParser:
    def __init__(self):
        self.shows: List[Dict] = []
    
    def parse_calendar_data(self, raw_data: str, month: str = "October", year: int = 2025) -> List[Dict]:
        """Parse raw calendar data to extract individual shows"""
        print(f"Parsing calendar data for {month} {year}...")
        
        # Clean up the raw data
        lines = raw_data.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        # Find the calendar section (after "Sun Mon Tue Wed Thu Fri Sat")
        calendar_start = -1
        for i, line in enumerate(cleaned_lines):
            if "Sun Mon Tue Wed Thu Fri Sat" in line:
                calendar_start = i + 1
                break
        
        if calendar_start == -1:
            print("Could not find calendar section")
            return []
        
        # Extract calendar data
        calendar_lines = cleaned_lines[calendar_start:]
        
        # Parse the calendar grid
        shows = self._parse_calendar_grid(calendar_lines, month, year)
        
        self.shows = shows
        print(f"Parsed {len(shows)} shows from calendar")
        
        return shows
    
    def _parse_calendar_grid(self, lines: List[str], month: str, year: int) -> List[Dict]:
        """Parse the calendar grid to extract individual shows"""
        shows = []
        
        # Find the calendar section with day numbers
        day_line_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^\s*\d+\s*$', line):  # Line with just a day number
                day_line_start = i
                break
        
        if day_line_start == -1:
            print("Could not find day numbers in calendar")
            return []
        
        # Process the calendar data
        current_day = None
        current_show = None
        
        for i in range(day_line_start, len(lines)):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is a day number
            day_match = re.match(r'^(\d+)$', line)
            if day_match:
                # Save previous show if exists
                if current_show and current_day:
                    shows.append(current_show)
                
                # Start new day
                current_day = int(day_match.group(1))
                current_show = None
                continue
            
            # Check if this is a show description
            if current_day and line and not re.match(r'^\d+$', line):
                # This is a show description
                if current_show:
                    # Multiple shows on same day, save previous and start new
                    shows.append(current_show)
                
                current_show = self._create_show_entry(line, current_day, month, year)
        
        # Don't forget the last show
        if current_show and current_day:
            shows.append(current_show)
        
        return shows
    
    def _create_show_entry(self, description: str, day: int, month: str, year: int) -> Dict:
        """Create a show entry from description and date info"""
        # Parse the show description
        show_data = self._parse_show_description(description)
        
        # Create the date
        try:
            date_str = f"{year}-{self._month_to_number(month):02d}-{day:02d}"
            show_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            show_date = None
            date_str = f"{month} {day}, {year}"
        
        return {
            'date': date_str,
            'day': day,
            'month': month,
            'year': year,
            'title': show_data['title'],
            'genre': show_data['genre'],
            'artists': show_data['artists'],
            'description': description,
            'venue': 'Velour Live Music Gallery',
            'extracted_at': datetime.now().isoformat()
        }
    
    def _parse_show_description(self, description: str) -> Dict:
        """Parse show description to extract title, genre, and artists"""
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description.strip())
        
        # Look for genre in parentheses at the start
        genre_match = re.match(r'^\(([^)]+)\)\s*(.*)', description)
        if genre_match:
            genre = genre_match.group(1)
            rest = genre_match.group(2)
        else:
            genre = None
            rest = description
        
        # Look for "w/" (with) to separate headliner from openers
        if ' w/ ' in rest:
            parts = rest.split(' w/ ', 1)
            title = parts[0].strip()
            artists = parts[1].strip()
        else:
            title = rest
            artists = None
        
        # Clean up title (remove quotes, etc.)
        title = title.strip('"').strip()
        
        return {
            'title': title,
            'genre': genre,
            'artists': artists
        }
    
    def _month_to_number(self, month: str) -> int:
        """Convert month name to number"""
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        return months.get(month, 1)
    
    def save_to_csv(self, filename: str = None) -> str:
        """Save parsed shows to CSV"""
        if not self.shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_parsed_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        df = pd.DataFrame(self.shows)
        df.to_csv(filepath, index=False)
        
        print(f"Parsed shows saved to: {filepath}")
        return filepath
    
    def save_to_json(self, filename: str = None) -> str:
        """Save parsed shows to JSON"""
        if not self.shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_parsed_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(self.shows, f, indent=2, default=str)
        
        print(f"Parsed shows saved to: {filepath}")
        return filepath
    
    def print_summary(self):
        """Print a summary of parsed shows"""
        if not self.shows:
            print("No shows data found")
            return
        
        print(f"\n=== Parsed Shows Summary ===")
        print(f"Total shows found: {len(self.shows)}")
        
        # Group by genre
        genres = {}
        for show in self.shows:
            genre = show.get('genre') or 'Unknown'
            genres[genre] = genres.get(genre, 0) + 1
        
        print(f"\n=== Shows by Genre ===")
        for genre, count in sorted(genres.items(), key=lambda x: x[0] if x[0] else ''):
            print(f"{genre}: {count}")
        
        # Show sample shows
        print(f"\n=== Sample Shows ===")
        for i, show in enumerate(self.shows[:10], 1):
            print(f"{i}. {show['date']} - {show['title']}")
            if show.get('genre'):
                print(f"   Genre: {show['genre']}")
            if show.get('artists'):
                print(f"   Artists: {show['artists']}")
            print()

def main():
    # Load the raw calendar data from the previous scraping
    try:
        with open('/Users/deancheesman/Dropbox/Provo Music Museum/velour_shows_20251011_143528.json', 'r') as f:
            raw_data = json.load(f)
        
        # Find the calendar data (it's in the first entry's raw_text)
        calendar_data = None
        for entry in raw_data:
            if 'raw_text' in entry and 'Open-Mic Night' in entry['raw_text']:
                calendar_data = entry['raw_text']
                break
        
        if not calendar_data:
            print("Could not find calendar data in scraped results")
            return
        
        # Parse the calendar data
        parser = VelourCalendarParser()
        shows = parser.parse_calendar_data(calendar_data, month="October", year=2025)
        
        if shows:
            # Print summary
            parser.print_summary()
            
            # Save to files
            csv_file = parser.save_to_csv()
            json_file = parser.save_to_json()
            
            print(f"\n=== Files Created ===")
            print(f"CSV: {csv_file}")
            print(f"JSON: {json_file}")
        else:
            print("No shows could be parsed from the calendar data")
    
    except FileNotFoundError:
        print("Could not find the scraped data file. Please run the scraper first.")
    except Exception as e:
        print(f"Error parsing calendar data: {e}")

if __name__ == "__main__":
    main()
