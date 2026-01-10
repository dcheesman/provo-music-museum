#!/usr/bin/env python3
"""
Fix Artists with "w/" in Names
Splits artist entries that contain "w/" into separate artists and updates network data
"""

import json
import csv
import os
import re
from datetime import datetime
from collections import defaultdict

def load_artists(csv_file):
    """Load artists from CSV"""
    artists = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            artists.append({
                'artist_name': row['artist_name'],
                'normalized_name': row['normalized_name'],
                'total_shows': int(row['total_shows']) if row['total_shows'] else 0,
                'connection_count': int(row['connection_count']) if row['connection_count'] else 0,
                'first_year': int(row['first_year']) if row['first_year'] else None,
                'last_year': int(row['last_year']) if row['last_year'] else None,
                'years_span': int(row['years_span']) if row['years_span'] else 0,
                'years_active': json.loads(row['years_active']) if row['years_active'] else []
            })
    return artists

def load_shows_data(json_file):
    """Load original shows data to find which shows have the split artists"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def split_artist_name(name):
    """Split an artist name that contains 'w/' into separate names"""
    # Skip if name starts with "w/" (incomplete entry, no artist before it)
    if re.match(r'^\s*w/\s*', name, re.IGNORECASE):
        return None
    
    # Look for "w/" pattern (case insensitive) - with or without spaces
    # Pattern: space(s) + w/ + space(s) OR just w/ (no spaces)
    pattern = r'\s+w/\s+|\s+w/|w/\s+|w/'
    parts = re.split(pattern, name, flags=re.IGNORECASE)
    
    if len(parts) > 1:
        # Clean up each part
        cleaned_parts = []
        for part in parts:
            part = part.strip()
            # Remove leading/trailing quotes, commas, dollar signs, asterisks, parentheses, etc.
            part = re.sub(r'^["\',\s$*!()]+|["\',\s$*!()]+$', '', part)
            # Remove extra spaces
            part = re.sub(r'\s+', ' ', part).strip()
            # Remove trailing punctuation like "SOLD OUT!" but keep if it's part of the name
            # Only remove if it's clearly metadata (all caps, common phrases)
            if re.search(r'\$\d+|SOLD OUT|sold out', part, re.IGNORECASE):
                part = re.sub(r'\s*\$\d+.*$', '', part, flags=re.IGNORECASE)
                part = re.sub(r'\s*\*?\s*SOLD OUT.*$', '', part, flags=re.IGNORECASE)
                part = part.strip()
            # Remove trailing quotes that might be from parsing
            part = re.sub(r'^["\']+|["\']+$', '', part)
            # Clean up quotes in the middle (like "Ferocious Oaks"Reunion"")
            part = re.sub(r'""+', ' ', part)  # Replace multiple quotes with space
            part = re.sub(r'\s+', ' ', part).strip()  # Clean up extra spaces
            # Skip if too short or just punctuation
            if part and len(part) > 1 and not re.match(r'^[^a-zA-Z0-9]+$', part):
                cleaned_parts.append(part)
        
        # Only return if we have at least 2 valid parts
        return cleaned_parts if len(cleaned_parts) > 1 else None
    
    return None

def normalize_name(name):
    """Normalize artist name for matching"""
    return name.lower().strip()

def find_shows_with_artist(shows_data, artist_name, normalized_name):
    """Find all shows that mention this artist"""
    matching_shows = []
    
    for show in shows_data:
        if not show.get('date') or not show.get('title'):
            continue
        
        # Skip open mic and other non-band events
        title = show.get('title', '').lower()
        if any(skip in title for skip in ['open-mic', 'open mic', 'prom', 'dance', 'festival']):
            continue
        
        # Check if artist appears in title, description, or artists field
        title_field = show.get('title', '')
        desc_field = show.get('description', '')
        artists_field = show.get('artists', '')
        
        # Check various fields
        search_text = f"{title_field} {desc_field} {artists_field}".lower()
        
        if normalized_name in search_text or artist_name.lower() in search_text:
            matching_shows.append(show)
    
    return matching_shows

def create_new_artist(name, base_artist, shows_count=0):
    """Create a new artist entry"""
    normalized = normalize_name(name)
    
    return {
        'artist_name': name,
        'normalized_name': normalized,
        'total_shows': shows_count,
        'connection_count': 0,  # Will be recalculated
        'first_year': base_artist.get('first_year'),
        'last_year': base_artist.get('last_year'),
        'years_span': base_artist.get('years_span', 0),
        'years_active': base_artist.get('years_active', [])
    }

def extract_artists_from_show(show):
    """Extract normalized artist names from a show"""
    artists = []
    
    # From artists field
    if show.get('artists'):
        artist_str = str(show['artists']).strip()
        if artist_str and artist_str.lower() not in ['none', 'null']:
            # Split by comma
            for a in artist_str.split(','):
                a = a.strip()
                if a:
                    artists.append(normalize_name(a))
    
    # From title
    title = show.get('title', '')
    if ' w/ ' in title.lower() or 'w/' in title.lower():
        # Split by w/
        pattern = r'\s+w/\s+|\s+w/|w/\s+|w/'
        parts = re.split(pattern, title, flags=re.IGNORECASE)
        
        # Clean first part (headliner)
        if parts:
            headliner = parts[0].strip()
            # Remove genre prefix
            headliner = re.sub(r'^\([^)]+\)\s*', '', headliner)
            headliner = re.sub(r'^\d+pm[»\s]*', '', headliner)
            headliner = headliner.strip('"').strip()
            if headliner:
                artists.append(normalize_name(headliner))
        
        # Clean remaining parts (openers)
        for part in parts[1:]:
            # Split by comma if multiple openers
            for opener in part.split(','):
                opener = opener.strip()
                # Clean up
                opener = re.sub(r'\s*\$\d+.*$', '', opener, flags=re.IGNORECASE)
                opener = re.sub(r'\s*\*?\s*SOLD OUT.*$', '', opener, flags=re.IGNORECASE)
                opener = opener.strip('"').strip()
                if opener:
                    artists.append(normalize_name(opener))
    elif ',' in title:
        # List of artists
        title_clean = title.split(') ', 1)[-1] if ') ' in title else title
        for a in title_clean.split(','):
            a = a.strip()
            if a:
                artists.append(normalize_name(a))
    
    return list(set(artists))  # Remove duplicates

def fix_artists_with_w():
    """Main function to fix artists with 'w/' in names"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load data
    artists_file = os.path.join(project_root, 'data', 'processed', 'artists_20260102_211457.csv')
    shows_file = os.path.join(project_root, 'data', 'exports', 'velour_complete_historical_20260102_205023.json')
    network_file = os.path.join(project_root, 'data', 'processed', 'artist_network_enhanced_20260102_211457.json')
    
    print("Loading data...")
    artists = load_artists(artists_file)
    shows_data = load_shows_data(shows_file)
    
    print(f"Loaded {len(artists)} artists")
    print(f"Loaded {len(shows_data)} shows")
    
    # Find artists with "w/" in name
    artists_to_split = []
    for artist in artists:
        if 'w/' in artist['artist_name'].lower() or ' w/ ' in artist['artist_name'].lower():
            split_names = split_artist_name(artist['artist_name'])
            if split_names:
                artists_to_split.append({
                    'original': artist,
                    'split_names': split_names
                })
    
    print(f"\nFound {len(artists_to_split)} artists with 'w/' that need splitting:")
    for item in artists_to_split[:10]:  # Show first 10
        print(f"  - '{item['original']['artist_name']}' -> {item['split_names']}")
    if len(artists_to_split) > 10:
        print(f"  ... and {len(artists_to_split) - 10} more")
    
    if not artists_to_split:
        print("No artists with 'w/' found. Nothing to fix!")
        return
    
    # Create new artist entries
    new_artists = []
    artists_to_remove = set()
    artist_name_mapping = {}  # Maps old normalized names to new ones
    
    for item in artists_to_split:
        original = item['original']
        split_names = item['split_names']
        original_normalized = original['normalized_name']
        
        # Mark original for removal
        artists_to_remove.add(original_normalized)
        
        # Create new artists for each split name
        for name in split_names:
            normalized = normalize_name(name)
            
            # Check if this artist already exists
            existing = next((a for a in artists if a['normalized_name'] == normalized), None)
            
            if existing:
                # Artist already exists, we'll merge the shows
                print(f"  Note: '{name}' already exists, will merge shows")
                # Don't create duplicate, but track the mapping
                artist_name_mapping[original_normalized] = normalized
            else:
                # Create new artist
                new_artist = create_new_artist(name, original)
                new_artists.append(new_artist)
                artist_name_mapping[original_normalized] = normalized
                print(f"  Created new artist: '{name}'")
    
    # Remove original artists and add new ones
    fixed_artists = [a for a in artists if a['normalized_name'] not in artists_to_remove]
    fixed_artists.extend(new_artists)
    
    # Count shows for each artist by checking the shows data
    print("\nCounting shows for split artists...")
    artist_show_counts = defaultdict(int)
    
    for show in shows_data:
        if not show.get('date') or not show.get('title'):
            continue
        
        # Extract artists from show
        show_artists = extract_artists_from_show(show)
        
        for artist_norm in show_artists:
            artist_show_counts[artist_norm] += 1
    
    # Update show counts
    for artist in fixed_artists:
        if artist['normalized_name'] in artist_show_counts:
            artist['total_shows'] = artist_show_counts[artist['normalized_name']]
    
    print(f"\nFixed artists: {len(fixed_artists)} (removed {len(artists_to_remove)}, added {len(new_artists)})")
    
    # Save fixed artists CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_csv = os.path.join(project_root, 'data', 'processed', f'artists_fixed_{timestamp}.csv')
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['artist_name', 'normalized_name', 'total_shows', 
                                               'connection_count', 'years_active', 'first_year', 
                                               'last_year', 'years_span'])
        writer.writeheader()
        for artist in fixed_artists:
            row = artist.copy()
            row['years_active'] = json.dumps(artist['years_active'])
            writer.writerow(row)
    
    print(f"✅ Fixed artists saved to: {output_csv}")
    
    # Update network data
    if os.path.exists(network_file):
        print("\nUpdating network data...")
        update_network_file(network_file, artist_name_mapping, fixed_artists, timestamp)
    
    # Also update webapp files
    webapp_artists = os.path.join(project_root, 'webapp', 'artists_data.csv')
    webapp_network = os.path.join(project_root, 'webapp', 'network_data.json')
    
    if os.path.exists(webapp_artists):
        import shutil
        shutil.copy(output_csv, webapp_artists)
        print(f"✅ Updated webapp artists file: {webapp_artists}")
    
    print("\n✅ All done! Artists with 'w/' have been split.")

def update_network_file(network_file, name_mapping, fixed_artists, timestamp):
    """Update network JSON file with split artists"""
    with open(network_file, 'r', encoding='utf-8') as f:
        network_data = json.load(f)
    
    # Create lookup for fixed artists
    fixed_artists_lookup = {a['normalized_name']: a for a in fixed_artists}
    
    # Update nodes
    updated_nodes = []
    nodes_to_remove = set()
    
    for node in network_data['nodes']:
        node_id = node['id']
        
        # Check if this node needs to be split/removed
        if node_id in name_mapping:
            # This artist was split, remove the old node
            nodes_to_remove.add(node_id)
            continue
        
        # Update node if artist data exists
        if node_id in fixed_artists_lookup:
            artist = fixed_artists_lookup[node_id]
            node['label'] = artist['artist_name']
            node['shows'] = artist['total_shows']
            node['size'] = artist['total_shows']
        
        updated_nodes.append(node)
    
    # Add new nodes for split artists
    for artist in fixed_artists:
        # Check if node already exists
        existing_node = next((n for n in updated_nodes if n['id'] == artist['normalized_name']), None)
        if not existing_node:
            updated_nodes.append({
                'id': artist['normalized_name'],
                'label': artist['artist_name'],
                'size': artist['total_shows'],
                'shows': artist['total_shows']
            })
    
    # Update edges - remove edges with removed nodes, update source/target names
    updated_edges = []
    for edge in network_data['edges']:
        source = edge['source']
        target = edge['target']
        
        # Skip if either node was removed
        if source in nodes_to_remove or target in nodes_to_remove:
            continue
        
        # Update edge if names changed
        if source in name_mapping:
            source = name_mapping[source]
        if target in name_mapping:
            target = name_mapping[target]
        
        edge['source'] = source
        edge['target'] = target
        updated_edges.append(edge)
    
    # Remove duplicate edges
    seen_edges = set()
    final_edges = []
    for edge in updated_edges:
        edge_key = tuple(sorted([edge['source'], edge['target']]))
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            final_edges.append(edge)
    
    network_data['nodes'] = updated_nodes
    network_data['edges'] = final_edges
    network_data['metadata']['updated_at'] = datetime.now().isoformat()
    network_data['metadata']['updated_from'] = 'fix_w_artists'
    
    # Save updated network
    output_network = os.path.join(
        os.path.dirname(network_file),
        f'artist_network_fixed_{timestamp}.json'
    )
    
    with open(output_network, 'w', encoding='utf-8') as f:
        json.dump(network_data, f, indent=2, default=str)
    
    print(f"✅ Updated network saved to: {output_network}")
    print(f"   Nodes: {len(updated_nodes)}")
    print(f"   Edges: {len(final_edges)}")
    
    # Also update webapp file
    webapp_network = os.path.join(os.path.dirname(os.path.dirname(network_file)), 'webapp', 'network_data.json')
    if os.path.exists(os.path.dirname(webapp_network)):
        with open(webapp_network, 'w', encoding='utf-8') as f:
            json.dump(network_data, f, indent=2, default=str)
        print(f"✅ Updated webapp network file: {webapp_network}")

if __name__ == "__main__":
    fix_artists_with_w()
