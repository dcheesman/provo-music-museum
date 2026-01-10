#!/usr/bin/env python3
"""
Velour Live Historical Show Data Scraper
Scrapes show data from multiple months and years, going back as far as possible
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class VelourHistoricalScraper:
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
        
        # Import the parser
        from parse_velour_calendar import VelourCalendarParser
        self.parser = VelourCalendarParser()
    
    def explore_calendar_navigation(self) -> Dict:
        """Explore the calendar to understand navigation options"""
        print("Exploring calendar navigation...")
        
        try:
            self.driver.get(self.calendar_url)
            time.sleep(3)
            
            # Look for navigation elements
            navigation_info = {
                'current_month': None,
                'available_months': [],
                'navigation_elements': [],
                'page_source_sample': self.driver.page_source[:1000]
            }
            
            # Look for month/year selectors
            selectors = [
                "select[name*='month']", "select[name*='year']", 
                "select[id*='month']", "select[id*='year']",
                "input[name*='month']", "input[name*='year']",
                "a[href*='month']", "a[href*='year']"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        navigation_info['navigation_elements'].append({
                            'type': element.tag_name,
                            'selector': selector,
                            'text': element.text,
                            'value': element.get_attribute('value'),
                            'href': element.get_attribute('href')
                        })
                except:
                    continue
            
            # Look for iframe content
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    iframe_content = self.driver.page_source
                    self.driver.switch_to.default_content()
                    
                    # Look for month/year navigation in iframe
                    month_matches = re.findall(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', iframe_content)
                    year_matches = re.findall(r'(\d{4})', iframe_content)
                    
                    navigation_info['available_months'] = list(set(month_matches))
                    navigation_info['available_years'] = list(set(year_matches))
                    
                except Exception as e:
                    self.driver.switch_to.default_content()
                    print(f"Error exploring iframe: {e}")
            
            return navigation_info
            
        except Exception as e:
            print(f"Error exploring calendar navigation: {e}")
            return {}
    
    def scrape_historical_data(self, start_year: int = 2006, end_year: int = 2026) -> List[Dict]:
        """Scrape historical data from start_year to end_year"""
        print(f"Scraping historical data from {start_year} to {end_year}...")
        
        all_shows = []
        current_year = start_year
        
        while current_year <= end_year:
            print(f"\n=== Scraping Year {current_year} ===")
            
            # Try to scrape each month of the year
            for month_num in range(1, 13):
                month_name = datetime(2000, month_num, 1).strftime('%B')
                print(f"Scraping {month_name} {current_year}...")
                
                try:
                    month_shows = self._scrape_month_year(month_name, current_year)
                    if month_shows:
                        all_shows.extend(month_shows)
                        print(f"  Found {len(month_shows)} shows")
                    else:
                        print(f"  No shows found")
                    
                    time.sleep(2)  # Be respectful
                    
                except Exception as e:
                    print(f"  Error scraping {month_name} {current_year}: {e}")
                    continue
            
            current_year += 1
            
            # Save progress periodically
            if all_shows and len(all_shows) % 100 == 0:
                self._save_progress(all_shows, f"progress_{current_year}")
        
        self.all_shows = all_shows
        print(f"\nTotal historical shows scraped: {len(all_shows)}")
        return all_shows
    
    def _scrape_month_year(self, month: str, year: int) -> List[Dict]:
        """Scrape shows for a specific month and year"""
        try:
            # Navigate to calendar
            self.driver.get(self.calendar_url)
            time.sleep(2)
            
            # Try to navigate to specific month/year
            success = self._navigate_to_month_year(month, year)
            if not success:
                print(f"  Could not navigate to {month} {year}")
                return []
            
            # Get calendar content
            calendar_content = self._get_calendar_content()
            if not calendar_content:
                print(f"  No calendar content found for {month} {year}")
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
                "input[name*='month']", "input[name*='year']"
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
        filename = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename_prefix}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(shows, f, indent=2, default=str)
        
        print(f"  Progress saved to: {filename}")
    
    def save_final_dataset(self, filename: str = None) -> str:
        """Save the complete historical dataset"""
        if not self.all_shows:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_historical_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save as CSV
        df = pd.DataFrame(self.all_shows)
        csv_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}.csv"
        df.to_csv(csv_file, index=False)
        print(f"Historical dataset saved to: {csv_file}")
        
        # Save as JSON
        json_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}.json"
        with open(json_file, 'w') as f:
            json.dump(self.all_shows, f, indent=2, default=str)
        print(f"Historical dataset saved to: {json_file}")
        
        # Save as TSV
        tsv_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}.tsv"
        df.to_csv(tsv_file, index=False, sep='\t')
        print(f"Historical dataset saved to: {tsv_file}")
        
        return csv_file
    
    def print_summary(self):
        """Print a summary of the historical data"""
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
    scraper = VelourHistoricalScraper(headless=True)
    
    try:
        print("=== Velour Live Historical Show Scraper ===\n")
        
        # First, explore the calendar navigation
        print("1. Exploring calendar navigation...")
        nav_info = scraper.explore_calendar_navigation()
        
        print(f"Navigation elements found: {len(nav_info.get('navigation_elements', []))}")
        print(f"Available months: {nav_info.get('available_months', [])}")
        print(f"Available years: {nav_info.get('available_years', [])}")
        
        # Save navigation info
        nav_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/calendar_navigation_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(nav_file, 'w') as f:
            json.dump(nav_info, f, indent=2, default=str)
        print(f"Navigation info saved to: {nav_file}")
        
        # Start with a smaller range to test
        print(f"\n2. Starting historical scraping...")
        print("Note: This will take a while for historical data. Starting with recent years first...")
        
        # Start with recent years to test the approach
        shows = scraper.scrape_historical_data(start_year=2020, end_year=2026)
        
        if shows:
            scraper.print_summary()
            scraper.save_final_dataset()
        else:
            print("No historical shows found. The calendar may not have historical data available.")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
