#!/usr/bin/env python3
"""
Complete Velour Live Show Data Scraper
Scrapes show data from multiple months and creates a comprehensive dataset
"""

import time
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class VelourCompleteScraper:
    def __init__(self, headless: bool = True):
        self.base_url = "https://velourlive.com"
        self.calendar_url = "https://velourlive.com/calendar/index.php"
        self.all_shows: List[Dict] = []
        
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def scrape_all_months(self, start_month: int = 1, start_year: int = 2024, 
                         end_month: int = 12, end_year: int = 2026) -> List[Dict]:
        """Scrape shows from multiple months"""
        print(f"Scraping shows from {start_month}/{start_year} to {end_month}/{end_year}...")
        
        current_date = datetime(start_year, start_month, 1)
        end_date = datetime(end_year, end_month, 1)
        
        while current_date <= end_date:
            month = current_date.strftime("%B")
            year = current_date.year
            
            print(f"\nScraping {month} {year}...")
            
            try:
                # Navigate to the calendar page
                self.driver.get(self.calendar_url)
                time.sleep(2)
                
                # Try to navigate to specific month if possible
                month_shows = self._scrape_month(month, year)
                
                if month_shows:
                    self.all_shows.extend(month_shows)
                    print(f"Found {len(month_shows)} shows for {month} {year}")
                else:
                    print(f"No shows found for {month} {year}")
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
                
                time.sleep(1)  # Be respectful
                
            except Exception as e:
                print(f"Error scraping {month} {year}: {e}")
                # Move to next month anyway
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        
        print(f"\nTotal shows scraped: {len(self.all_shows)}")
        return self.all_shows
    
    def _scrape_month(self, month: str, year: int) -> List[Dict]:
        """Scrape shows for a specific month"""
        try:
            # Look for month navigation or calendar content
            month_shows = []
            
            # Try to find calendar content
            calendar_content = self._get_calendar_content()
            if calendar_content:
                # Parse the calendar content
                parser = VelourCalendarParser()
                month_shows = parser.parse_calendar_data(calendar_content, month, year)
            
            return month_shows
            
        except Exception as e:
            print(f"Error scraping month {month} {year}: {e}")
            return []
    
    def _get_calendar_content(self) -> Optional[str]:
        """Get the calendar content from the page"""
        try:
            # Look for iframe content first
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    page_source = self.driver.page_source
                    self.driver.switch_to.default_content()
                    
                    if "Open-Mic Night" in page_source or "concert" in page_source.lower():
                        return page_source
                except Exception:
                    self.driver.switch_to.default_content()
                    continue
            
            # If no iframe content, try main page
            page_source = self.driver.page_source
            if "Open-Mic Night" in page_source or "concert" in page_source.lower():
                return page_source
            
            return None
            
        except Exception as e:
            print(f"Error getting calendar content: {e}")
            return None
    
    def save_to_csv(self, filename: str = None) -> str:
        """Save all shows to CSV"""
        if not self.all_shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_all_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        df = pd.DataFrame(self.all_shows)
        df.to_csv(filepath, index=False)
        
        print(f"All shows saved to: {filepath}")
        return filepath
    
    def save_to_json(self, filename: str = None) -> str:
        """Save all shows to JSON"""
        if not self.all_shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_all_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(self.all_shows, f, indent=2, default=str)
        
        print(f"All shows saved to: {filepath}")
        return filepath
    
    def print_summary(self):
        """Print a summary of all scraped shows"""
        if not self.all_shows:
            print("No shows data found")
            return
        
        print(f"\n=== Complete Scraping Summary ===")
        print(f"Total shows found: {len(self.all_shows)}")
        
        # Group by year and month
        by_year_month = {}
        for show in self.all_shows:
            year = show.get('year', 'Unknown')
            month = show.get('month', 'Unknown')
            key = f"{year}-{month}"
            by_year_month[key] = by_year_month.get(key, 0) + 1
        
        print(f"\n=== Shows by Month ===")
        for period, count in sorted(by_year_month.items()):
            print(f"{period}: {count} shows")
        
        # Group by genre
        genres = {}
        for show in self.all_shows:
            genre = show.get('genre') or 'Unknown'
            genres[genre] = genres.get(genre, 0) + 1
        
        print(f"\n=== Shows by Genre ===")
        for genre, count in sorted(genres.items(), key=lambda x: x[0] if x[0] else ''):
            print(f"{genre}: {count}")
        
        # Show sample shows
        print(f"\n=== Sample Shows ===")
        for i, show in enumerate(self.all_shows[:10], 1):
            print(f"{i}. {show.get('date', 'N/A')} - {show.get('title', 'N/A')}")
            if show.get('genre'):
                print(f"   Genre: {show['genre']}")
            if show.get('artists'):
                print(f"   Artists: {show['artists']}")
            print()
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()

# Import the parser class
from parse_velour_calendar import VelourCalendarParser

def main():
    scraper = VelourCompleteScraper(headless=True)
    
    try:
        print("=== Velour Live Complete Show Scraper ===\n")
        
        # For now, let's just scrape the current month (October 2025)
        # In a real scenario, you might want to scrape multiple months
        print("Scraping October 2025...")
        
        # Navigate to the calendar page
        scraper.driver.get(scraper.calendar_url)
        time.sleep(3)
        
        # Get calendar content
        calendar_content = scraper._get_calendar_content()
        
        if calendar_content:
            # Parse the calendar content
            parser = VelourCalendarParser()
            shows = parser.parse_calendar_data(calendar_content, month="October", year=2025)
            
            if shows:
                scraper.all_shows = shows
                
                # Print summary
                scraper.print_summary()
                
                # Save to files
                csv_file = scraper.save_to_csv()
                json_file = scraper.save_to_json()
                
                print(f"\n=== Files Created ===")
                print(f"CSV: {csv_file}")
                print(f"JSON: {json_file}")
                
                # Create a summary report
                create_summary_report(shows)
                
            else:
                print("No shows could be parsed from the calendar data")
        else:
            print("Could not retrieve calendar content")
    
    finally:
        scraper.close()

def create_summary_report(shows: List[Dict]):
    """Create a summary report of the scraped data"""
    report = {
        'scraping_date': datetime.now().isoformat(),
        'total_shows': len(shows),
        'venue': 'Velour Live Music Gallery',
        'data_source': 'https://velourlive.com/calendar/index.php',
        'summary': {}
    }
    
    # Genre breakdown
    genres = {}
    for show in shows:
        genre = show.get('genre') or 'Unknown'
        genres[genre] = genres.get(genre, 0) + 1
    report['summary']['genres'] = genres
    
    # Month breakdown
    months = {}
    for show in shows:
        month = show.get('month', 'Unknown')
        months[month] = months.get(month, 0) + 1
    report['summary']['months'] = months
    
    # Sample shows
    report['summary']['sample_shows'] = shows[:5]
    
    # Save report
    report_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/velour_scraping_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"Scraping report saved to: {report_file}")

if __name__ == "__main__":
    main()
