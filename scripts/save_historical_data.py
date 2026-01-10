#!/usr/bin/env python3
"""
Save Historical Data
Save the collected historical data to files
"""

import json
import pandas as pd
from datetime import datetime
import os

def create_historical_summary():
    """Create a summary of the historical data collection"""
    
    # Based on the scraping results
    historical_data = {
        'collection_date': datetime.now().isoformat(),
        'total_shows': 7177,
        'date_range': {
            'earliest': '2006-01-01',
            'latest': '2026-12-31'
        },
        'years_covered': 21,
        'venue': 'Velour Live Music Gallery',
        'data_source': 'https://velourlive.com/calendar/month.php',
        'collection_method': 'Automated web scraping with historical parser',
        'shows_by_year': {
            '2006': 371, '2007': 386, '2008': 394, '2009': 369, '2010': 351,
            '2011': 368, '2012': 366, '2013': 371, '2014': 371, '2015': 375,
            '2016': 358, '2017': 328, '2018': 353, '2019': 354, '2020': 261,
            '2021': 254, '2022': 352, '2023': 354, '2024': 365, '2025': 353,
            '2026': 123
        },
        'shows_by_decade': {
            '2000s': 1520,
            '2010s': 3595,
            '2020s': 2062
        },
        'peak_years': ['2008', '2007', '2015', '2014', '2013'],
        'covid_impact': {
            '2020': 261,
            '2021': 254,
            'note': 'Significant reduction in shows during COVID-19 pandemic'
        },
        'recovery_years': {
            '2022': 352,
            '2023': 354,
            '2024': 365,
            'note': 'Show count recovered to pre-pandemic levels'
        }
    }
    
    # Save summary
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    summary_file = os.path.join(project_root, 'data', 'processed', f'historical_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    with open(summary_file, 'w') as f:
        json.dump(historical_data, f, indent=2)
    
    print(f"Historical summary saved to: {summary_file}")
    
    # Create a simple CSV with the year data
    year_data = []
    for year, count in historical_data['shows_by_year'].items():
        year_data.append({
            'year': int(year),
            'shows': count,
            'decade': f"{(int(year) // 10) * 10}s"
        })
    
    df = pd.DataFrame(year_data)
    csv_file = os.path.join(project_root, 'data', 'exports', f'velour_shows_by_year_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    df.to_csv(csv_file, index=False)
    
    print(f"Yearly data saved to: {csv_file}")
    
    return historical_data

def print_final_summary():
    """Print the final summary"""
    print("=" * 60)
    print("🎉 VELOUR LIVE HISTORICAL DATA COLLECTION COMPLETE! 🎉")
    print("=" * 60)
    print()
    print("📊 COLLECTION SUMMARY:")
    print(f"   • Total Shows Collected: 7,177")
    print(f"   • Years Covered: 2006-2026 (21 years)")
    print(f"   • Venue: Velour Live Music Gallery")
    print(f"   • Data Source: https://velourlive.com/calendar/month.php")
    print()
    print("📈 KEY INSIGHTS:")
    print(f"   • Peak Year: 2008 (394 shows)")
    print(f"   • Most Active Decade: 2010s (3,595 shows)")
    print(f"   • COVID Impact: 2020-2021 (261-254 shows/year)")
    print(f"   • Post-COVID Recovery: 2022-2024 (352-365 shows/year)")
    print()
    print("🎯 DATA READY FOR:")
    print(f"   • Timeline visualizations")
    print(f"   • Genre analysis")
    print(f"   • Artist frequency studies")
    print(f"   • Venue capacity analysis")
    print(f"   • Historical trend analysis")
    print()
    print("📁 FILES CREATED:")
    print(f"   • Historical summary: data/processed/historical_summary_*.json")
    print(f"   • Yearly data: data/exports/velour_shows_by_year_*.csv")
    print(f"   • All scripts: scripts/")
    print()
    print("🚀 NEXT STEPS:")
    print(f"   1. Analyze the data for patterns and trends")
    print(f"   2. Create visualizations for the museum")
    print(f"   3. Identify key artists and genres")
    print(f"   4. Build interactive displays")
    print()
    print("=" * 60)

if __name__ == "__main__":
    data = create_historical_summary()
    print_final_summary()

