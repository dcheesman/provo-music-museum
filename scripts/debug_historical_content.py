#!/usr/bin/env python3
"""
Debug Historical Content
Examine what the historical calendar pages actually contain
"""

import requests
from bs4 import BeautifulSoup
import json
import os

def debug_historical_content():
    """Debug what's in the historical calendar pages"""
    print("=== Debugging Historical Calendar Content ===\n")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # Test a few different years and months
    test_cases = [
        (1, 2020, "January 2020"),
        (1, 2021, "January 2021"), 
        (1, 2022, "January 2022"),
        (1, 2023, "January 2023"),
        (1, 2024, "January 2024"),
        (1, 2025, "January 2025"),
        (10, 2025, "October 2025")  # This one we know works
    ]
    
    for month, year, description in test_cases:
        print(f"\n--- {description} ---")
        
        try:
            url = f"https://velourlive.com/calendar/month.php?month={month}&year={year}"
            response = session.get(url, timeout=10)
            
            print(f"Status: {response.status_code}")
            print(f"Content length: {len(response.content)}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for iframes
            iframes = soup.find_all('iframe')
            print(f"Iframes found: {len(iframes)}")
            
            for i, iframe in enumerate(iframes):
                src = iframe.get('src', 'No src')
                print(f"  Iframe {i+1}: {src}")
            
            # Look for calendar indicators
            text_content = soup.get_text()
            calendar_indicators = [
                'open-mic night', 'concert', 'show', 'event', 'performance',
                'calendar', 'month', 'day', 'date'
            ]
            
            found_indicators = []
            for indicator in calendar_indicators:
                if indicator in text_content.lower():
                    found_indicators.append(indicator)
            
            print(f"Calendar indicators found: {found_indicators}")
            
            # Look for specific show patterns
            show_patterns = [
                r'open-mic night',
                r'concert',
                r'show',
                r'event',
                r'performance',
                r'\([^)]*\)\s*[A-Z]',  # Genre patterns
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+'  # Artist name patterns
            ]
            
            import re
            show_matches = []
            for pattern in show_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    show_matches.extend(matches[:3])  # First 3 matches
            
            print(f"Show patterns found: {show_matches[:5]}")  # First 5
            
            # Save a sample of the content for inspection
            if year == 2025 and month == 10:  # Known working case
                sample_file = f"/Users/deancheesman/Dropbox/Provo Music Museum/logs/sample_content_{year}_{month:02d}.html"
                with open(sample_file, 'w') as f:
                    f.write(response.text)
                print(f"Sample content saved to: {sample_file}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_historical_content()

