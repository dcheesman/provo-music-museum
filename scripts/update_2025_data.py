#!/usr/bin/env python3
"""
Update Velour Live Data for Rest of 2025
Scrapes November and December 2025, then merges with existing data
"""

import time
import json
import os
from datetime import datetime
from typing import List, Dict
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Import the historical parser
from parse_velour_historical import VelourHistoricalParser

class Velour2025Updater:
    def __init__(self):
        self.base_url = "https://velourlive.com"
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.new_shows: List[Dict] = []
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        self.parser = VelourHistoricalParser()
    
    def scrape_remaining_2025(self) -> List[Dict]:
        """Scrape November and December 2025 data"""
        print("=== Updating Velour Live Data for Rest of 2025 ===\n")
        print("Scraping November and December 2025...\n")
        
        months_to_scrape = [
            (11, "November", 2025),
            (12, "December", 2025)
        ]
        
        all_shows = []
        
        for month_num, month_name, year in months_to_scrape:
            print(f"Scraping {month_name} {year}...", end=" ")
            
            try:
                url = f"{self.base_url}/calendar/month.php?month={month_num}&year={year}"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                # Parse the HTML content
                shows = self.parser.parse_historical_calendar(response.text, month_name, year)
                
                if shows:
                    all_shows.extend(shows)
                    print(f"✅ Found {len(shows)} shows")
                else:
                    print("❌ No shows found")
                
                time.sleep(0.5)  # Be respectful
                
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        self.new_shows = all_shows
        print(f"\nTotal new shows scraped: {len(all_shows)}")
        
        return all_shows
    
    def load_existing_data(self) -> List[Dict]:
        """Load existing historical data"""
        print("\n=== Loading Existing Data ===")
        
        # Try to load the most recent complete historical dataset
        existing_file = os.path.join(
            self.project_root, 
            'data', 
            'exports', 
            'velour_complete_historical_20251011_150605.json'
        )
        
        if os.path.exists(existing_file):
            print(f"Loading existing data from: {existing_file}")
            with open(existing_file, 'r') as f:
                existing_shows = json.load(f)
            print(f"Loaded {len(existing_shows)} existing shows")
            return existing_shows
        else:
            print("No existing historical data file found. Starting fresh.")
            return []
    
    def merge_data(self, existing_shows: List[Dict], new_shows: List[Dict]) -> List[Dict]:
        """Merge existing and new data, removing duplicates"""
        print("\n=== Merging Data ===")
        
        # Create a set of existing show keys (date + title)
        existing_keys = set()
        for show in existing_shows:
            key = (show.get('date', ''), show.get('title', ''))
            if key != ('', ''):
                existing_keys.add(key)
        
        # Add new shows that aren't duplicates
        merged_shows = existing_shows.copy()
        new_count = 0
        
        for show in new_shows:
            key = (show.get('date', ''), show.get('title', ''))
            if key != ('', '') and key not in existing_keys:
                merged_shows.append(show)
                existing_keys.add(key)
                new_count += 1
        
        print(f"Added {new_count} new shows")
        print(f"Total shows in merged dataset: {len(merged_shows)}")
        
        # Sort by date (handle None values)
        def sort_key(x):
            year = x.get('year') or 0
            month = self._month_to_number(x.get('month') or 'January')
            day = x.get('day') or 0
            return (year, month, day)
        
        merged_shows.sort(key=sort_key)
        
        return merged_shows
    
    def _month_to_number(self, month: str) -> int:
        """Convert month name to number"""
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        return months.get(month, 1)
    
    def save_updated_dataset(self, shows: List[Dict]):
        """Save the updated complete dataset"""
        print("\n=== Saving Updated Dataset ===")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"velour_complete_historical_{timestamp}"
        
        # Ensure directories exist
        os.makedirs(os.path.join(self.project_root, 'data', 'exports'), exist_ok=True)
        os.makedirs(os.path.join(self.project_root, 'data', 'processed'), exist_ok=True)
        
        # Save as CSV
        df = pd.DataFrame(shows)
        csv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.csv")
        df.to_csv(csv_file, index=False)
        print(f"✅ CSV saved: {csv_file}")
        
        # Save as JSON
        json_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.json")
        with open(json_file, 'w') as f:
            json.dump(shows, f, indent=2, default=str)
        print(f"✅ JSON saved: {json_file}")
        
        # Save as TSV
        tsv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.tsv")
        df.to_csv(tsv_file, index=False, sep='\t')
        print(f"✅ TSV saved: {tsv_file}")
        
        # Create summary report
        summary = self._create_summary(shows)
        summary_file = os.path.join(self.project_root, 'data', 'processed', f'velour_summary_report_{timestamp}.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"✅ Summary saved: {summary_file}")
        
        return csv_file
    
    def _create_summary(self, shows: List[Dict]) -> Dict:
        """Create summary statistics"""
        # Filter 2025 shows
        shows_2025 = [s for s in shows if s.get('year') == 2025]
        
        # Group by month
        by_month = {}
        for show in shows_2025:
            month = show.get('month', 'Unknown')
            by_month[month] = by_month.get(month, 0) + 1
        
        # Genre breakdown
        genres = {}
        for show in shows_2025:
            genre = show.get('genre') or 'Unknown'
            genres[genre] = genres.get(genre, 0) + 1
        
        return {
            'total_shows_all_time': len(shows),
            'total_shows_2025': len(shows_2025),
            '2025_by_month': by_month,
            '2025_genres': genres,
            'updated_at': datetime.now().isoformat()
        }
    
    def print_summary(self, shows: List[Dict]):
        """Print a summary of the updated data"""
        print("\n=== Updated Dataset Summary ===")
        print(f"Total shows (all time): {len(shows)}")
        
        # 2025 breakdown
        shows_2025 = [s for s in shows if s.get('year') == 2025]
        print(f"\n2025 shows: {len(shows_2025)}")
        
        by_month = {}
        for show in shows_2025:
            month = show.get('month', 'Unknown')
            by_month[month] = by_month.get(month, 0) + 1
        
        print("\n2025 Shows by Month:")
        for month in ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']:
            count = by_month.get(month, 0)
            print(f"  {month}: {count} shows")

def main():
    updater = Velour2025Updater()
    
    try:
        # Scrape new data
        new_shows = updater.scrape_remaining_2025()
        
        if not new_shows:
            print("\n⚠️  No new shows found. The months may not have data yet, or there may be an issue.")
            return
        
        # Load existing data
        existing_shows = updater.load_existing_data()
        
        # Merge data
        merged_shows = updater.merge_data(existing_shows, new_shows)
        
        # Save updated dataset
        updater.save_updated_dataset(merged_shows)
        
        # Print summary
        updater.print_summary(merged_shows)
        
        print("\n✅ Data update complete!")
        
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

