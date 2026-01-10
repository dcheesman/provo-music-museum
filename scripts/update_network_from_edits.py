#!/usr/bin/env python3
"""
Update Network Data from Artist Edits
Takes edited artist CSV and changes log, updates the network JSON files
"""

import json
import csv
import os
from datetime import datetime
from collections import defaultdict

def load_edited_artists(csv_file):
    """Load edited artists CSV"""
    artists = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = row['normalized_name']
            artists[normalized] = {
                'artist_name': row['artist_name'],
                'normalized_name': normalized,
                'total_shows': int(row['total_shows']),
                'connection_count': int(row['connection_count']),
                'first_year': int(row['first_year']) if row['first_year'] else None,
                'last_year': int(row['last_year']) if row['last_year'] else None,
                'years_span': int(row['years_span']) if row['years_span'] else 0
            }
    return artists

def load_changes_log(json_file):
    """Load changes log"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_network_data(network_file, artists_map, changes):
    """Update network JSON with edited artist data"""
    print(f"Loading network data from {network_file}...")
    with open(network_file, 'r', encoding='utf-8') as f:
        network_data = json.load(f)
    
    # Create mapping of old normalized names to new ones
    name_mapping = {}
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
    
    # Update nodes
    print("Updating nodes...")
    updated_nodes = []
    nodes_to_remove = set()
    
    for node in network_data['nodes']:
        node_id = node['id']
        
        # Check if this node was merged into another
        if node_id in name_mapping:
            target_id = name_mapping[node_id]
            # Skip this node, it was merged
            nodes_to_remove.add(node_id)
            continue
        
        # Check if this node's normalized name changed
        if node_id in name_mapping:
            node_id = name_mapping[node_id]
        
        # Update node data if artist exists in edited data
        if node_id in artists_map:
            artist = artists_map[node_id]
            node['label'] = artist['artist_name']
            node['id'] = node_id
            node['shows'] = artist['total_shows']
            node['size'] = artist['total_shows']
        
        updated_nodes.append(node)
    
    # Update edges
    print("Updating edges...")
    updated_edges = []
    edges_to_remove = set()
    
    for i, edge in enumerate(network_data['edges']):
        source = edge['source']
        target = edge['target']
        
        # Map old names to new names
        if source in name_mapping:
            source = name_mapping[source]
        if target in name_mapping:
            target = name_mapping[target]
        
        # Skip edges where both nodes were merged (duplicate)
        if source == target:
            continue
        
        # Skip edges where source or target was removed
        if source in nodes_to_remove or target in nodes_to_remove:
            continue
        
        edge['source'] = source
        edge['target'] = target
        updated_edges.append(edge)
    
    # Remove duplicate edges after merging
    seen_edges = set()
    final_edges = []
    for edge in updated_edges:
        edge_key = tuple(sorted([edge['source'], edge['target']]))
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            final_edges.append(edge)
        else:
            # Merge edge data (combine shows)
            existing = next(e for e in final_edges if tuple(sorted([e['source'], e['target']])) == edge_key)
            if 'shows' in edge and 'shows' in existing:
                existing['shows'].extend(edge.get('shows', []))
                existing['total_shows'] = len(existing['shows'])
                existing['weight'] = existing['total_shows']
                existing['shows_together'] = existing['total_shows']
    
    network_data['nodes'] = updated_nodes
    network_data['edges'] = final_edges
    network_data['metadata']['updated_at'] = datetime.now().isoformat()
    network_data['metadata']['updated_from'] = 'artist_editor'
    
    return network_data

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Look for edited files in webapp directory or downloads
    edited_csv = input("Enter path to edited artists CSV (or press Enter to skip): ").strip()
    if not edited_csv:
        print("No edited CSV provided. Exiting.")
        return
    
    if not os.path.exists(edited_csv):
        print(f"File not found: {edited_csv}")
        return
    
    changes_json = input("Enter path to changes log JSON (or press Enter to skip): ").strip()
    changes = []
    if changes_json and os.path.exists(changes_json):
        changes = load_changes_log(changes_json)
        print(f"Loaded {len(changes)} changes")
    
    # Load edited artists
    artists_map = load_edited_artists(edited_csv)
    print(f"Loaded {len(artists_map)} artists")
    
    # Update network file
    network_file = os.path.join(
        project_root,
        'data',
        'processed',
        'artist_network_enhanced_20260102_211457.json'
    )
    
    if not os.path.exists(network_file):
        print(f"Network file not found: {network_file}")
        return
    
    updated_network = update_network_data(network_file, artists_map, changes)
    
    # Save updated network
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(
        project_root,
        'data',
        'processed',
        f'artist_network_updated_{timestamp}.json'
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(updated_network, f, indent=2, default=str)
    
    print(f"\n✅ Updated network saved to: {output_file}")
    print(f"   Nodes: {len(updated_network['nodes'])}")
    print(f"   Edges: {len(updated_network['edges'])}")
    
    # Also update the webapp file
    webapp_file = os.path.join(project_root, 'webapp', 'network_data.json')
    if os.path.exists(webapp_file):
        with open(webapp_file, 'w', encoding='utf-8') as f:
            json.dump(updated_network, f, indent=2, default=str)
        print(f"✅ Webapp network file updated: {webapp_file}")

if __name__ == "__main__":
    main()

