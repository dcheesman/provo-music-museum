# Velour Live Artist Network Visualization

Interactive web-based network visualization of artists who have performed at Velour Live Music Gallery.

## Features

- **Interactive Network Graph**: Force-directed layout showing artist connections
- **Node Hover**: Hover over artist nodes to see name, show count, and connection count
- **Link Hover**: Hover over connections to see show dates and details
- **Interactive Controls**:
  - Adjust node size
  - Adjust link distance
  - Adjust charge (repulsion between nodes)
  - Reset view
  - Filter by minimum number of shows
- **Node Selection**: Click nodes to highlight their connections
- **Draggable Nodes**: Drag nodes to rearrange the network
- **Zoom**: Scroll to zoom in/out, drag to pan

## Setup

1. The network data file should be automatically copied to `webapp/network_data.json`.
   If it's missing, copy it:
   ```bash
   cp ../data/processed/artist_network_enhanced_20260102_211457.json network_data.json
   ```

2. If the enhanced file doesn't exist, run:
   ```bash
   python scripts/enhance_network_with_shows.py
   ```
   Then copy it to the webapp directory.

3. Start a local web server:

   **Option 1 - Using the provided script:**
   ```bash
   cd webapp
   ./start_server.sh
   ```

   **Option 2 - Using Python directly:**
   ```bash
   cd webapp
   python3 -m http.server 8000
   ```

   **Option 3 - Using any other web server:**
   - Node.js: `npx http-server`
   - PHP: `php -S localhost:8000`
   - Or any other local web server

4. Open your browser to: `http://localhost:8000`

   **Note**: Due to browser security restrictions (CORS), you cannot simply open `index.html` directly. You must use a web server.

## File Structure

```
webapp/
├── index.html          # Main HTML file (network visualization)
├── editor.html         # Artist data editor
├── style.css          # Styling for network view
├── editor.css         # Styling for editor
├── app.js             # D3.js visualization code
├── editor.js          # Editor functionality
├── network_data.json  # Network data (copied from processed/)
└── README.md          # This file
```

## Data Editor

The editor (`editor.html`) allows you to:
- View all artists in a searchable, filterable table
- Edit artist names and normalized names
- Merge duplicate artists
- Detect and fix issues (names with "w/", typos, etc.)
- Export edited data

After editing, you can update the network data by running:
```bash
python scripts/update_network_from_edits.py
```

## Data Format

The visualization expects a JSON file with this structure:

```json
{
  "nodes": [
    {
      "id": "artist_id",
      "label": "Artist Name",
      "size": 10,
      "shows": 10
    }
  ],
  "edges": [
    {
      "source": "artist1_id",
      "target": "artist2_id",
      "weight": 3,
      "shows_together": 3,
      "shows": [
        {
          "date": "2025-10-15",
          "title": "Show Title",
          "genre": "Rock",
          "description": "Show description"
        }
      ],
      "total_shows": 3
    }
  ]
}
```

## Customization

### Adjust Default Settings

Edit `app.js`:

```javascript
const config = {
    nodeSize: 3,        // Base node size multiplier
    linkDistance: 50,   // Default link distance
    charge: -100,      // Node repulsion strength
    width: window.innerWidth - 40,
    height: window.innerHeight * 0.8
};
```

### Change Color Scheme

Modify the `getNodeColor()` function in `app.js`:

```javascript
function getNodeColor(shows) {
    // Your custom color logic
}
```

### Show/Hide Labels

Modify the label filter in `createVisualization()`:

```javascript
const label = g.append("g")
    .selectAll("text")
    .data(data.nodes.filter(d => d.shows >= 10)) // Change threshold
```

## Performance Tips

- The full network has ~2,880 nodes and ~6,486 edges
- For better performance, use the "Filter Top Artists" button
- Start with filtering to artists with 5+ shows
- Adjust node size and link distance for better visibility

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires JavaScript enabled
- Uses D3.js v7 (loaded from CDN)

## Troubleshooting

**Data not loading:**
- Check that the JSON file path is correct
- Make sure you're using a local web server (not file://)
- Check browser console for errors

**Visualization is slow:**
- Use the filter button to reduce number of nodes
- Reduce node size
- Increase link distance

**Nodes overlapping:**
- Increase charge (more negative = more repulsion)
- Increase link distance
- Use collision detection (already enabled)

