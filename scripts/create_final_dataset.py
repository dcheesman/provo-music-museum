#!/usr/bin/env python3
"""
Create Final Velour Show Dataset
Processes the scraped data and creates a clean, analysis-ready dataset
"""

import json
import pandas as pd
from datetime import datetime
from typing import List, Dict
import os

def create_final_dataset():
    """Create the final dataset from the parsed shows"""
    print("=== Creating Final Velour Show Dataset ===\n")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load the parsed shows data
    try:
        parsed_file = os.path.join(project_root, 'data', 'processed', 'velour_parsed_shows_20251011_143618.json')
        with open(parsed_file, 'r') as f:
            shows = json.load(f)
        
        print(f"Loaded {len(shows)} shows from parsed data")
        
        # Clean and enhance the data
        cleaned_shows = clean_show_data(shows)
        
        # Create summary statistics
        summary = create_summary_statistics(cleaned_shows)
        
        # Save the final dataset
        save_final_dataset(cleaned_shows, summary, project_root)
        
        print(f"\n=== Dataset Creation Complete ===")
        print(f"Final dataset contains {len(cleaned_shows)} shows")
        print(f"Data spans from {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
        print(f"Genres represented: {len(summary['genres'])}")
        
    except FileNotFoundError:
        print("Could not find the parsed shows data. Please run the parser first.")
    except Exception as e:
        print(f"Error creating final dataset: {e}")

def clean_show_data(shows: List[Dict]) -> List[Dict]:
    """Clean and enhance the show data"""
    cleaned = []
    
    for show in shows:
        # Clean the title
        title = show.get('title') or ''
        title = str(title).strip()
        if not title or title in ['', 'None']:
            continue
        
        # Clean the genre
        genre = show.get('genre') or ''
        genre = str(genre).strip()
        if not genre or genre == 'None':
            genre = 'Unknown'
        
        # Clean the artists
        artists = show.get('artists') or ''
        artists = str(artists).strip()
        if not artists or artists == 'None':
            artists = ''
        
        # Clean the description
        description = show.get('description') or ''
        description = str(description).strip()
        
        # Create a clean show entry
        clean_show = {
            'date': show.get('date', ''),
            'day': show.get('day', ''),
            'month': show.get('month', ''),
            'year': show.get('year', ''),
            'title': title,
            'genre': genre,
            'artists': artists,
            'description': description,
            'venue': 'Velour Live Music Gallery',
            'is_open_mic': 'Open-Mic' in title,
            'is_festival': 'Festival' in title or 'FilmQuest' in title,
            'is_special_event': any(keyword in title.lower() for keyword in ['prom', 'dance', 'special', 'event']),
            'extracted_at': show.get('extracted_at', datetime.now().isoformat())
        }
        
        cleaned.append(clean_show)
    
    return cleaned

def create_summary_statistics(shows: List[Dict]) -> Dict:
    """Create summary statistics for the dataset"""
    if not shows:
        return {}
    
    # Date range
    dates = [show['date'] for show in shows if show['date']]
    dates.sort()
    
    # Genre breakdown
    genres = {}
    for show in shows:
        genre = show.get('genre', 'Unknown')
        genres[genre] = genres.get(genre, 0) + 1
    
    # Event type breakdown
    event_types = {
        'Open Mic': len([s for s in shows if s['is_open_mic']]),
        'Festivals': len([s for s in shows if s['is_festival']]),
        'Special Events': len([s for s in shows if s['is_special_event']]),
        'Regular Shows': len([s for s in shows if not any([s['is_open_mic'], s['is_festival'], s['is_special_event']])])
    }
    
    # Monthly breakdown
    monthly = {}
    for show in shows:
        month = show.get('month', 'Unknown')
        monthly[month] = monthly.get(month, 0) + 1
    
    return {
        'total_shows': len(shows),
        'date_range': {
            'earliest': dates[0] if dates else 'N/A',
            'latest': dates[-1] if dates else 'N/A'
        },
        'genres': genres,
        'event_types': event_types,
        'monthly_breakdown': monthly,
        'venue': 'Velour Live Music Gallery',
        'data_source': 'https://velourlive.com/calendar/index.php',
        'created_at': datetime.now().isoformat()
    }

def save_final_dataset(shows: List[Dict], summary: Dict, project_root: str):
    """Save the final dataset and summary"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure directories exist
    os.makedirs(os.path.join(project_root, 'data', 'exports'), exist_ok=True)
    os.makedirs(os.path.join(project_root, 'data', 'processed'), exist_ok=True)
    
    # Save main dataset as CSV
    df = pd.DataFrame(shows)
    csv_file = os.path.join(project_root, 'data', 'exports', f'velour_final_dataset_{timestamp}.csv')
    df.to_csv(csv_file, index=False)
    print(f"Final dataset saved to: {csv_file}")
    
    # Save as JSON
    json_file = os.path.join(project_root, 'data', 'exports', f'velour_final_dataset_{timestamp}.json')
    with open(json_file, 'w') as f:
        json.dump(shows, f, indent=2, default=str)
    print(f"Final dataset saved to: {json_file}")
    
    # Save summary report
    summary_file = os.path.join(project_root, 'data', 'processed', f'velour_summary_report_{timestamp}.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Summary report saved to: {summary_file}")
    
    # Create a TSV file as requested
    tsv_file = os.path.join(project_root, 'data', 'exports', f'velour_final_dataset_{timestamp}.tsv')
    df.to_csv(tsv_file, index=False, sep='\t')
    print(f"TSV file saved to: {tsv_file}")
    
    # Print summary to console
    print(f"\n=== Dataset Summary ===")
    print(f"Total shows: {summary['total_shows']}")
    print(f"Date range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
    print(f"Genres: {len(summary['genres'])}")
    print(f"Event types:")
    for event_type, count in summary['event_types'].items():
        print(f"  {event_type}: {count}")
    
    print(f"\n=== Top Genres ===")
    sorted_genres = sorted(summary['genres'].items(), key=lambda x: x[1], reverse=True)
    for genre, count in sorted_genres[:10]:
        print(f"  {genre}: {count}")

if __name__ == "__main__":
    create_final_dataset()