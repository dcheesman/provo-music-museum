#!/usr/bin/env python3
"""
Apply Shows Editor Changes to Data Files
Takes the exported CSV from shows.html and replaces the existing show data files
"""

import os
import shutil
from datetime import datetime

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_downloads_dir = os.path.join(project_root, 'data', 'downloads')
    user_downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    
    print("=== Apply Shows Editor Changes ===\n")
    print("This script will replace the existing show data files with your edited CSV.\n")
    
    # Look for the most recent exported CSV
    exported_csv = input("Enter path to exported shows CSV (or press Enter to auto-detect): ").strip()
    
    if not exported_csv:
        # First, look in data/downloads/
        csv_files = []
        if os.path.exists(data_downloads_dir):
            csv_files = [f for f in os.listdir(data_downloads_dir) 
                        if f.startswith('velour_shows_edited_') and f.endswith('.csv')]
            csv_files = [os.path.join(data_downloads_dir, f) for f in csv_files]
        
        # Also check user Downloads folder
        if os.path.exists(user_downloads_dir):
            user_csv_files = [f for f in os.listdir(user_downloads_dir) 
                             if f.startswith('velour_shows_edited_') and f.endswith('.csv')]
            csv_files.extend([os.path.join(user_downloads_dir, f) for f in user_csv_files])
        
        if csv_files:
            # Sort by modification time, most recent first
            csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            exported_csv = csv_files[0]
            print(f"Found: {os.path.basename(exported_csv)}")
        else:
            print("No exported CSV found in data/downloads/ or Downloads folder.")
            print("Please provide the path manually.")
            return
    
    # Handle relative paths
    if not os.path.isabs(exported_csv):
        if not os.path.exists(exported_csv):
            # Try data/downloads first
            data_downloads_path = os.path.join(data_downloads_dir, os.path.basename(exported_csv))
            if os.path.exists(data_downloads_path):
                exported_csv = data_downloads_path
            else:
                # Try user Downloads
                user_downloads_path = os.path.join(user_downloads_dir, os.path.basename(exported_csv))
                if os.path.exists(user_downloads_path):
                    exported_csv = user_downloads_path
                else:
                    # Try project root
                    exported_csv = os.path.join(project_root, exported_csv)
    
    if not os.path.exists(exported_csv):
        print(f"Error: File not found: {exported_csv}")
        return
    
    print(f"\nUsing CSV file: {exported_csv}\n")
    
    # Find the latest show data file in data/exports
    exports_dir = os.path.join(project_root, 'data', 'exports')
    if not os.path.exists(exports_dir):
        print(f"Error: Exports directory not found: {exports_dir}")
        return
    
    # Find the most recent velour_complete_historical CSV
    show_files = [f for f in os.listdir(exports_dir) 
                 if f.startswith('velour_complete_historical_') and f.endswith('.csv')]
    
    if not show_files:
        print("No existing show data files found in data/exports/")
        print("Creating new file...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_file = os.path.join(exports_dir, f'velour_complete_historical_{timestamp}.csv')
    else:
        show_files.sort(reverse=True)
        latest_file = show_files[0]
        target_file = os.path.join(exports_dir, latest_file)
        print(f"Found existing show data file: {latest_file}")
    
    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(project_root, 'data', 'backups', timestamp)
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.exists(target_file):
        backup_file = os.path.join(backup_dir, os.path.basename(target_file))
        shutil.copy2(target_file, backup_file)
        print(f"\n✅ Backed up original file to: {backup_file}")
    
    # Copy the exported CSV to replace the existing file
    shutil.copy2(exported_csv, target_file)
    print(f"✅ Replaced show data file: {target_file}")
    
    # Also update the webapp shows_data.csv
    webapp_file = os.path.join(project_root, 'webapp', 'shows_data.csv')
    if os.path.exists(webapp_file):
        backup_webapp = os.path.join(backup_dir, 'shows_data.csv')
        shutil.copy2(webapp_file, backup_webapp)
        print(f"✅ Backed up webapp file to: {backup_webapp}")
    
    shutil.copy2(exported_csv, webapp_file)
    print(f"✅ Updated webapp file: {webapp_file}")
    
    print(f"\n✅ All done! Your show changes have been applied.")
    print(f"   Backup saved to: {backup_dir}")
    print(f"\n   Updated files:")
    print(f"   - {target_file}")
    print(f"   - {webapp_file}")

if __name__ == "__main__":
    main()

