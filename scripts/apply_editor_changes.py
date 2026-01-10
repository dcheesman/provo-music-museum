#!/usr/bin/env python3
"""
Apply Editor Changes to Data Files
Takes the exported CSV and changes JSON from the editor and applies them to the actual data files
"""

import json
import csv
import os
import shutil
import re
from datetime import datetime

def load_edited_csv(csv_file):
    """Load the edited artists CSV with proper handling of quoted fields"""
    artists = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Use csv.DictReader with proper quoting to handle JSON arrays and commas
        reader = csv.DictReader(f, quoting=csv.QUOTE_ALL)
        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
            try:
                # Parse years_active with error handling
                years_active = []
                years_str = row.get('years_active', '').strip()
                if years_str:
                    # Remove quotes if present
                    years_str = years_str.strip('"').strip("'")
                    try:
                        years_active = json.loads(years_str)
                        if not isinstance(years_active, list):
                            years_active = []
                    except json.JSONDecodeError:
                        # Try to extract years from malformed JSON
                        # Look for numbers in brackets like [2006, 2007] or [2006,2007]
                        years = re.findall(r'\d{4}', years_str)
                        years_active = [int(y) for y in years] if years else []
                        if years_active:
                            print(f"  Warning: Row {row_num} had malformed years_active JSON, extracted years: {years_active}")
                
                # Clean up artist name (remove quotes)
                artist_name = row.get('artist_name', '').strip().strip('"').strip("'")
                normalized_name = row.get('normalized_name', '').strip().strip('"').strip("'")
                
                # Parse numeric fields with better error handling
                def safe_int(value, default=0):
                    if not value or not str(value).strip():
                        return default
                    value_str = str(value).strip().strip('"').strip("'")
                    # Remove trailing brackets or other junk
                    value_str = re.sub(r'[\]\[]+$', '', value_str)
                    try:
                        return int(value_str)
                    except ValueError:
                        return default
                
                artists.append({
                    'artist_name': artist_name,
                    'normalized_name': normalized_name,
                    'total_shows': safe_int(row.get('total_shows'), 0),
                    'connection_count': safe_int(row.get('connection_count'), 0),
                    'first_year': safe_int(row.get('first_year'), None) if row.get('first_year') else None,
                    'last_year': safe_int(row.get('last_year'), None) if row.get('last_year') else None,
                    'years_span': safe_int(row.get('years_span'), 0),
                    'years_active': years_active
                })
            except Exception as e:
                print(f"  Error processing row {row_num}: {e}")
                print(f"  Artist name: {row.get('artist_name', 'N/A')}")
                continue
    
    print(f"Successfully loaded {len(artists)} artists from CSV")
    return artists

def load_changes_log(json_file):
    """Load the changes log"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def apply_changes_to_network(network_file, changes, artists_map):
    """Apply editor changes to network data"""
    print(f"Loading network data from {network_file}...")
    with open(network_file, 'r', encoding='utf-8') as f:
        network_data = json.load(f)
    
    # Process changes
    name_mapping = {}  # old normalized -> new normalized
    nodes_to_remove = set()
    
    for change in changes:
        if change['type'] == 'edit':
            old_normalized = change['original']['normalized_name']
            new_normalized = change['updated']['normalized_name']
            if old_normalized != new_normalized:
                name_mapping[old_normalized] = new_normalized
        
        elif change['type'] == 'merge':
            source_normalized = change['source']['normalized_name']
            target_normalized = change['target']['normalized_name']
            name_mapping[source_normalized] = target_normalized
            nodes_to_remove.add(source_normalized)
        
        elif change['type'] == 'delete':
            nodes_to_remove.add(change['artist']['normalized_name'])
    
    # Update nodes
    print("Updating nodes...")
    updated_nodes = []
    
    for node in network_data['nodes']:
        node_id = node['id']
        
        # Skip removed nodes
        if node_id in nodes_to_remove:
            continue
        
        # Update name if mapped
        if node_id in name_mapping:
            node_id = name_mapping[node_id]
            node['id'] = node_id
        
        # Update label and size from artists_map
        if node_id in artists_map:
            artist = artists_map[node_id]
            node['label'] = artist['artist_name']
            node['shows'] = artist['total_shows']
            node['size'] = artist['total_shows']
        
        updated_nodes.append(node)
    
    # Update edges
    print("Updating edges...")
    updated_edges = []
    
    for edge in network_data['edges']:
        source = edge['source']
        target = edge['target']
        
        # Skip if either node was removed
        if source in nodes_to_remove or target in nodes_to_remove:
            continue
        
        # Map names
        if source in name_mapping:
            source = name_mapping[source]
        if target in name_mapping:
            target = name_mapping[target]
        
        # Skip self-loops
        if source == target:
            continue
        
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
    network_data['metadata']['updated_from'] = 'editor_changes'
    
    return network_data

def find_latest_file(directory, pattern):
    """Find the most recent file matching a pattern in a directory"""
    if not os.path.exists(directory):
        return None
    
    matching_files = []
    for filename in os.listdir(directory):
        if pattern in filename.lower():
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                matching_files.append((filepath, os.path.getmtime(filepath)))
    
    if not matching_files:
        return None
    
    # Sort by modification time, most recent first
    matching_files.sort(key=lambda x: x[1], reverse=True)
    return matching_files[0][0]

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    downloads_dir = os.path.join(project_root, 'data', 'downloads')
    
    print("=== Apply Editor Changes to Data Files ===\n")
    
    # Try to find latest files in downloads directory
    default_csv = find_latest_file(downloads_dir, 'artists_edited')
    default_json = find_latest_file(downloads_dir, 'artist_changes')
    
    # Get file paths with defaults
    if default_csv:
        prompt = f"Enter path to edited artists CSV (or press Enter for: {os.path.basename(default_csv)}): "
        edited_csv = input(prompt).strip()
        if not edited_csv:
            edited_csv = default_csv
            print(f"Using default: {edited_csv}")
    else:
        edited_csv = input("Enter path to edited artists CSV (from editor Save): ").strip()
    
    # Handle relative paths and expand user home
    if not os.path.isabs(edited_csv):
        # Try relative to project root first
        if not os.path.exists(edited_csv):
            # Try in downloads folder
            downloads_path = os.path.join(downloads_dir, os.path.basename(edited_csv))
            if os.path.exists(downloads_path):
                edited_csv = downloads_path
            else:
                # Try as relative to project root
                edited_csv = os.path.join(project_root, edited_csv)
    
    if not os.path.exists(edited_csv):
        print(f"Error: CSV file not found: {edited_csv}")
        print(f"Current directory: {os.getcwd()}")
        return
    
    print(f"Using CSV file: {edited_csv}\n")
    
    # Get changes JSON with default
    if default_json:
        prompt = f"Enter path to changes log JSON (or press Enter for: {os.path.basename(default_json)}): "
        changes_json = input(prompt).strip()
        if not changes_json:
            changes_json = default_json
            print(f"Using default: {changes_json}")
    else:
        changes_json = input("Enter path to changes log JSON (from editor Save, or press Enter to skip): ").strip()
    
    changes = []
    if changes_json:
        # Handle relative paths
        if not os.path.isabs(changes_json):
            if not os.path.exists(changes_json):
                downloads_path = os.path.join(downloads_dir, os.path.basename(changes_json))
                if os.path.exists(downloads_path):
                    changes_json = downloads_path
                else:
                    changes_json = os.path.join(project_root, changes_json)
        
        if os.path.exists(changes_json):
            changes = load_changes_log(changes_json)
            print(f"Loaded {len(changes)} changes from log\n")
        else:
            print(f"Warning: Changes JSON not found: {changes_json}, continuing without it\n")
    
    # Load edited artists
    print(f"\nLoading edited artists from {edited_csv}...")
    artists = load_edited_csv(edited_csv)
    artists_map = {a['normalized_name']: a for a in artists}
    print(f"Loaded {len(artists)} artists")
    
    # Backup original files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(project_root, 'data', 'backups', timestamp)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Files to update
    files_to_update = [
        ('data/processed/artists_20260102_211457.csv', 'artists_20260102_211457.csv'),
        ('data/processed/artist_network_enhanced_20260102_211457.json', 'artist_network_enhanced_20260102_211457.json'),
        ('webapp/artists_data.csv', 'artists_data.csv'),
        ('webapp/network_data.json', 'network_data.json')
    ]
    
    print(f"\nBacking up original files to {backup_dir}...")
    for file_path, filename in files_to_update:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            shutil.copy(full_path, os.path.join(backup_dir, filename))
            print(f"  Backed up: {filename}")
    
    # Update artists CSV
    print("\nUpdating artists CSV files...")
    output_csv = os.path.join(project_root, 'data', 'processed', 'artists_20260102_211457.csv')
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['artist_name', 'normalized_name', 'total_shows', 
                                               'connection_count', 'years_active', 'first_year', 
                                               'last_year', 'years_span'])
        writer.writeheader()
        for artist in artists:
            row = artist.copy()
            row['years_active'] = json.dumps(artist['years_active'])
            writer.writerow(row)
    print(f"✅ Updated: {output_csv}")
    
    # Copy to webapp
    webapp_csv = os.path.join(project_root, 'webapp', 'artists_data.csv')
    shutil.copy(output_csv, webapp_csv)
    print(f"✅ Updated: {webapp_csv}")
    
    # Update network data
    network_file = os.path.join(project_root, 'data', 'processed', 'artist_network_enhanced_20260102_211457.json')
    if os.path.exists(network_file):
        print("\nUpdating network data...")
        updated_network = apply_changes_to_network(network_file, changes, artists_map)
        
        # Save updated network
        with open(network_file, 'w', encoding='utf-8') as f:
            json.dump(updated_network, f, indent=2, default=str)
        print(f"✅ Updated: {network_file}")
        
        # Copy to webapp
        webapp_network = os.path.join(project_root, 'webapp', 'network_data.json')
        with open(webapp_network, 'w', encoding='utf-8') as f:
            json.dump(updated_network, f, indent=2, default=str)
        print(f"✅ Updated: {webapp_network}")
    
    print(f"\n✅ All changes applied!")
    print(f"   Original files backed up to: {backup_dir}")
    print(f"\nYou can now refresh your browser to see the updated data.")

if __name__ == "__main__":
    main()

