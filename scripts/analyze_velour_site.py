#!/usr/bin/env python3
"""
Velour Live Website Analysis Tool
Analyzes the structure of velourlive.com to determine the best approach for data extraction
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Optional

class VelourSiteAnalyzer:
    def __init__(self, base_url: str = "https://velourlive.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def analyze_site_structure(self) -> Dict:
        """Analyze the main site structure and identify data sources"""
        print(f"Analyzing {self.base_url}...")
        
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            analysis = {
                'main_page': {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', ''),
                    'title': soup.title.string if soup.title else 'No title',
                    'has_javascript': self._check_javascript_usage(soup),
                    'potential_data_sources': self._find_data_sources(soup, response.text)
                }
            }
            
            # Look for common show/event related patterns
            analysis['show_patterns'] = self._find_show_patterns(soup, response.text)
            
            # Check for API endpoints
            analysis['api_endpoints'] = self._find_api_endpoints(response.text)
            
            return analysis
            
        except requests.RequestException as e:
            print(f"Error analyzing site: {e}")
            return {'error': str(e)}
    
    def _check_javascript_usage(self, soup: BeautifulSoup) -> Dict:
        """Check if the site heavily relies on JavaScript for content loading"""
        scripts = soup.find_all('script')
        js_indicators = {
            'total_scripts': len(scripts),
            'external_scripts': len([s for s in scripts if s.get('src')]),
            'inline_scripts': len([s for s in scripts if not s.get('src')]),
            'has_react': any('react' in str(s).lower() for s in scripts),
            'has_vue': any('vue' in str(s).lower() for s in scripts),
            'has_angular': any('angular' in str(s).lower() for s in scripts)
        }
        return js_indicators
    
    def _find_data_sources(self, soup: BeautifulSoup, html_content: str) -> List[Dict]:
        """Find potential data sources like JSON-LD, microdata, or API calls"""
        sources = []
        
        # Look for JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                sources.append({
                    'type': 'json_ld',
                    'data': data,
                    'description': 'Structured data found'
                })
            except json.JSONDecodeError:
                pass
        
        # Look for microdata
        microdata_items = soup.find_all(attrs={'itemscope': True})
        if microdata_items:
            sources.append({
                'type': 'microdata',
                'count': len(microdata_items),
                'description': 'Microdata markup found'
            })
        
        # Look for data attributes
        data_attrs = soup.find_all(attrs=lambda x: x and any(attr.startswith('data-') for attr in x.keys()))
        if data_attrs:
            sources.append({
                'type': 'data_attributes',
                'count': len(data_attrs),
                'description': 'HTML5 data attributes found'
            })
        
        return sources
    
    def _find_show_patterns(self, soup: BeautifulSoup, html_content: str) -> Dict:
        """Look for patterns that might indicate show/event data"""
        patterns = {
            'show_keywords': [],
            'date_patterns': [],
            'venue_mentions': [],
            'artist_mentions': []
        }
        
        # Common show-related keywords
        show_keywords = ['show', 'concert', 'event', 'performance', 'gig', 'venue', 'ticket', 'date', 'time']
        text_content = soup.get_text().lower()
        
        for keyword in show_keywords:
            if keyword in text_content:
                patterns['show_keywords'].append(keyword)
        
        # Look for date patterns
        date_patterns = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', html_content)
        patterns['date_patterns'] = list(set(date_patterns))
        
        # Look for venue mentions
        venue_keywords = ['velour', 'venue', 'stage', 'theater', 'theatre', 'club', 'bar']
        for keyword in venue_keywords:
            if keyword in text_content:
                patterns['venue_mentions'].append(keyword)
        
        return patterns
    
    def _find_api_endpoints(self, html_content: str) -> List[Dict]:
        """Look for API endpoints in the HTML content"""
        endpoints = []
        
        # Common API patterns
        api_patterns = [
            r'["\']([^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*\.json[^"\']*)["\']',
            r'["\']([^"\']*\.xml[^"\']*)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.get\(["\']([^"\']+)["\']',
            r'\.get\(["\']([^"\']+)["\']'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('/') or match.startswith('http'):
                    endpoints.append({
                        'url': match,
                        'pattern': pattern,
                        'description': 'Potential API endpoint'
                    })
        
        return endpoints
    
    def check_robots_txt(self) -> Dict:
        """Check robots.txt for scraping guidelines"""
        try:
            response = self.session.get(f"{self.base_url}/robots.txt")
            if response.status_code == 200:
                return {
                    'exists': True,
                    'content': response.text,
                    'allows_scraping': 'Disallow' not in response.text or '/api' not in response.text
                }
            else:
                return {'exists': False}
        except requests.RequestException:
            return {'exists': False, 'error': 'Could not fetch robots.txt'}
    
    def test_common_endpoints(self) -> Dict:
        """Test common API endpoints that might contain show data"""
        common_endpoints = [
            '/api/shows',
            '/api/events',
            '/api/concerts',
            '/shows.json',
            '/events.json',
            '/api/v1/shows',
            '/api/v1/events',
            '/data/shows',
            '/data/events'
        ]
        
        results = {}
        for endpoint in common_endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                response = self.session.get(url, timeout=5)
                results[endpoint] = {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', ''),
                    'content_length': len(response.content),
                    'is_json': 'application/json' in response.headers.get('content-type', ''),
                    'accessible': response.status_code == 200
                }
                
                if response.status_code == 200 and 'application/json' in response.headers.get('content-type', ''):
                    try:
                        data = response.json()
                        results[endpoint]['data_sample'] = str(data)[:200] + '...' if len(str(data)) > 200 else str(data)
                    except json.JSONDecodeError:
                        pass
                        
            except requests.RequestException as e:
                results[endpoint] = {'error': str(e)}
            
            time.sleep(0.5)  # Be respectful
        
        return results

def main():
    analyzer = VelourSiteAnalyzer()
    
    print("=== Velour Live Website Analysis ===\n")
    
    # Analyze main site structure
    print("1. Analyzing main site structure...")
    structure_analysis = analyzer.analyze_site_structure()
    print(f"Status: {structure_analysis.get('main_page', {}).get('status_code', 'Error')}")
    print(f"Title: {structure_analysis.get('main_page', {}).get('title', 'N/A')}")
    
    js_info = structure_analysis.get('main_page', {}).get('has_javascript', {})
    print(f"JavaScript usage: {js_info.get('total_scripts', 0)} scripts")
    print(f"External scripts: {js_info.get('external_scripts', 0)}")
    print(f"Uses React/Vue/Angular: {js_info.get('has_react', False)}/{js_info.get('has_vue', False)}/{js_info.get('has_angular', False)}")
    
    # Check data sources
    data_sources = structure_analysis.get('main_page', {}).get('potential_data_sources', [])
    print(f"\n2. Data sources found: {len(data_sources)}")
    for source in data_sources:
        print(f"  - {source['type']}: {source['description']}")
    
    # Check show patterns
    show_patterns = structure_analysis.get('show_patterns', {})
    print(f"\n3. Show-related patterns:")
    print(f"  - Keywords found: {', '.join(show_patterns.get('show_keywords', []))}")
    print(f"  - Date patterns: {show_patterns.get('date_patterns', [])}")
    print(f"  - Venue mentions: {', '.join(show_patterns.get('venue_mentions', []))}")
    
    # Check API endpoints
    api_endpoints = structure_analysis.get('api_endpoints', [])
    print(f"\n4. Potential API endpoints: {len(api_endpoints)}")
    for endpoint in api_endpoints[:5]:  # Show first 5
        print(f"  - {endpoint['url']}")
    
    # Check robots.txt
    print(f"\n5. Checking robots.txt...")
    robots_info = analyzer.check_robots_txt()
    print(f"  - Exists: {robots_info.get('exists', False)}")
    if robots_info.get('allows_scraping'):
        print("  - Scraping appears to be allowed")
    else:
        print("  - Scraping may be restricted")
    
    # Test common endpoints
    print(f"\n6. Testing common API endpoints...")
    endpoint_results = analyzer.test_common_endpoints()
    accessible_endpoints = [ep for ep, result in endpoint_results.items() if result.get('accessible', False)]
    print(f"  - Accessible endpoints: {len(accessible_endpoints)}")
    for endpoint in accessible_endpoints:
        result = endpoint_results[endpoint]
        print(f"    * {endpoint}: {result.get('content_type', 'unknown')} ({result.get('content_length', 0)} bytes)")
        if result.get('data_sample'):
            print(f"      Sample: {result['data_sample']}")
    
    # Save detailed results
    with open('/Users/deancheesman/Dropbox/Provo Music Museum/site_analysis.json', 'w') as f:
        json.dump({
            'structure_analysis': structure_analysis,
            'robots_info': robots_info,
            'endpoint_results': endpoint_results
        }, f, indent=2)
    
    print(f"\n=== Analysis Complete ===")
    print(f"Detailed results saved to: site_analysis.json")
    
    # Recommendations
    print(f"\n=== Recommendations ===")
    if accessible_endpoints:
        print("✓ API endpoints found - consider using these for data extraction")
    elif js_info.get('total_scripts', 0) > 5:
        print("⚠ Site uses JavaScript heavily - may need Selenium/Playwright for scraping")
    else:
        print("✓ Site appears to be mostly static - BeautifulSoup should work well")
    
    if show_patterns.get('show_keywords'):
        print("✓ Show-related content detected - good target for scraping")
    else:
        print("⚠ Limited show-related content found on main page - may need to explore other pages")

if __name__ == "__main__":
    main()
