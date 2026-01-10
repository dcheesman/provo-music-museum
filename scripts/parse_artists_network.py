#!/usr/bin/env python3
"""
Parse Artists and Create Network Graph
Extracts all artists from shows, creates unique artist list, and builds network graph
showing which bands have played together.
"""

import json
import re
import os
from datetime import datetime
from typing import List, Dict, Set, Tuple
from collections import defaultdict, Counter
import pandas as pd

class ArtistParser:
    def __init__(self):
        self.all_shows: List[Dict] = []
        self.unique_artists: Set[str] = set()
        self.artist_shows: Dict[str, List[Dict]] = defaultdict(list)
        self.artist_connections: Dict[Tuple[str, str], int] = defaultdict(int)
        self.normalized_artists: Dict[str, str] = {}  # variant -> normalized
        
    def load_data(self, filepath: str):
        """Load show data from JSON file"""
        print(f"Loading data from {filepath}...")
        with open(filepath, 'r') as f:
            self.all_shows = json.load(f)
        print(f"Loaded {len(self.all_shows)} shows")
    
    def extract_artists_from_show(self, show: Dict) -> List[str]:
        """Extract all artists from a single show"""
        artists = []
        
        # Skip invalid shows
        if not show.get('date') or not show.get('title'):
            return artists
        
        # Skip open mic and other non-band events
        title = show.get('title', '').lower()
        if any(skip in title for skip in ['open-mic', 'open mic', 'prom', 'dance', 'festival']):
            return artists
        
        # Try to extract from artists field
        artists_field = show.get('artists')
        if artists_field:
            artists.extend(self._parse_artist_string(str(artists_field)))
        
        # Try to extract from title field
        title_field = show.get('title', '')
        if title_field:
            # Skip if title is clearly not about artists (dates, numbers, etc.)
            if re.match(r'^\d+$', title_field.strip()) or \
               re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$', title_field.strip(), re.IGNORECASE):
                pass  # Skip these
            else:
                # Remove genre prefix like "(indie-rock) " or "(Rock/Indie) "
                title_clean = re.sub(r'^\([^)]+\)\s*', '', title_field)
                # Remove time prefix like "8pm» "
                title_clean = re.sub(r'^\d+pm[»\s]*', '', title_clean)
                # Remove quotes
                title_clean = title_clean.strip('"').strip()
                
                # Skip generic event titles
                if any(skip in title_clean.lower() for skip in ['cabaret', 'showcase', 'acoustic showcase']):
                    pass
                # If title doesn't have "w/" it might be a list of artists
                elif ' w/ ' not in title_clean and ',' in title_clean:
                    artists.extend(self._parse_artist_string(title_clean))
                elif ' w/ ' in title_clean:
                    # Split headliner and openers
                    parts = title_clean.split(' w/ ', 1)
                    headliner = self._clean_artist_name(parts[0].strip())
                    if headliner:
                        artists.append(headliner)
                    if len(parts) > 1:
                        artists.extend(self._parse_artist_string(parts[1]))
        
        # Try to extract from description if we didn't get anything
        if not artists:
            desc = show.get('description', '')
            if desc:
                # Remove genre and time prefixes
                desc_clean = re.sub(r'^\([^)]+\)\s*', '', desc)
                desc_clean = re.sub(r'^\d+pm[»\s]*', '', desc_clean)
                if ' w/ ' in desc_clean:
                    parts = desc_clean.split(' w/ ', 1)
                    headliner = self._clean_artist_name(parts[0].strip())
                    if headliner:
                        artists.append(headliner)
                    if len(parts) > 1:
                        artists.extend(self._parse_artist_string(parts[1]))
                elif ',' in desc_clean:
                    artists.extend(self._parse_artist_string(desc_clean))
        
        # Clean and normalize
        cleaned_artists = []
        for artist in artists:
            cleaned = self._clean_artist_name(artist)
            if cleaned and len(cleaned) > 1:  # Filter out single characters
                cleaned_artists.append(cleaned)
        
        return list(set(cleaned_artists))  # Remove duplicates within show
    
    def _parse_artist_string(self, artist_string: str) -> List[str]:
        """Parse a string containing multiple artists"""
        if not artist_string or artist_string.lower() in ['none', 'null', '']:
            return []
        
        artists = []
        
        # Split by common separators
        # Handle "and" and "&" specially
        parts = re.split(r',\s*|\s+and\s+|\s+&\s+', artist_string)
        
        for part in parts:
            part = part.strip()
            if part:
                # Handle nested separators
                if ' & ' in part and ',' not in part:
                    # Split "A & B" but not "A, B & C" (already split)
                    subparts = part.split(' & ')
                    artists.extend([p.strip() for p in subparts if p.strip()])
                else:
                    artists.append(part)
        
        return artists
    
    def _clean_artist_name(self, name: str) -> str:
        """Clean and normalize an artist name"""
        if not name:
            return ""
        
        # Remove common prefixes/suffixes
        name = name.strip()
        
        # Remove parenthetical info like "(formerly X)", "(from Y)", "(CD release)"
        name = re.sub(r'\s*\([^)]*formerly[^)]*\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\([^)]*from[^)]*\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\([^)]*cd release[^)]*\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\([^)]*\)', '', name)  # Remove any remaining parentheses
        
        # Remove quotes
        name = name.strip('"').strip("'").strip()
        
        # Remove trailing punctuation
        name = name.rstrip('.,;:')
        
        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Skip if too short or looks like metadata
        if len(name) < 2:
            return ""
        if name.lower() in ['none', 'null', 'tba', 'tbd', 'art', 'poetry', 'music', 'featuring']:
            return ""
        
        # Skip if it's clearly not an artist name (too generic)
        generic_terms = ['cabaret', 'velour', 'showcase', 'night', 'release', 'cd', 'ep']
        if any(term in name.lower() for term in generic_terms):
            return ""
        
        return name
    
    def normalize_artist_name(self, name: str) -> str:
        """Normalize artist name for grouping (case-insensitive, etc.)"""
        normalized = name.lower().strip()
        # Store mapping
        if normalized not in self.normalized_artists:
            self.normalized_artists[normalized] = name
        return normalized
    
    def process_all_shows(self):
        """Process all shows to extract artists and build network"""
        print("\n=== Processing Shows to Extract Artists ===")
        
        shows_with_artists = 0
        total_artists_extracted = 0
        
        for show in self.all_shows:
            artists = self.extract_artists_from_show(show)
            
            if artists:
                shows_with_artists += 1
                total_artists_extracted += len(artists)
                
                # Track which shows each artist played
                for artist in artists:
                    normalized = self.normalize_artist_name(artist)
                    self.unique_artists.add(normalized)
                    self.artist_shows[normalized].append(show)
                
                # Build connections (which artists played together)
                if len(artists) > 1:
                    for i, artist1 in enumerate(artists):
                        for artist2 in artists[i+1:]:
                            norm1 = self.normalize_artist_name(artist1)
                            norm2 = self.normalize_artist_name(artist2)
                            # Store in sorted order for consistency
                            pair = tuple(sorted([norm1, norm2]))
                            self.artist_connections[pair] += 1
        
        print(f"Shows with artists: {shows_with_artists}")
        print(f"Total artist mentions: {total_artists_extracted}")
        print(f"Unique artists/bands: {len(self.unique_artists)}")
        print(f"Artist connections (edges): {len(self.artist_connections)}")
    
    def create_artists_dataset(self) -> pd.DataFrame:
        """Create a dataset of all unique artists with their stats"""
        artists_data = []
        
        for normalized_name in self.unique_artists:
            display_name = self.normalized_artists.get(normalized_name, normalized_name)
            shows = self.artist_shows[normalized_name]
            
            # Count connections
            connection_count = sum(1 for pair in self.artist_connections.keys() 
                                 if normalized_name in pair)
            
            # Get years active
            years = set()
            for show in shows:
                if show.get('year'):
                    years.add(show['year'])
            
            artists_data.append({
                'artist_name': display_name,
                'normalized_name': normalized_name,
                'total_shows': len(shows),
                'connection_count': connection_count,
                'years_active': sorted(list(years)),
                'first_year': min(years) if years else None,
                'last_year': max(years) if years else None,
                'years_span': len(years)
            })
        
        df = pd.DataFrame(artists_data)
        df = df.sort_values('total_shows', ascending=False)
        return df
    
    def create_connections_dataset(self) -> pd.DataFrame:
        """Create a dataset of artist connections (edges)"""
        connections_data = []
        
        for (artist1, artist2), count in self.artist_connections.items():
            name1 = self.normalized_artists.get(artist1, artist1)
            name2 = self.normalized_artists.get(artist2, artist2)
            
            connections_data.append({
                'artist1': name1,
                'artist1_normalized': artist1,
                'artist2': name2,
                'artist2_normalized': artist2,
                'shows_together': count
            })
        
        df = pd.DataFrame(connections_data)
        df = df.sort_values('shows_together', ascending=False)
        return df
    
    def create_network_data(self) -> Dict:
        """Create network data structure for visualization"""
        nodes = []
        edges = []
        
        # Create nodes (artists)
        for normalized_name in self.unique_artists:
            display_name = self.normalized_artists.get(normalized_name, normalized_name)
            shows = self.artist_shows[normalized_name]
            
            # Calculate node size based on number of shows
            node_size = len(shows)
            
            nodes.append({
                'id': normalized_name,
                'label': display_name,
                'size': node_size,
                'shows': node_size
            })
        
        # Create edges (connections)
        for (artist1, artist2), count in self.artist_connections.items():
            edges.append({
                'source': artist1,
                'target': artist2,
                'weight': count,
                'shows_together': count
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'total_shows': len(self.all_shows),
                'created_at': datetime.now().isoformat()
            }
        }
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n=== Artist Network Summary ===")
        print(f"Total unique artists/bands: {len(self.unique_artists)}")
        print(f"Total artist connections: {len(self.artist_connections)}")
        
        # Top artists by show count
        artist_show_counts = {
            self.normalized_artists.get(norm, norm): len(shows)
            for norm, shows in self.artist_shows.items()
        }
        top_artists = sorted(artist_show_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        print("\n=== Top 20 Artists by Show Count ===")
        for i, (artist, count) in enumerate(top_artists, 1):
            print(f"{i:2d}. {artist}: {count} shows")
        
        # Top connections
        top_connections = sorted(self.artist_connections.items(), 
                               key=lambda x: x[1], reverse=True)[:10]
        
        print("\n=== Top 10 Artist Connections ===")
        for i, ((artist1, artist2), count) in enumerate(top_connections, 1):
            name1 = self.normalized_artists.get(artist1, artist1)
            name2 = self.normalized_artists.get(artist2, artist2)
            print(f"{i:2d}. {name1} <-> {name2}: {count} shows together")
    
    def save_all(self, output_dir: str):
        """Save all datasets and network data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save artists dataset
        artists_df = self.create_artists_dataset()
        artists_file = os.path.join(output_dir, f'artists_{timestamp}.csv')
        artists_df.to_csv(artists_file, index=False)
        print(f"\n✅ Artists dataset saved: {artists_file}")
        
        # Save connections dataset
        connections_df = self.create_connections_dataset()
        connections_file = os.path.join(output_dir, f'artist_connections_{timestamp}.csv')
        connections_df.to_csv(connections_file, index=False)
        print(f"✅ Connections dataset saved: {connections_file}")
        
        # Save network data (JSON for visualization)
        network_data = self.create_network_data()
        network_file = os.path.join(output_dir, f'artist_network_{timestamp}.json')
        with open(network_file, 'w') as f:
            json.dump(network_data, f, indent=2, default=str)
        print(f"✅ Network data saved: {network_file}")
        
        # Save summary statistics
        summary = {
            'total_unique_artists': len(self.unique_artists),
            'total_connections': len(self.artist_connections),
            'total_shows_processed': len(self.all_shows),
            'top_artists': [
                {
                    'name': self.normalized_artists.get(norm, norm),
                    'shows': len(shows)
                }
                for norm, shows in sorted(self.artist_shows.items(), 
                                        key=lambda x: len(x[1]), reverse=True)[:50]
            ],
            'top_connections': [
                {
                    'artist1': self.normalized_artists.get(pair[0], pair[0]),
                    'artist2': self.normalized_artists.get(pair[1], pair[1]),
                    'shows_together': count
                }
                for pair, count in sorted(self.artist_connections.items(),
                                        key=lambda x: x[1], reverse=True)[:50]
            ],
            'created_at': datetime.now().isoformat()
        }
        summary_file = os.path.join(output_dir, f'artist_network_summary_{timestamp}.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"✅ Summary saved: {summary_file}")
        
        return {
            'artists': artists_file,
            'connections': connections_file,
            'network': network_file,
            'summary': summary_file
        }

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load the most recent complete dataset
    data_file = os.path.join(
        project_root,
        'data',
        'exports',
        'velour_complete_historical_20260102_205023.json'
    )
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found: {data_file}")
        return
    
    # Initialize parser
    parser = ArtistParser()
    parser.load_data(data_file)
    
    # Process all shows
    parser.process_all_shows()
    
    # Print summary
    parser.print_summary()
    
    # Save all datasets
    output_dir = os.path.join(project_root, 'data', 'processed')
    files = parser.save_all(output_dir)
    
    print(f"\n✅ All artist data processed and saved!")
    print(f"\nFiles created:")
    for key, path in files.items():
        print(f"  {key}: {path}")

if __name__ == "__main__":
    main()

