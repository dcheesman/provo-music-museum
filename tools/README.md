# Provo Music Museum - Admin Tools

Backend tools for managing the Velour show archive data.

## Tools Available

### 1. Admin Server (`admin_server.py`)
**Port:** 5002

The main admin interface for data management.

**Features:**
- **Artist Management**: View, search, and manage all artists
- **Merge Artists**: Combine duplicate artists into one
  - Preserves show history from all merged artists
  - Adds old names as aliases
  - Updates all show references automatically
- **Show Management**: Add/remove artists from shows
- **Smart Autocomplete**: Type-ahead search when adding artists to shows

**Usage:**
```bash
cd tools
python admin_server.py
```

Then open: http://127.0.0.1:5002

#### Artist Merging Workflow:
1. Go to the Artists tab
2. Search for duplicate artists (e.g., "neon trees" vs "Neon Trees")
3. Click on multiple artists to select them
4. Click "Merge Selected"
5. Choose which artist name to keep as primary
6. Review the preview showing:
   - Combined show count
   - Aliases that will be created
   - Artists that will be deleted
7. Click "Confirm Merge"

All shows will be updated to reference the primary artist, and the other artists will be deleted.

#### Adding Artists to Shows:
1. Go to the Shows tab
2. Find the show you want to edit
3. Click "Edit Artists"
4. Click "+ Add Artist"
5. Start typing the artist name - autocomplete will show matches
6. Select from dropdown or type new name
7. Check "Headliner" if applicable
8. Click "Save Changes"

### 2. Export Script (`export_website_data.py`)

Exports clean data to JSON files for the website.

**Usage:**
```bash
cd tools
python export_website_data.py
```

Generates:
- `website/public/data/artists.json`
- `website/public/data/shows.json`
- `website/public/data/network.json`
- `website/public/data/stats.json`

Run this after making changes in the admin server to update the website data.

## Common Tasks

### Merge Duplicate Artists
1. Open admin server (port 5002)
2. Search for duplicates
3. Select multiple artists
4. Use "Merge Selected" feature

### Add Missing Artists to Christmas Show
1. Open admin server → Shows tab
2. Search for "Christmas"
3. Click "Edit Artists" on the show
4. Use "+ Add Artist" button repeatedly
5. Use autocomplete to find existing artists or create new ones

### After Data Changes
```bash
# 1. Export updated data to website
cd tools
python export_website_data.py

# 2. Commit changes
cd ..
git add data/clean/*.json website/public/data/*.json
git commit -m "Update show/artist data"

# 3. Push to deploy
git push
```

## Notes

- All changes auto-save to `data/clean/*.json`
- The admin server rebuilds the artist index after merges
- Always export data to website after making changes
- The website uses static JSON files (no database)
