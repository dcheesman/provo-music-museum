#!/usr/bin/env python3
"""
Velour Live URL Explorer
Explores different URL patterns to find historical data access points
"""

import time
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import os

class VelourURLExplorer:
    def __init__(self):
        self.base_url = "https://velourlive.com"
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def explore_url_patterns(self) -> Dict:
        """Explore different URL patterns to find historical data"""
        print("=== Exploring Velour Live URL Patterns ===\n")
        
        results = {
            'working_urls': [],
            'calendar_variations': [],
            'historical_access': [],
            'api_endpoints': [],
            'archive_links': []
        }
        
        # Test different calendar URL patterns
        calendar_patterns = [
            "/calendar/",
            "/calendar/index.php",
            "/calendar/month.php",
            "/calendar/calendar.php",
            "/events/",
            "/shows/",
            "/schedule/",
            "/archive/",
            "/history/",
            "/past/",
            "/previous/",
            "/old/",
            "/back/",
            "/calendar/month.php?month=1&year=2024",
            "/calendar/month.php?month=1&year=2023",
            "/calendar/month.php?month=1&year=2022",
            "/calendar/month.php?month=1&year=2021",
            "/calendar/month.php?month=1&year=2020",
            "/calendar/month.php?month=1&year=2019",
            "/calendar/month.php?month=1&year=2018",
            "/calendar/month.php?month=1&year=2017",
            "/calendar/month.php?month=1&year=2016",
            "/calendar/month.php?month=1&year=2015",
            "/calendar/month.php?month=1&year=2010",
            "/calendar/month.php?month=1&year=2006"
        ]
        
        print("Testing calendar URL patterns...")
        for pattern in calendar_patterns:
            url = self.base_url + pattern
            result = self._test_url(url)
            if result['status'] == 'success':
                results['working_urls'].append({
                    'url': url,
                    'pattern': pattern,
                    'content_length': result['content_length'],
                    'has_calendar': result['has_calendar'],
                    'has_shows': result['has_shows']
                })
                print(f"✅ {pattern} - {result['content_length']} bytes")
            else:
                print(f"❌ {pattern} - {result['error']}")
        
        # Test month/year parameter combinations
        print(f"\nTesting month/year parameter combinations...")
        for year in range(2006, 2027):
            for month in range(1, 13):
                url = f"{self.base_url}/calendar/month.php?month={month}&year={year}"
                result = self._test_url(url)
                if result['status'] == 'success' and result['has_shows']:
                    results['historical_access'].append({
                        'url': url,
                        'year': year,
                        'month': month,
                        'content_length': result['content_length'],
                        'show_count': result['show_count']
                    })
                    print(f"✅ {year}-{month:02d}: {result['show_count']} shows")
        
        # Look for archive or historical links
        print(f"\nLooking for archive/historical links...")
        archive_patterns = [
            "/archive/",
            "/history/",
            "/past/",
            "/previous/",
            "/old/",
            "/back/",
            "/old-calendar/",
            "/historical/",
            "/legacy/",
            "/vintage/"
        ]
        
        for pattern in archive_patterns:
            url = self.base_url + pattern
            result = self._test_url(url)
            if result['status'] == 'success':
                results['archive_links'].append({
                    'url': url,
                    'pattern': pattern,
                    'content_length': result['content_length']
                })
                print(f"✅ Archive link found: {pattern}")
        
        return results
    
    def _test_url(self, url: str) -> Dict:
        """Test a URL and return information about its content"""
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                soup = BeautifulSoup(content, 'html.parser')
                
                # Check for calendar indicators
                has_calendar = any(indicator in content.lower() for indicator in [
                    'calendar', 'month', 'day', 'date', 'schedule'
                ])
                
                # Check for show indicators
                has_shows = any(indicator in content.lower() for indicator in [
                    'open-mic', 'concert', 'show', 'event', 'performance', 'band', 'artist'
                ])
                
                # Count potential shows
                show_count = 0
                if has_shows:
                    # Look for common show patterns
                    show_patterns = [
                        r'open-mic night',
                        r'concert',
                        r'show',
                        r'event',
                        r'performance',
                        r'\([^)]*\)\s*[A-Z]',  # Genre patterns
                        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+'  # Artist name patterns
                    ]
                    
                    for pattern in show_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        show_count += len(matches)
                
                return {
                    'status': 'success',
                    'content_length': len(content),
                    'has_calendar': has_calendar,
                    'has_shows': has_shows,
                    'show_count': show_count
                }
            else:
                return {
                    'status': 'error',
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def save_results(self, results: Dict):
        """Save exploration results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.project_root, 'logs', f'url_exploration_{timestamp}.json')
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {filename}")
        return filename

def main():
    explorer = VelourURLExplorer()
    
    print("Exploring Velour Live URL patterns to find historical data access...")
    
    results = explorer.explore_url_patterns()
    
    print(f"\n=== Exploration Summary ===")
    print(f"Working URLs: {len(results['working_urls'])}")
    print(f"Historical access points: {len(results['historical_access'])}")
    print(f"Archive links: {len(results['archive_links'])}")
    
    if results['historical_access']:
        print(f"\n=== Historical Data Found ===")
        years = set()
        for access in results['historical_access']:
            years.add(access['year'])
        
        print(f"Years with data: {sorted(years)}")
        print(f"Earliest year: {min(years)}")
        print(f"Latest year: {max(years)}")
    
    explorer.save_results(results)

if __name__ == "__main__":
    main()

