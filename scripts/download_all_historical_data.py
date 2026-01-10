#!/usr/bin/env python3
"""
Download All Historical Data
Downloads and saves all historical Velour Live data to exports folder
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

class DownloadAllHistoricalData:
    def __init__(self):
        self.base_url = "https://velourlive.com"
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.all_shows: List[Dict] = []
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Import the historical parser
        from parse_velour_historical import VelourHistoricalParser
        self.parser = VelourHistoricalParser()
    
    def download_all_data(self, start_year: int = 2006, end_year: int = 2026) -> List[Dict]:
        """Download ALL historical data from start_year to end_year"""
        print(f"=== Downloading All Historical Velour Live Data ===")
        print(f"Years: {start_year} to {end_year}")
        print(f"Target: Exports folder")
        print()
        
        all_shows = []
        total_months = (end_year - start_year + 1) * 12
        current_month = 0
        
        for year in range(start_year, end_year + 1):
            print(f"📅 Year {year}:")
            year_shows = 0
            
            for month in range(1, 13):
                current_month += 1
                month_name = datetime(2000, month, 1).strftime('%B')
                
                print(f"  [{current_month:3d}/{total_months}] {month_name:9s} {year}...", end=" ")
                
                try:
                    month_shows = self._download_month_year(month, year, month_name)
                    
                    if month_shows:
                        all_shows.extend(month_shows)
                        year_shows += len(month_shows)
                        print(f"✅ {len(month_shows):2d} shows")
                    else:
                        print("❌ No shows")
                    
                    # Save progress every 200 shows
                    if len(all_shows) % 200 == 0 and len(all_shows) > 0:
                        self._save_progress(all_shows, f"progress_{year}_{month:02d}")
                        print(f"    💾 Progress saved: {len(all_shows)} shows")
                    
                    time.sleep(0.2)  # Be respectful
                    
                except Exception as e:
                    print(f"❌ Error: {str(e)[:30]}...")
                    continue
            
            print(f"  📊 Year {year} total: {year_shows} shows")
            print()
        
        self.all_shows = all_shows
        print(f"🎉 Download Complete!")
        print(f"📊 Total shows collected: {len(all_shows)}")
        
        return all_shows
    
    def _download_month_year(self, month: int, year: int, month_name: str) -> List[Dict]:
        """Download shows for a specific month and year"""
        try:
            # Use the discovered URL pattern
            url = f"{self.base_url}/calendar/month.php?month={month}&year={year}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML content using the historical parser
            shows = self.parser.parse_historical_calendar(response.text, month_name, year)
            
            return shows
            
        except Exception as e:
            raise Exception(f"Download error: {e}")
    
    def _save_progress(self, shows: List[Dict], filename_prefix: str):
        """Save progress periodically"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.project_root, 'logs', f"{filename_prefix}_{timestamp}.json")
        
        with open(filename, 'w') as f:
            json.dump(shows, f, indent=2, default=str)
    
    def save_to_exports(self, filename: str = None) -> Dict[str, str]:
        """Save the complete historical dataset to exports folder"""
        if not self.all_shows:
            print("❌ No shows data to save")
            return {}
        
        if filename is None:
            filename = f"velour_complete_historical_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure exports directory exists
        os.makedirs(os.path.join(self.project_root, 'data', 'exports'), exist_ok=True)
        
        files_created = {}
        
        # Save as CSV
        df = pd.DataFrame(self.all_shows)
        csv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.csv")
        df.to_csv(csv_file, index=False)
        files_created['csv'] = csv_file
        print(f"📄 CSV saved: {csv_file}")
        
        # Save as TSV
        tsv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.tsv")
        df.to_csv(tsv_file, index=False, sep='\t')
        files_created['tsv'] = tsv_file
        print(f"📄 TSV saved: {tsv_file}")
        
        # Save as JSON
        json_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.json")
        with open(json_file, 'w') as f:
            json.dump(self.all_shows, f, indent=2, default=str)
        files_created['json'] = json_file
        print(f"📄 JSON saved: {json_file}")
        
        # Create a summary file
        summary = self._create_summary()
        summary_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        files_created['summary'] = summary_file
        print(f"📄 Summary saved: {summary_file}")
        
        return files_created
    
    def _create_summary(self) -> Dict:
        """Create a comprehensive summary of the data"""
        if not self.all_shows:
            return {}
        
        # Year breakdown
        years = {}
        for show in self.all_shows:
            year = show.get('year', 'Unknown')
            years[year] = years.get(year, 0) + 1
        
        # Genre breakdown
        genres = {}
        for show in self.all_shows:
            genre = show.get('genre') or 'Unknown'
            genres[genre] = genres.get(genre, 0) + 1
        
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
        
        return {
            'collection_info': {
                'total_shows': len(self.all_shows),
                'collection_date': datetime.now().isoformat(),
                'venue': 'Velour Live Music Gallery',
                'data_source': 'https://velourlive.com/calendar/month.php',
                'years_covered': list(years.keys()),
                'date_range': {
                    'earliest': min([s.get('date', '') for s in self.all_shows if s.get('date')]),
                    'latest': max([s.get('date', '') for s in self.all_shows if s.get('date')])
                }
            },
            'shows_by_year': years,
            'shows_by_genre': dict(sorted(genres.items(), key=lambda x: x[1], reverse=True)[:20]),
            'event_types': event_types,
            'top_artists': self._get_top_artists(),
            'monthly_averages': self._get_monthly_averages()
        }
    
    def _get_top_artists(self) -> List[Dict]:
        """Get top performing artists"""
        artist_counts = {}
        for show in self.all_shows:
            title = show.get('title', '')
            if title and 'Open-Mic' not in title and 'Festival' not in title:
                # Simple artist extraction
                artists = title.split(' w/ ')[0].strip()
                if artists:
                    artist_counts[artists] = artist_counts.get(artists, 0) + 1
        
        return [{'artist': artist, 'shows': count} for artist, count in sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:20]]
    
    def _get_monthly_averages(self) -> Dict:
        """Get monthly averages across all years"""
        monthly_counts = {}
        for show in self.all_shows:
            month = show.get('month', 'Unknown')
            monthly_counts[month] = monthly_counts.get(month, 0) + 1
        
        return monthly_counts
    
    def print_final_summary(self):
        """Print final summary"""
        if not self.all_shows:
            print("❌ No data to summarize")
            return
        
        print(f"\n{'='*60}")
        print(f"🎉 VELOUR LIVE HISTORICAL DATA DOWNLOAD COMPLETE! 🎉")
        print(f"{'='*60}")
        print(f"📊 Total Shows: {len(self.all_shows):,}")
        print(f"📅 Years Covered: {min(self.all_shows, key=lambda x: x.get('year', 9999)).get('year')} - {max(self.all_shows, key=lambda x: x.get('year', 0)).get('year')}")
        print(f"🏢 Venue: Velour Live Music Gallery")
        print(f"📁 Files saved to: data/exports/")
        print(f"{'='*60}")

def main():
    downloader = DownloadAllHistoricalData()
    
    try:
        print("🚀 Starting complete historical data download...")
        print("This will download 20+ years of Velour Live show data!")
        print()
        
        # Download all data
        all_shows = downloader.download_all_data(start_year=2006, end_year=2026)
        
        if all_shows:
            # Save to exports folder
            print(f"\n💾 Saving data to exports folder...")
            files = downloader.save_to_exports()
            
            # Print final summary
            downloader.print_final_summary()
            
            print(f"\n📁 Files created:")
            for file_type, file_path in files.items():
                print(f"   {file_type.upper()}: {file_path}")
            
        else:
            print("❌ No data downloaded")
    
    except Exception as e:
        print(f"❌ Error during download: {e}")

if __name__ == "__main__":
    main()

