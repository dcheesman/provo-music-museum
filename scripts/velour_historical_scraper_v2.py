#!/usr/bin/env python3
"""
Velour Live Historical Scraper V2
Scrapes ALL available historical data from 2006-2026 using the discovered URL pattern
"""

import time
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

class VelourHistoricalScraperV2:
    def __init__(self):
        self.base_url = "https://velourlive.com"
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.all_shows: List[Dict] = []
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Import the parser
        from parse_velour_calendar import VelourCalendarParser
        self.parser = VelourCalendarParser()
    
    def scrape_all_historical_data(self, start_year: int = 2006, end_year: int = 2026) -> List[Dict]:
        """Scrape ALL historical data from start_year to end_year"""
        print(f"=== Velour Live Historical Data Scraper V2 ===")
        print(f"Scraping data from {start_year} to {end_year}")
        print(f"This will collect ~20 years of show data!\n")
        
        all_shows = []
        total_months = (end_year - start_year + 1) * 12
        current_month = 0
        
        for year in range(start_year, end_year + 1):
            print(f"\n=== Scraping Year {year} ===")
            
            for month in range(1, 13):
                current_month += 1
                month_name = datetime(2000, month, 1).strftime('%B')
                
                print(f"[{current_month}/{total_months}] {month_name} {year}...", end=" ")
                
                try:
                    month_shows = self._scrape_month_year_direct(month, year, month_name)
                    
                    if month_shows:
                        all_shows.extend(month_shows)
                        print(f"✅ {len(month_shows)} shows")
                    else:
                        print("❌ No shows")
                    
                    # Save progress every 50 shows
                    if len(all_shows) % 50 == 0 and len(all_shows) > 0:
                        self._save_progress(all_shows, f"historical_progress_{year}_{month:02d}")
                    
                    time.sleep(0.5)  # Be respectful
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                    continue
        
        self.all_shows = all_shows
        print(f"\n=== Historical Scraping Complete ===")
        print(f"Total shows collected: {len(all_shows)}")
        
        return all_shows
    
    def _scrape_month_year_direct(self, month: int, year: int, month_name: str) -> List[Dict]:
        """Scrape shows for a specific month and year using direct URL access"""
        try:
            # Use the discovered URL pattern
            url = f"{self.base_url}/calendar/month.php?month={month}&year={year}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for calendar content
            calendar_content = self._extract_calendar_content(soup)
            if not calendar_content:
                return []
            
            # Parse the calendar content
            shows = self.parser.parse_calendar_data(calendar_content, month_name, year)
            
            # Filter out shows that don't match the target year
            filtered_shows = []
            for show in shows:
                if show.get('year') == year and show.get('month') == month_name:
                    filtered_shows.append(show)
            
            return filtered_shows
            
        except Exception as e:
            print(f"Error scraping {month_name} {year}: {e}")
            return []
    
    def _extract_calendar_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract calendar content from the parsed HTML"""
        try:
            # Look for iframe content first
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if 'calendar' in iframe_src.lower():
                    # This is likely the calendar iframe
                    return str(iframe)
            
            # Look for calendar content in the main page
            calendar_indicators = [
                'open-mic night', 'concert', 'show', 'event', 'performance'
            ]
            
            page_text = soup.get_text().lower()
            if any(indicator in page_text for indicator in calendar_indicators):
                return soup.get_text()
            
            return None
            
        except Exception as e:
            print(f"Error extracting calendar content: {e}")
            return None
    
    def _save_progress(self, shows: List[Dict], filename_prefix: str):
        """Save progress periodically"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.project_root, 'logs', f"{filename_prefix}_{timestamp}.json")
        
        with open(filename, 'w') as f:
            json.dump(shows, f, indent=2, default=str)
        
        print(f"  Progress saved: {len(shows)} shows")
    
    def save_final_dataset(self, filename: str = None) -> str:
        """Save the complete historical dataset"""
        if not self.all_shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_historical_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure directories exist
        os.makedirs(os.path.join(self.project_root, 'data', 'exports'), exist_ok=True)
        os.makedirs(os.path.join(self.project_root, 'data', 'processed'), exist_ok=True)
        
        # Save as CSV
        df = pd.DataFrame(self.all_shows)
        csv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.csv")
        df.to_csv(csv_file, index=False)
        print(f"Historical dataset saved to: {csv_file}")
        
        # Save as JSON
        json_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.json")
        with open(json_file, 'w') as f:
            json.dump(self.all_shows, f, indent=2, default=str)
        print(f"Historical dataset saved to: {json_file}")
        
        # Save as TSV
        tsv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.tsv")
        df.to_csv(tsv_file, index=False, sep='\t')
        print(f"Historical dataset saved to: {tsv_file}")
        
        return csv_file
    
    def print_summary(self):
        """Print a comprehensive summary of the historical data"""
        if not self.all_shows:
            print("No historical shows data found")
            return
        
        print(f"\n=== Historical Data Summary ===")
        print(f"Total shows found: {len(self.all_shows)}")
        
        # Year breakdown
        years = {}
        for show in self.all_shows:
            year = show.get('year', 'Unknown')
            years[year] = years.get(year, 0) + 1
        
        print(f"\n=== Shows by Year ===")
        for year in sorted(years.keys()):
            print(f"{year}: {years[year]} shows")
        
        # Decade breakdown
        decades = {}
        for show in self.all_shows:
            year = show.get('year')
            if year and isinstance(year, int):
                decade = (year // 10) * 10
                decades[decade] = decades.get(decade, 0) + 1
        
        print(f"\n=== Shows by Decade ===")
        for decade in sorted(decades.keys()):
            print(f"{decade}s: {decades[decade]} shows")
        
        # Genre breakdown
        genres = {}
        for show in self.all_shows:
            genre = show.get('genre') or 'Unknown'
            genres[genre] = genres.get(genre, 0) + 1
        
        print(f"\n=== Top Genres ===")
        sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
        for genre, count in sorted_genres[:15]:
            print(f"{genre}: {count}")
        
        # Event type breakdown
        event_types = {
            'Open Mic': len([s for s in self.all_shows if 'Open-Mic' in s.get('title', '')]),
            'Festivals': len([s for s in self.all_shows if 'Festival' in s.get('title', '')]),
            'Special Events': len([s for s in self.all_shows if any(keyword in s.get('title', '').lower() for keyword in ['prom', 'dance', 'special', 'event'])]),
            'Regular Shows': len([s for s in self.all_shows if not any([
                'Open-Mic' in s.get('title', ''),
                'Festival' in s.get('title', ''),
                any(keyword in s.get('title', '').lower() for keyword in ['prom', 'dance', 'special', 'event'])
            ])])
        }
        
        print(f"\n=== Event Types ===")
        for event_type, count in event_types.items():
            print(f"{event_type}: {count}")

def main():
    scraper = VelourHistoricalScraperV2()
    
    try:
        print("Starting comprehensive historical data collection...")
        print("This will take a while - we're collecting 20 years of data!")
        
        # Start with a smaller range to test first
        print("\nTesting with recent years first...")
        test_shows = scraper.scrape_all_historical_data(start_year=2020, end_year=2022)
        
        if test_shows:
            print(f"\nTest successful! Found {len(test_shows)} shows from 2020-2022")
            
            # Ask if we should continue with full historical data
            print(f"\nProceeding with full historical data collection (2006-2026)...")
            all_shows = scraper.scrape_all_historical_data(start_year=2006, end_year=2026)
            
            if all_shows:
                scraper.print_summary()
                scraper.save_final_dataset()
                
                print(f"\n🎉 Historical data collection complete!")
                print(f"Collected {len(all_shows)} shows spanning 20 years!")
            else:
                print("No historical shows found.")
        else:
            print("Test failed. Please check the setup.")
    
    except Exception as e:
        print(f"Error during historical scraping: {e}")

if __name__ == "__main__":
    main()

