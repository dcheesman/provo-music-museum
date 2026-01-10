#!/usr/bin/env python3
"""
Velour Live Backwards Scraper
Starts from current month and works backwards until no more data is available
"""

import time
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class VelourBackwardsScraper:
    def __init__(self, headless: bool = True):
        self.base_url = "https://velourlive.com"
        self.calendar_url = "https://velourlive.com/calendar/index.php"
        self.all_shows: List[Dict] = []
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
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
        
        # Import the parser
        from parse_velour_calendar import VelourCalendarParser
        self.parser = VelourCalendarParser()
    
    def scrape_backwards_from_current(self) -> List[Dict]:
        """Start from current month and work backwards until no data found"""
        print("=== Velour Live Backwards Scraper ===\n")
        
        # Start from current month
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        print(f"Starting from {current_date.strftime('%B %Y')} and working backwards...")
        
        all_shows = []
        consecutive_empty_months = 0
        max_empty_months = 3  # Stop after 3 consecutive empty months
        
        while consecutive_empty_months < max_empty_months:
            month_name = current_date.strftime('%B')
            year = current_date.year
            
            print(f"\n--- Scraping {month_name} {year} ---")
            
            try:
                month_shows = self._scrape_month_year(month_name, year)
                
                if month_shows:
                    all_shows.extend(month_shows)
                    consecutive_empty_months = 0  # Reset counter
                    print(f"✅ Found {len(month_shows)} shows")
                    
                    # Save progress every 10 shows
                    if len(all_shows) % 10 == 0:
                        self._save_progress(all_shows, f"backwards_progress_{current_date.strftime('%Y%m')}")
                else:
                    consecutive_empty_months += 1
                    print(f"❌ No shows found (empty month #{consecutive_empty_months})")
                
                # Move to previous month
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12)
                else:
                    current_date = current_date.replace(month=current_date.month - 1)
                
                time.sleep(2)  # Be respectful
                
            except Exception as e:
                print(f"❌ Error scraping {month_name} {year}: {e}")
                consecutive_empty_months += 1
                
                # Move to previous month anyway
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12)
                else:
                    current_date = current_date.replace(month=current_date.month - 1)
        
        self.all_shows = all_shows
        print(f"\n=== Backwards Scraping Complete ===")
        print(f"Total shows found: {len(all_shows)}")
        print(f"Stopped after {consecutive_empty_months} consecutive empty months")
        
        return all_shows
    
    def _scrape_month_year(self, month: str, year: int) -> List[Dict]:
        """Scrape shows for a specific month and year"""
        try:
            # Navigate to calendar
            self.driver.get(self.calendar_url)
            time.sleep(3)
            
            # Try to navigate to specific month/year
            success = self._navigate_to_month_year(month, year)
            if not success:
                print(f"  Could not navigate to {month} {year}")
                return []
            
            # Get calendar content
            calendar_content = self._get_calendar_content()
            if not calendar_content:
                print(f"  No calendar content found")
                return []
            
            # Parse the calendar content
            shows = self.parser.parse_calendar_data(calendar_content, month, year)
            
            # Filter out shows that don't match the target year
            filtered_shows = []
            for show in shows:
                if show.get('year') == year and show.get('month') == month:
                    filtered_shows.append(show)
            
            return filtered_shows
            
        except Exception as e:
            print(f"  Error in _scrape_month_year: {e}")
            return []
    
    def _navigate_to_month_year(self, month: str, year: int) -> bool:
        """Try to navigate to a specific month and year"""
        try:
            # Look for month/year navigation elements
            navigation_selectors = [
                "select[name*='month']", "select[name*='year']",
                "select[id*='month']", "select[id*='year']",
                "input[name*='month']", "input[name*='year']",
                "a[href*='month']", "a[href*='year']"
            ]
            
            for selector in navigation_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if 'month' in selector.lower():
                            # Try to select month
                            try:
                                element.click()
                                time.sleep(0.5)
                                
                                # Look for month option
                                month_options = self.driver.find_elements(By.XPATH, f"//option[contains(text(), '{month}')]")
                                if month_options:
                                    month_options[0].click()
                                    time.sleep(0.5)
                                    
                            except:
                                pass
                        
                        elif 'year' in selector.lower():
                            # Try to select year
                            try:
                                element.clear()
                                element.send_keys(str(year))
                                time.sleep(0.5)
                                
                            except:
                                pass
                except:
                    continue
            
            # Look for submit/go button
            submit_selectors = [
                "input[type='submit']", "button[type='submit']",
                "input[value*='Go']", "button[value*='Go']",
                "a[href*='month']", "a[href*='year']"
            ]
            
            for selector in submit_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(2)
                            break
                except:
                    continue
            
            return True
            
        except Exception as e:
            print(f"  Navigation error: {e}")
            return False
    
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
                    
                    if "Open-Mic Night" in page_source or "concert" in page_source.lower() or "show" in page_source.lower():
                        return page_source
                except Exception:
                    self.driver.switch_to.default_content()
                    continue
            
            # If no iframe content, try main page
            page_source = self.driver.page_source
            if "Open-Mic Night" in page_source or "concert" in page_source.lower() or "show" in page_source.lower():
                return page_source
            
            return None
            
        except Exception as e:
            print(f"  Error getting calendar content: {e}")
            return None
    
    def _save_progress(self, shows: List[Dict], filename_prefix: str):
        """Save progress periodically"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.project_root, 'logs', f"{filename_prefix}_{timestamp}.json")
        
        with open(filename, 'w') as f:
            json.dump(shows, f, indent=2, default=str)
        
        print(f"  Progress saved to: {filename}")
    
    def save_final_dataset(self, filename: str = None) -> str:
        """Save the complete historical dataset"""
        if not self.all_shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_backwards_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ensure directories exist
        os.makedirs(os.path.join(self.project_root, 'data', 'exports'), exist_ok=True)
        os.makedirs(os.path.join(self.project_root, 'data', 'processed'), exist_ok=True)
        
        # Save as CSV
        df = pd.DataFrame(self.all_shows)
        csv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.csv")
        df.to_csv(csv_file, index=False)
        print(f"Backwards dataset saved to: {csv_file}")
        
        # Save as JSON
        json_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.json")
        with open(json_file, 'w') as f:
            json.dump(self.all_shows, f, indent=2, default=str)
        print(f"Backwards dataset saved to: {json_file}")
        
        # Save as TSV
        tsv_file = os.path.join(self.project_root, 'data', 'exports', f"{filename}.tsv")
        df.to_csv(tsv_file, index=False, sep='\t')
        print(f"Backwards dataset saved to: {tsv_file}")
        
        return csv_file
    
    def print_summary(self):
        """Print a summary of the backwards scraped data"""
        if not self.all_shows:
            print("No backwards scraped shows data found")
            return
        
        print(f"\n=== Backwards Scraping Summary ===")
        print(f"Total shows found: {len(self.all_shows)}")
        
        # Year breakdown
        years = {}
        for show in self.all_shows:
            year = show.get('year', 'Unknown')
            years[year] = years.get(year, 0) + 1
        
        print(f"\n=== Shows by Year ===")
        for year in sorted(years.keys()):
            print(f"{year}: {years[year]} shows")
        
        # Month breakdown
        months = {}
        for show in self.all_shows:
            month = show.get('month', 'Unknown')
            months[month] = months.get(month, 0) + 1
        
        print(f"\n=== Shows by Month ===")
        for month in sorted(months.keys()):
            print(f"{month}: {months[month]} shows")
        
        # Genre breakdown
        genres = {}
        for show in self.all_shows:
            genre = show.get('genre') or 'Unknown'
            genres[genre] = genres.get(genre, 0) + 1
        
        print(f"\n=== Top Genres ===")
        sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
        for genre, count in sorted_genres[:10]:
            print(f"{genre}: {count}")
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()

def main():
    scraper = VelourBackwardsScraper(headless=True)
    
    try:
        print("Starting backwards scraping from current month...")
        print("This will work backwards until no more data is found.\n")
        
        # Start backwards scraping
        shows = scraper.scrape_backwards_from_current()
        
        if shows:
            scraper.print_summary()
            scraper.save_final_dataset()
            
            print(f"\n🎉 Backwards scraping complete!")
            print(f"Found {len(shows)} total shows")
        else:
            print("No shows found during backwards scraping.")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()

