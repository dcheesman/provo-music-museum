#!/usr/bin/env python3
"""
Velour Historical Calendar Parser
Parses the historical calendar format with individual event links
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from bs4 import BeautifulSoup

class VelourHistoricalParser:
    def __init__(self):
        self.shows: List[Dict] = []
    
    def parse_historical_calendar(self, html_content: str, month: str = "October", year: int = 2025) -> List[Dict]:
        """Parse historical calendar HTML content to extract individual shows"""
        print(f"Parsing historical calendar for {month} {year}...")
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for event links
            event_links = soup.find_all('a', class_='entry')
            
            shows = []
            for link in event_links:
                show_data = self._extract_show_from_link(link, month, year)
                if show_data:
                    shows.append(show_data)
            
            # Also look for calendar table structure
            table_shows = self._parse_calendar_table(soup, month, year)
            if table_shows:
                shows.extend(table_shows)
            
            # Remove duplicates
            unique_shows = self._remove_duplicates(shows)
            
            self.shows = unique_shows
            print(f"Parsed {len(unique_shows)} shows from historical calendar")
            
            return unique_shows
            
        except Exception as e:
            print(f"Error parsing historical calendar: {e}")
            return []
    
    def _extract_show_from_link(self, link, month: str, year: int) -> Optional[Dict]:
        """Extract show data from an event link"""
        try:
            # Get the show title
            title = link.get_text(strip=True)
            if not title or title in ['', 'View this entry']:
                return None
            
            # Get the date from the href
            href = link.get('href', '')
            date_match = re.search(r'date=(\d{8})', href)
            if date_match:
                date_str = date_match.group(1)
                # Convert YYYYMMDD to date
                try:
                    show_date = datetime.strptime(date_str, '%Y%m%d')
                    date_formatted = show_date.strftime('%Y-%m-%d')
                    day = show_date.day
                except ValueError:
                    return None
            else:
                return None
            
            # Get additional info from title attribute
            title_attr = link.get('title', '')
            
            # Parse the show description
            show_data = self._parse_show_description(title)
            
            return {
                'date': date_formatted,
                'day': day,
                'month': month,
                'year': year,
                'title': show_data['title'],
                'genre': show_data['genre'],
                'artists': show_data['artists'],
                'description': title,
                'venue': 'Velour Live Music Gallery',
                'extracted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error extracting show from link: {e}")
            return None
    
    def _parse_calendar_table(self, soup: BeautifulSoup, month: str, year: int) -> List[Dict]:
        """Parse calendar table structure if present"""
        shows = []
        
        try:
            # Look for calendar tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 2:
                        show_data = self._extract_show_from_row(cells, month, year)
                        if show_data:
                            shows.append(show_data)
        
        except Exception as e:
            print(f"Error parsing calendar table: {e}")
        
        return shows
    
    def _extract_show_from_row(self, cells, month: str, year: int) -> Optional[Dict]:
        """Extract show data from a table row"""
        try:
            show_data = {
                'date': None,
                'day': None,
                'month': month,
                'year': year,
                'title': None,
                'genre': None,
                'artists': None,
                'description': None,
                'venue': 'Velour Live Music Gallery',
                'extracted_at': datetime.now().isoformat()
            }
            
            # Try to extract date from first cell
            if cells[0].get_text(strip=True):
                date_text = cells[0].get_text(strip=True)
                # Look for day number
                day_match = re.search(r'\b(\d{1,2})\b', date_text)
                if day_match:
                    day = int(day_match.group(1))
                    show_data['day'] = day
                    show_data['date'] = f"{year}-{self._month_to_number(month):02d}-{day:02d}"
            
            # Try to extract title/description from other cells
            for i, cell in enumerate(cells[1:], 1):
                cell_text = cell.get_text(strip=True)
                if cell_text and not show_data['title']:
                    show_data['title'] = cell_text
                    show_data['description'] = cell_text
                    
                    # Parse the show description
                    parsed = self._parse_show_description(cell_text)
                    show_data['genre'] = parsed['genre']
                    show_data['artists'] = parsed['artists']
                    break
            
            # Only return if we have some meaningful data
            if show_data['date'] or show_data['title']:
                return show_data
            
        except Exception as e:
            print(f"Error extracting show from row: {e}")
        
        return None
    
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
    
    def _remove_duplicates(self, shows: List[Dict]) -> List[Dict]:
        """Remove duplicate shows based on date and title"""
        seen = set()
        unique_shows = []
        
        for show in shows:
            # Create a key based on date and title
            key = (show.get('date', ''), show.get('title', ''))
            if key not in seen and key != ('', ''):
                seen.add(key)
                unique_shows.append(show)
        
        return unique_shows
    
    def save_to_csv(self, filename: str = None) -> str:
        """Save shows data to CSV file"""
        if not self.shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_historical_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df = pd.DataFrame(self.shows)
        df.to_csv(filename, index=False)
        
        print(f"Historical shows data saved to: {filename}")
        return filename
    
    def save_to_json(self, filename: str = None) -> str:
        """Save shows data to JSON file"""
        if not self.shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_historical_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.shows, f, indent=2, default=str)
        
        print(f"Historical shows data saved to: {filename}")
        return filename
    
    def print_summary(self):
        """Print a summary of parsed data"""
        if not self.shows:
            print("No shows data found")
            return
        
        print(f"\n=== Historical Parsing Summary ===")
        print(f"Total shows found: {len(self.shows)}")
        
        # Show first few shows as examples
        print(f"\n=== Sample Shows ===")
        for i, show in enumerate(self.shows[:10], 1):
            print(f"{i}. Date: {show.get('date', 'N/A')}")
            print(f"   Title: {show.get('title', 'N/A')}")
            if show.get('genre'):
                print(f"   Genre: {show['genre']}")
            if show.get('artists'):
                print(f"   Artists: {show['artists']}")
            print()

def main():
    # Test with the sample content
    sample_file = "/Users/deancheesman/Dropbox/Provo Music Museum/logs/sample_content_2025_10.html"
    
    try:
        with open(sample_file, 'r') as f:
            html_content = f.read()
        
        parser = VelourHistoricalParser()
        shows = parser.parse_historical_calendar(html_content, month="October", year=2025)
        
        if shows:
            parser.print_summary()
            parser.save_to_csv()
            parser.save_to_json()
        else:
            print("No shows could be parsed from the historical calendar")
    
    except FileNotFoundError:
        print("Could not find the sample content file. Please run the debug script first.")
    except Exception as e:
        print(f"Error parsing historical calendar: {e}")

if __name__ == "__main__":
    main()

