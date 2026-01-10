#!/usr/bin/env python3
"""
Velour Live Show Data Scraper
Scrapes show data from velourlive.com using Selenium to handle dynamic content
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
from bs4 import BeautifulSoup

class VelourScraper:
    def __init__(self, headless: bool = True):
        self.base_url = "https://velourlive.com"
        self.calendar_url = "https://velourlive.com/calendar/index.php"
        self.shows_data: List[Dict] = []
        
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
    
    def scrape_all_shows(self) -> List[Dict]:
        """Scrape all available show data from the calendar"""
        print(f"Scraping shows from {self.calendar_url}...")
        
        try:
            # Navigate to the calendar page
            self.driver.get(self.calendar_url)
            time.sleep(3)  # Wait for page to load
            
            # Check if we can access the calendar
            if "calendar" not in self.driver.title.lower():
                print("Warning: Calendar page may not have loaded correctly")
            
            # Look for different ways the calendar might be structured
            shows = []
            
            # Method 1: Look for table-based calendar
            table_shows = self._scrape_table_calendar()
            if table_shows:
                shows.extend(table_shows)
                print(f"Found {len(table_shows)} shows in table format")
            
            # Method 2: Look for list-based events
            list_shows = self._scrape_list_events()
            if list_shows:
                shows.extend(list_shows)
                print(f"Found {len(list_shows)} shows in list format")
            
            # Method 3: Look for iframe content
            iframe_shows = self._scrape_iframe_content()
            if iframe_shows:
                shows.extend(iframe_shows)
                print(f"Found {len(iframe_shows)} shows in iframe content")
            
            # Method 4: Look for any clickable elements that might be shows
            clickable_shows = self._scrape_clickable_elements()
            if clickable_shows:
                shows.extend(clickable_shows)
                print(f"Found {len(clickable_shows)} shows from clickable elements")
            
            # Remove duplicates based on date and title
            unique_shows = self._remove_duplicates(shows)
            
            self.shows_data = unique_shows
            print(f"Total unique shows found: {len(unique_shows)}")
            
            return unique_shows
            
        except Exception as e:
            print(f"Error scraping shows: {e}")
            return []
    
    def _scrape_table_calendar(self) -> List[Dict]:
        """Scrape shows from a table-based calendar"""
        shows = []
        
        try:
            # Look for tables that might contain calendar data
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 2:  # At least date and event info
                        show_data = self._extract_show_from_row(cells)
                        if show_data:
                            shows.append(show_data)
        
        except Exception as e:
            print(f"Error scraping table calendar: {e}")
        
        return shows
    
    def _scrape_list_events(self) -> List[Dict]:
        """Scrape shows from a list-based event display"""
        shows = []
        
        try:
            # Look for common event list selectors
            event_selectors = [
                "div.event", "div.show", "div.concert", "li.event", "li.show",
                ".event-item", ".show-item", ".concert-item", ".calendar-event"
            ]
            
            for selector in event_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        show_data = self._extract_show_from_element(element)
                        if show_data:
                            shows.append(show_data)
                except NoSuchElementException:
                    continue
        
        except Exception as e:
            print(f"Error scraping list events: {e}")
        
        return shows
    
    def _scrape_iframe_content(self) -> List[Dict]:
        """Scrape shows from iframe content"""
        shows = []
        
        try:
            # Look for iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            for iframe in iframes:
                try:
                    # Switch to iframe
                    self.driver.switch_to.frame(iframe)
                    
                    # Look for content in the iframe
                    iframe_shows = self._scrape_table_calendar()
                    if not iframe_shows:
                        iframe_shows = self._scrape_list_events()
                    
                    shows.extend(iframe_shows)
                    
                    # Switch back to main content
                    self.driver.switch_to.default_content()
                    
                except Exception as e:
                    print(f"Error scraping iframe: {e}")
                    self.driver.switch_to.default_content()
        
        except Exception as e:
            print(f"Error scraping iframe content: {e}")
        
        return shows
    
    def _scrape_clickable_elements(self) -> List[Dict]:
        """Scrape shows by looking for clickable elements"""
        shows = []
        
        try:
            # Look for clickable elements that might be shows
            clickable_selectors = [
                "a[href*='show']", "a[href*='event']", "a[href*='concert']",
                "div[onclick]", "span[onclick]", "td[onclick]"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        show_data = self._extract_show_from_element(element)
                        if show_data:
                            shows.append(show_data)
                except NoSuchElementException:
                    continue
        
        except Exception as e:
            print(f"Error scraping clickable elements: {e}")
        
        return shows
    
    def _extract_show_from_row(self, cells) -> Optional[Dict]:
        """Extract show data from a table row"""
        try:
            show_data = {
                'date': None,
                'time': None,
                'title': None,
                'venue': 'Velour Live Music Gallery',
                'description': None,
                'raw_text': ' '.join([cell.text for cell in cells]),
                'source_url': self.driver.current_url,
                'extracted_at': datetime.now().isoformat()
            }
            
            # Try to extract date from first cell
            if cells[0].text.strip():
                date_text = cells[0].text.strip()
                show_data['date'] = self._parse_date(date_text)
            
            # Try to extract title/description from other cells
            for i, cell in enumerate(cells[1:], 1):
                cell_text = cell.text.strip()
                if cell_text and not show_data['title']:
                    show_data['title'] = cell_text
                elif cell_text and show_data['title']:
                    show_data['description'] = cell_text
                    break
            
            # Only return if we have some meaningful data
            if show_data['date'] or show_data['title']:
                return show_data
            
        except Exception as e:
            print(f"Error extracting show from row: {e}")
        
        return None
    
    def _extract_show_from_element(self, element) -> Optional[Dict]:
        """Extract show data from a single element"""
        try:
            text = element.text.strip()
            if not text or len(text) < 5:  # Skip very short text
                return None
            
            show_data = {
                'date': None,
                'time': None,
                'title': text,
                'venue': 'Velour Live Music Gallery',
                'description': None,
                'raw_text': text,
                'source_url': self.driver.current_url,
                'extracted_at': datetime.now().isoformat()
            }
            
            # Try to extract date from the text
            date_match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
            if date_match:
                show_data['date'] = self._parse_date(date_match.group())
            
            # Try to extract time
            time_match = re.search(r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b', text)
            if time_match:
                show_data['time'] = time_match.group()
            
            return show_data
            
        except Exception as e:
            print(f"Error extracting show from element: {e}")
        
        return None
    
    def _parse_date(self, date_text: str) -> Optional[str]:
        """Parse date text into a standard format"""
        try:
            # Common date formats
            date_formats = [
                '%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y',
                '%B %d, %Y', '%b %d, %Y', '%B %d', '%b %d',
                '%d/%m/%Y', '%d-%m-%Y'
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # If no format matches, return the original text
            return date_text
            
        except Exception as e:
            print(f"Error parsing date '{date_text}': {e}")
            return date_text
    
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
        if not self.shows_data:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        df = pd.DataFrame(self.shows_data)
        df.to_csv(filepath, index=False)
        
        print(f"Shows data saved to: {filepath}")
        return filepath
    
    def save_to_json(self, filename: str = None) -> str:
        """Save shows data to JSON file"""
        if not self.shows_data:
            print("No shows data to save")
            return ""
        
        if filename is None:
            filename = f"velour_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(self.shows_data, f, indent=2, default=str)
        
        print(f"Shows data saved to: {filepath}")
        return filepath
    
    def print_summary(self):
        """Print a summary of scraped data"""
        if not self.shows_data:
            print("No shows data found")
            return
        
        print(f"\n=== Scraping Summary ===")
        print(f"Total shows found: {len(self.shows_data)}")
        
        # Show first few shows as examples
        print(f"\n=== Sample Shows ===")
        for i, show in enumerate(self.shows_data[:5], 1):
            print(f"{i}. Date: {show.get('date', 'N/A')}")
            print(f"   Time: {show.get('time', 'N/A')}")
            print(f"   Title: {show.get('title', 'N/A')}")
            print(f"   Venue: {show.get('venue', 'N/A')}")
            print()
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()

def main():
    scraper = VelourScraper(headless=True)
    
    try:
        print("=== Velour Live Show Scraper ===\n")
        
        # Scrape all shows
        shows = scraper.scrape_all_shows()
        
        if shows:
            # Print summary
            scraper.print_summary()
            
            # Save to files
            csv_file = scraper.save_to_csv()
            json_file = scraper.save_to_json()
            
            print(f"\n=== Files Created ===")
            print(f"CSV: {csv_file}")
            print(f"JSON: {json_file}")
            
        else:
            print("No shows found. The site structure may have changed or require different scraping approach.")
            
            # Save the page source for debugging
            page_source = scraper.driver.page_source
            debug_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/velour_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_file, 'w') as f:
                f.write(page_source)
            print(f"Page source saved to: {debug_file}")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
