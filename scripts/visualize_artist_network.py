#!/usr/bin/env python3
"""
Visualize Artist Network
Creates a network visualization showing which bands have played together.
Uses matplotlib and networkx for visualization.
"""

import json
import os
import sys
from typing import Dict, List

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
except ImportError:
    print("Error: Required packages not installed.")
    print("Please install: pip install networkx matplotlib")
    sys.exit(1)

class NetworkVisualizer:
    def __init__(self, network_file: str):
        """Load network data from JSON file"""
        with open(network_file, 'r') as f:
            self.network_data = json.load(f)
        
        self.nodes = self.network_data['nodes']
        self.edges = self.network_data['edges']
        self.metadata = self.network_data.get('metadata', {})
    
    def create_graph(self, min_shows: int = 1, min_connections: int = 1):
        """Create a NetworkX graph from the network data"""
        G = nx.Graph()
        
        # Add nodes (artists)
        for node in self.nodes:
            if node['shows'] >= min_shows:
                G.add_node(node['id'], 
                          label=node['label'],
                          size=node['size'],
                          shows=node['shows'])
        
        # Add edges (connections)
        for edge in self.edges:
            if edge['weight'] >= min_connections:
                # Check if both nodes are in the graph
                if edge['source'] in G and edge['target'] in G:
                    G.add_edge(edge['source'], 
                             edge['target'],
                             weight=edge['weight'],
                             shows_together=edge['shows_together'])
        
        return G
    
    def visualize_full_network(self, output_file: str, min_shows: int = 5, 
                               min_connections: int = 2, max_nodes: int = 500):
        """Create a full network visualization"""
        print(f"Creating full network visualization...")
        print(f"  Min shows per artist: {min_shows}")
        print(f"  Min connections: {min_connections}")
        print(f"  Max nodes: {max_nodes}")
        
        G = self.create_graph(min_shows=min_shows, min_connections=min_connections)
        
        # Limit nodes if too many
        if len(G.nodes()) > max_nodes:
            # Keep top nodes by show count
            nodes_by_shows = sorted(G.nodes(data=True), 
                                  key=lambda x: x[1].get('shows', 0), 
                                  reverse=True)
            nodes_to_keep = [n[0] for n in nodes_by_shows[:max_nodes]]
            G = G.subgraph(nodes_to_keep).copy()
        
        print(f"  Graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        # Create figure
        plt.figure(figsize=(20, 20))
        
        # Use spring layout for positioning
        pos = nx.spring_layout(G, k=1, iterations=50, seed=42)
        
        # Draw edges
        edges = G.edges()
        weights = [G[u][v].get('weight', 1) for u, v in edges]
        nx.draw_networkx_edges(G, pos, alpha=0.2, width=[w*0.5 for w in weights])
        
        # Draw nodes
        node_sizes = [G.nodes[n].get('shows', 1) * 10 for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                              node_color='lightblue', alpha=0.7)
        
        # Draw labels (only for nodes with many shows)
        labels = {n: G.nodes[n].get('label', n) 
                 for n in G.nodes() 
                 if G.nodes[n].get('shows', 0) >= min_shows * 2}
        nx.draw_networkx_labels(G, pos, labels, font_size=6, font_weight='bold')
        
        plt.title(f'Velour Live Artist Network\n'
                 f'{len(G.nodes())} artists, {len(G.edges())} connections\n'
                 f'(Min {min_shows} shows, Min {min_connections} connections)',
                 fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✅ Full network visualization saved: {output_file}")
        plt.close()
    
    def visualize_top_artists(self, output_file: str, top_n: int = 50):
        """Create a visualization of top artists and their connections"""
        print(f"Creating top {top_n} artists visualization...")
        
        # Sort nodes by show count
        sorted_nodes = sorted(self.nodes, key=lambda x: x['shows'], reverse=True)
        top_nodes = sorted_nodes[:top_n]
        top_node_ids = {node['id'] for node in top_nodes}
        
        # Create subgraph with top artists
        G = nx.Graph()
        
        for node in top_nodes:
            G.add_node(node['id'], 
                      label=node['label'],
                      size=node['size'],
                      shows=node['shows'])
        
        # Add edges between top artists
        for edge in self.edges:
            if edge['source'] in top_node_ids and edge['target'] in top_node_ids:
                G.add_edge(edge['source'], 
                         edge['target'],
                         weight=edge['weight'],
                         shows_together=edge['shows_together'])
        
        print(f"  Graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        # Create figure
        plt.figure(figsize=(16, 16))
        
        # Use spring layout
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # Draw edges
        edges = G.edges()
        weights = [G[u][v].get('weight', 1) for u, v in edges]
        nx.draw_networkx_edges(G, pos, alpha=0.3, width=[w*0.8 for w in weights])
        
        # Draw nodes
        node_sizes = [G.nodes[n].get('shows', 1) * 15 for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                              node_color='steelblue', alpha=0.8)
        
        # Draw all labels
        labels = {n: G.nodes[n].get('label', n) for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
        
        plt.title(f'Top {top_n} Velour Live Artists Network\n'
                 f'{len(G.nodes())} artists, {len(G.edges())} connections',
                 fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✅ Top artists visualization saved: {output_file}")
        plt.close()
    
    def print_statistics(self):
        """Print network statistics"""
        G = self.create_graph(min_shows=1, min_connections=1)
        
        print("\n=== Network Statistics ===")
        print(f"Total nodes (artists): {len(G.nodes())}")
        print(f"Total edges (connections): {len(G.edges())}")
        
        if len(G.nodes()) > 0:
            # Calculate network metrics
            print(f"\nNetwork Density: {nx.density(G):.4f}")
            print(f"Average Clustering: {nx.average_clustering(G):.4f}")
            
            if nx.is_connected(G):
                print(f"Average Path Length: {nx.average_shortest_path_length(G):.2f}")
            else:
                components = list(nx.connected_components(G))
                print(f"Number of Connected Components: {len(components)}")
                print(f"Largest Component Size: {len(max(components, key=len))}")
            
            # Degree statistics
            degrees = dict(G.degree())
            avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0
            print(f"Average Degree: {avg_degree:.2f}")
            print(f"Max Degree: {max(degrees.values()) if degrees else 0}")

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Find the most recent network file
    processed_dir = os.path.join(project_root, 'data', 'processed')
    network_files = [f for f in os.listdir(processed_dir) 
                    if f.startswith('artist_network_') and f.endswith('.json')]
    
    if not network_files:
        print("Error: No network data file found.")
        print("Please run parse_artists_network.py first.")
        return
    
    network_file = os.path.join(processed_dir, sorted(network_files)[-1])
    print(f"Loading network data from: {network_file}")
    
    visualizer = NetworkVisualizer(network_file)
    visualizer.print_statistics()
    
    # Create output directory
    output_dir = os.path.join(project_root, 'data', 'visualizations')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create visualizations
    print("\n=== Creating Visualizations ===")
    
    # Full network (filtered)
    full_output = os.path.join(output_dir, 'artist_network_full.png')
    visualizer.visualize_full_network(full_output, min_shows=3, min_connections=2)
    
    # Top artists
    top_output = os.path.join(output_dir, 'artist_network_top50.png')
    visualizer.visualize_top_artists(top_output, top_n=50)
    
    print(f"\n✅ Visualizations saved to: {output_dir}")

if __name__ == "__main__":
    main()

