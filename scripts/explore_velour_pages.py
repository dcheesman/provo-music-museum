#!/usr/bin/env python3
"""
Velour Live Page Explorer
Explores different pages and sections of velourlive.com to find show data
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Optional, Set
from datetime import datetime

class VelourPageExplorer:
    def __init__(self, base_url: str = "https://velourlive.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.show_data: List[Dict] = []
        
    def explore_site(self) -> Dict:
        """Explore the site systematically to find show data"""
        print(f"Exploring {self.base_url} for show data...")
        
        # Start with the main page
        main_page_data = self._analyze_page(self.base_url)
        
        # Find all internal links
        internal_links = self._find_internal_links(main_page_data['soup'])
        
        # Explore promising pages
        promising_pages = self._identify_promising_pages(internal_links)
        
        print(f"Found {len(internal_links)} internal links")
        print(f"Identified {len(promising_pages)} promising pages to explore")
        
        # Explore each promising page
        page_results = {}
        for page_url in promising_pages[:10]:  # Limit to first 10 to avoid overwhelming
            print(f"Exploring: {page_url}")
            page_data = self._analyze_page(page_url)
            page_results[page_url] = page_data
            
            # Extract show data if found
            shows = self._extract_show_data(page_data['soup'], page_url)
            if shows:
                self.show_data.extend(shows)
                print(f"  Found {len(shows)} shows")
            
            time.sleep(1)  # Be respectful
        
        return {
            'main_page': main_page_data,
            'internal_links': internal_links,
            'promising_pages': promising_pages,
            'page_results': page_results,
            'total_shows_found': len(self.show_data),
            'show_data': self.show_data
        }
    
    def _analyze_page(self, url: str) -> Dict:
        """Analyze a single page for content and structure"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text()
            
            # Look for show-related patterns
            show_indicators = self._find_show_indicators(text_content, soup)
            
            # Find all links
            links = self._extract_links(soup, url)
            
            return {
                'url': url,
                'status_code': response.status_code,
                'title': soup.title.string if soup.title else 'No title',
                'soup': soup,
                'text_content': text_content,
                'show_indicators': show_indicators,
                'links': links,
                'content_length': len(text_content)
            }
            
        except requests.RequestException as e:
            return {
                'url': url,
                'error': str(e),
                'soup': None,
                'show_indicators': {},
                'links': []
            }
    
    def _find_internal_links(self, soup: BeautifulSoup) -> List[str]:
        """Find all internal links on the page"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(self.base_url, href)
            
            # Only include internal links
            if urlparse(full_url).netloc == urlparse(self.base_url).netloc:
                links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract all links with their text and attributes"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            text = link.get_text(strip=True)
            
            links.append({
                'url': full_url,
                'text': text,
                'href': href,
                'is_internal': urlparse(full_url).netloc == urlparse(self.base_url).netloc
            })
        
        return links
    
    def _identify_promising_pages(self, links: List[str]) -> List[str]:
        """Identify pages that are likely to contain show data"""
        promising_keywords = [
            'shows', 'events', 'concerts', 'calendar', 'schedule', 
            'upcoming', 'past', 'archive', 'gallery', 'photos',
            'bands', 'artists', 'performers', 'music'
        ]
        
        promising_pages = []
        for link in links:
            link_lower = link.lower()
            if any(keyword in link_lower for keyword in promising_keywords):
                promising_pages.append(link)
        
        return promising_pages
    
    def _find_show_indicators(self, text_content: str, soup: BeautifulSoup) -> Dict:
        """Find indicators that suggest show data is present"""
        indicators = {
            'date_patterns': [],
            'time_patterns': [],
            'venue_mentions': [],
            'artist_mentions': [],
            'show_keywords': [],
            'ticket_mentions': [],
            'price_mentions': []
        }
        
        text_lower = text_content.lower()
        
        # Date patterns
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',  # DD Month YYYY
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'  # Day names
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            indicators['date_patterns'].extend(matches)
        
        # Time patterns
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b',  # 7:30 PM
            r'\b\d{1,2}:\d{2}\b',  # 19:30
            r'\b(?:doors|show|start)\s*(?:at|@)?\s*\d{1,2}:\d{2}\b'  # doors at 7:30
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            indicators['time_patterns'].extend(matches)
        
        # Show-related keywords
        show_keywords = [
            'show', 'concert', 'event', 'performance', 'gig', 'venue', 
            'ticket', 'doors', 'opener', 'headliner', 'band', 'artist',
            'music', 'live', 'stage', 'theater', 'theatre'
        ]
        
        for keyword in show_keywords:
            if keyword in text_lower:
                indicators['show_keywords'].append(keyword)
        
        # Venue mentions
        venue_keywords = ['velour', 'venue', 'stage', 'theater', 'theatre', 'club', 'bar', 'gallery']
        for keyword in venue_keywords:
            if keyword in text_lower:
                indicators['venue_mentions'].append(keyword)
        
        # Ticket mentions
        ticket_keywords = ['ticket', 'price', 'cost', '$', 'free', 'donation', 'cover']
        for keyword in ticket_keywords:
            if keyword in text_lower:
                indicators['ticket_mentions'].append(keyword)
        
        return indicators
    
    def _extract_show_data(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract structured show data from a page"""
        shows = []
        
        # Look for common show data patterns
        # This is a basic implementation - would need to be customized based on actual site structure
        
        # Look for date/time patterns in the content
        text_content = soup.get_text()
        
        # Find potential show entries by looking for date patterns
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        dates = re.findall(date_pattern, text_content)
        
        for date in dates:
            # Try to find context around the date
            show_entry = {
                'date': date,
                'source_url': page_url,
                'raw_text': text_content[:500],  # First 500 chars for context
                'extracted_at': datetime.now().isoformat()
            }
            shows.append(show_entry)
        
        return shows
    
    def save_results(self, results: Dict, filename: str = None):
        """Save exploration results to a file"""
        if filename is None:
            filename = f"velour_exploration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = f"/Users/deancheesman/Dropbox/Provo Music Museum/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to: {filepath}")
        return filepath

def main():
    explorer = VelourPageExplorer()
    
    print("=== Velour Live Page Exploration ===\n")
    
    # Explore the site
    results = explorer.explore_site()
    
    # Print summary
    print(f"\n=== Exploration Summary ===")
    print(f"Total internal links found: {len(results['internal_links'])}")
    print(f"Promising pages identified: {len(results['promising_pages'])}")
    print(f"Pages explored: {len(results['page_results'])}")
    print(f"Total shows found: {results['total_shows_found']}")
    
    # Show promising pages
    print(f"\n=== Promising Pages ===")
    for i, page in enumerate(results['promising_pages'][:10], 1):
        print(f"{i}. {page}")
    
    # Show show data if found
    if results['show_data']:
        print(f"\n=== Show Data Found ===")
        for i, show in enumerate(results['show_data'][:5], 1):  # Show first 5
            print(f"{i}. Date: {show.get('date', 'N/A')}")
            print(f"   Source: {show.get('source_url', 'N/A')}")
            print(f"   Context: {show.get('raw_text', '')[:100]}...")
            print()
    
    # Save results
    filepath = explorer.save_results(results)
    
    print(f"\n=== Next Steps ===")
    if results['total_shows_found'] > 0:
        print("✓ Show data found! Review the results and refine the extraction logic.")
    else:
        print("⚠ No show data found in initial exploration.")
        print("  - The site might use JavaScript to load content dynamically")
        print("  - Show data might be in a different format or location")
        print("  - Consider using Selenium for dynamic content")
    
    print(f"  - Detailed results saved to: {filepath}")

if __name__ == "__main__":
    main()
