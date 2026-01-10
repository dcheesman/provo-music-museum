#!/usr/bin/env python3
"""
Enhance Network Data with Show Details
Adds show dates and details to network edges for visualization
"""

import json
import os
from collections import defaultdict
from datetime import datetime

def enhance_network_with_shows():
    """Enhance network JSON with show details for each connection"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load network data
    network_file = os.path.join(
        project_root,
        'data',
        'processed',
        'artist_network_20260102_211457.json'
    )
    
    # Load original show data
    shows_file = os.path.join(
        project_root,
        'data',
        'exports',
        'velour_complete_historical_20260102_205023.json'
    )
    
    print("Loading network data...")
    with open(network_file, 'r') as f:
        network_data = json.load(f)
    
    print("Loading show data...")
    with open(shows_file, 'r') as f:
        all_shows = json.load(f)
    
    # Build a map of artist pairs to shows
    print("Building artist pair to shows mapping...")
    pair_to_shows = defaultdict(list)
    
    for show in all_shows:
        if not show.get('date') or not show.get('title'):
            continue
        
        # Skip open mic and other non-band events
        title = show.get('title', '').lower()
        if any(skip in title for skip in ['open-mic', 'open mic', 'prom', 'dance', 'festival']):
            continue
        
        # Extract artists from the show (simplified version)
        artists = []
        
        # From artists field
        if show.get('artists'):
            artist_str = str(show['artists']).strip()
            if artist_str and artist_str.lower() not in ['none', 'null']:
                # Simple split by comma
                artists.extend([a.strip() for a in artist_str.split(',') if a.strip()])
        
        # From title (if no artists field)
        if not artists:
            title_field = show.get('title', '')
            if ' w/ ' in title_field:
                parts = title_field.split(' w/ ', 1)
                headliner = parts[0].strip()
                # Remove genre prefix
                headliner = headliner.split(') ', 1)[-1] if ') ' in headliner else headliner
                artists.append(headliner)
                if len(parts) > 1:
                    artists.extend([a.strip() for a in parts[1].split(',') if a.strip()])
            elif ',' in title_field:
                # List of artists
                title_clean = title_field.split(') ', 1)[-1] if ') ' in title_field else title_field
                artists.extend([a.strip() for a in title_clean.split(',') if a.strip()])
        
        # Normalize artist names
        normalized_artists = []
        for artist in artists:
            normalized = artist.lower().strip()
            if normalized and len(normalized) > 2:
                normalized_artists.append(normalized)
        
        # Create pairs and add to mapping
        if len(normalized_artists) > 1:
            for i, artist1 in enumerate(normalized_artists):
                for artist2 in normalized_artists[i+1:]:
                    pair = tuple(sorted([artist1, artist2]))
                    pair_to_shows[pair].append({
                        'date': show.get('date', ''),
                        'title': show.get('title', ''),
                        'genre': show.get('genre', ''),
                        'description': show.get('description', '')
                    })
    
    print(f"Found {len(pair_to_shows)} artist pairs with show data")
    
    # Enhance edges with show details
    print("Enhancing edges with show details...")
    enhanced_edges = []
    
    for edge in network_data['edges']:
        source = edge['source']
        target = edge['target']
        pair = tuple(sorted([source, target]))
        
        shows = pair_to_shows.get(pair, [])
        
        enhanced_edge = edge.copy()
        enhanced_edge['shows'] = shows[:10]  # Limit to 10 shows for performance
        enhanced_edge['total_shows'] = len(shows)
        
        enhanced_edges.append(enhanced_edge)
    
    # Update network data
    network_data['edges'] = enhanced_edges
    
    # Save enhanced network
    output_file = os.path.join(
        project_root,
        'data',
        'processed',
        'artist_network_enhanced_20260102_211457.json'
    )
    
    with open(output_file, 'w') as f:
        json.dump(network_data, f, indent=2, default=str)
    
    print(f"✅ Enhanced network saved to: {output_file}")
    print(f"   Total edges: {len(enhanced_edges)}")
    print(f"   Edges with show data: {sum(1 for e in enhanced_edges if e.get('shows'))}")

if __name__ == "__main__":
    enhance_network_with_shows()

