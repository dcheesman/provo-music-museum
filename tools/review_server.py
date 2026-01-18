#!/usr/bin/env python3
"""
Web-based Review Tool for Velour Show Data

A simple CRUD interface for reviewing and correcting flagged shows.

Usage:
    python review_server.py

Then open http://localhost:5000 in your browser.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, jsonify, request, render_template_string
from data_model import DataStore, ShowArtist

app = Flask(__name__)
store = DataStore()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Show Review Tool</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #e5e5e5;
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #fff; margin-bottom: 10px; }
        .stats { color: #888; margin-bottom: 20px; }

        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            align-items: center;
        }
        input, select, button {
            padding: 8px 12px;
            border: 1px solid #444;
            border-radius: 4px;
            background: #2a2a2a;
            color: #e5e5e5;
            font-size: 14px;
        }
        button {
            cursor: pointer;
            background: #BF0404;
            border-color: #BF0404;
            color: white;
        }
        button:hover { background: #d40404; }
        button.secondary { background: #444; border-color: #555; }
        button.secondary:hover { background: #555; }
        button.success { background: #065f46; border-color: #065f46; }
        button.success:hover { background: #047857; }

        .show-list {
            display: grid;
            gap: 15px;
        }
        .show-card {
            background: #2a2a2a;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 15px;
        }
        .show-card.editing {
            border-color: #BF0404;
        }
        .show-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .show-date {
            color: #BF0404;
            font-weight: bold;
            font-size: 14px;
        }
        .show-title {
            font-size: 18px;
            color: #fff;
            margin: 5px 0;
        }
        .show-meta {
            color: #888;
            font-size: 13px;
        }
        .review-reason {
            background: #3d2020;
            color: #f87171;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 13px;
            margin: 10px 0;
        }

        .artists-section { margin-top: 15px; }
        .artists-section h4 {
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
            margin: 0 0 8px 0;
        }
        .artist-list { display: flex; flex-direction: column; gap: 5px; }
        .artist-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
            background: #333;
            border-radius: 4px;
        }
        .artist-item input {
            flex: 1;
            background: #222;
        }
        .artist-item .headliner {
            color: #fbbf24;
            font-size: 12px;
        }
        .artist-item button {
            padding: 4px 8px;
            font-size: 12px;
        }

        .raw-text {
            background: #222;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            color: #888;
            margin-top: 10px;
        }

        .actions {
            display: flex;
            gap: 8px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #444;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-top: 20px;
            padding: 15px;
            background: #2a2a2a;
            border-radius: 8px;
        }
        .page-info { color: #888; }

        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            background: #065f46;
            color: white;
            border-radius: 6px;
            display: none;
            z-index: 1000;
        }
        .toast.error { background: #991b1b; }
        .toast.show { display: block; }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        .empty-state h2 { color: #065f46; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Show Review Tool</h1>
        <div class="stats" id="stats">Loading...</div>

        <div class="controls">
            <input type="text" id="search" placeholder="Search shows..." style="width: 200px;">
            <select id="filter">
                <option value="review">Needs Review</option>
                <option value="all">All Shows</option>
            </select>
            <select id="year">
                <option value="">All Years</option>
            </select>
            <button onclick="loadShows()" class="secondary">Refresh</button>
        </div>

        <div class="show-list" id="showList"></div>

        <div class="pagination" id="pagination" style="display: none;">
            <button onclick="prevPage()" class="secondary">&larr; Previous</button>
            <span class="page-info" id="pageInfo"></span>
            <button onclick="nextPage()" class="secondary">Next &rarr;</button>
        </div>
    </div>

    <div class="toast" id="toast"></div>

<script>
let shows = [];
let currentPage = 0;
const pageSize = 20;
let editingShow = null;

async function loadStats() {
    const res = await fetch('/api/stats');
    const stats = await res.json();
    document.getElementById('stats').textContent =
        `${stats.needs_review} shows need review | ${stats.total_shows} total shows | ${stats.total_artists} artists`;

    // Populate year dropdown
    const yearSelect = document.getElementById('year');
    const years = Object.keys(stats.shows_by_year || {}).sort().reverse();
    years.forEach(y => {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y;
        yearSelect.appendChild(opt);
    });
}

async function loadShows() {
    const filter = document.getElementById('filter').value;
    const year = document.getElementById('year').value;
    const search = document.getElementById('search').value;

    let url = `/api/shows?filter=${filter}`;
    if (year) url += `&year=${year}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const res = await fetch(url);
    shows = await res.json();
    currentPage = 0;
    renderShows();
}

function renderShows() {
    const list = document.getElementById('showList');
    const start = currentPage * pageSize;
    const pageShows = shows.slice(start, start + pageSize);

    if (shows.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <h2>All caught up!</h2>
                <p>No shows match your current filters.</p>
            </div>
        `;
        document.getElementById('pagination').style.display = 'none';
        return;
    }

    list.innerHTML = pageShows.map(show => renderShowCard(show)).join('');

    // Pagination
    const totalPages = Math.ceil(shows.length / pageSize);
    document.getElementById('pagination').style.display = totalPages > 1 ? 'flex' : 'none';
    document.getElementById('pageInfo').textContent = `Page ${currentPage + 1} of ${totalPages} (${shows.length} shows)`;
}

function renderShowCard(show) {
    const isEditing = editingShow === show.id;
    const artistsHtml = show.artists.map((a, i) => `
        <div class="artist-item">
            ${isEditing ? `
                <input type="text" value="${escapeHtml(a.name)}" data-index="${i}" onchange="updateArtist('${show.id}', ${i}, this.value)">
                <label><input type="checkbox" ${a.is_headliner ? 'checked' : ''} onchange="toggleHeadliner('${show.id}', ${i})"> Headliner</label>
                <button onclick="removeArtist('${show.id}', ${i})" class="secondary">Remove</button>
            ` : `
                <span>${escapeHtml(a.name)}</span>
                ${a.is_headliner ? '<span class="headliner">★ Headliner</span>' : ''}
            `}
        </div>
    `).join('');

    return `
        <div class="show-card ${isEditing ? 'editing' : ''}" id="show-${show.id}">
            <div class="show-header">
                <div>
                    <div class="show-date">${show.date}</div>
                    <div class="show-title">${escapeHtml(show.title)}</div>
                    <div class="show-meta">${show.event_type} | ${show.artists.length} artists</div>
                </div>
            </div>

            ${show.review_notes ? `<div class="review-reason">⚠️ ${escapeHtml(show.review_notes)}</div>` : ''}

            <div class="artists-section">
                <h4>Artists</h4>
                <div class="artist-list" id="artists-${show.id}">
                    ${artistsHtml}
                </div>
                ${isEditing ? `
                    <button onclick="addArtist('${show.id}')" class="secondary" style="margin-top: 8px;">+ Add Artist</button>
                ` : ''}
            </div>

            ${show.raw_artists_text ? `<div class="raw-text">Raw: ${escapeHtml(show.raw_artists_text)}</div>` : ''}

            <div class="actions">
                ${isEditing ? `
                    <button onclick="saveShow('${show.id}')" class="success">Save Changes</button>
                    <button onclick="cancelEdit()" class="secondary">Cancel</button>
                ` : `
                    <button onclick="startEdit('${show.id}')">Edit</button>
                    <button onclick="approveShow('${show.id}')" class="success">Approve ✓</button>
                    <button onclick="markNotMusic('${show.id}')" class="secondary">Not Music</button>
                `}
            </div>
        </div>
    `;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function startEdit(showId) {
    editingShow = showId;
    renderShows();
}

function cancelEdit() {
    editingShow = null;
    loadShows();
}

function updateArtist(showId, index, name) {
    const show = shows.find(s => s.id === showId);
    if (show) show.artists[index].name = name;
}

function toggleHeadliner(showId, index) {
    const show = shows.find(s => s.id === showId);
    if (show) show.artists[index].is_headliner = !show.artists[index].is_headliner;
}

function removeArtist(showId, index) {
    const show = shows.find(s => s.id === showId);
    if (show) {
        show.artists.splice(index, 1);
        renderShows();
    }
}

function addArtist(showId) {
    const show = shows.find(s => s.id === showId);
    if (show) {
        show.artists.push({ name: '', is_headliner: false });
        renderShows();
        // Focus the new input
        setTimeout(() => {
            const inputs = document.querySelectorAll(`#show-${showId} .artist-item input[type="text"]`);
            if (inputs.length) inputs[inputs.length - 1].focus();
        }, 50);
    }
}

async function saveShow(showId) {
    const show = shows.find(s => s.id === showId);
    if (!show) return;

    // Filter out empty artist names
    show.artists = show.artists.filter(a => a.name && a.name.trim());

    const res = await fetch(`/api/shows/${showId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            artists: show.artists,
            needs_review: false
        })
    });

    if (res.ok) {
        showToast('Show saved successfully');
        editingShow = null;
        loadShows();
        loadStats();
    } else {
        showToast('Error saving show', true);
    }
}

async function approveShow(showId) {
    const res = await fetch(`/api/shows/${showId}/approve`, { method: 'POST' });
    if (res.ok) {
        showToast('Show approved');
        loadShows();
        loadStats();
    }
}

async function markNotMusic(showId) {
    const res = await fetch(`/api/shows/${showId}/not-music`, { method: 'POST' });
    if (res.ok) {
        showToast('Marked as non-music event');
        loadShows();
        loadStats();
    }
}

function prevPage() {
    if (currentPage > 0) {
        currentPage--;
        renderShows();
        window.scrollTo(0, 0);
    }
}

function nextPage() {
    if ((currentPage + 1) * pageSize < shows.length) {
        currentPage++;
        renderShows();
        window.scrollTo(0, 0);
    }
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show' + (isError ? ' error' : '');
    setTimeout(() => toast.className = 'toast', 3000);
}

// Event listeners
document.getElementById('filter').addEventListener('change', loadShows);
document.getElementById('year').addEventListener('change', loadShows);
document.getElementById('search').addEventListener('input', debounce(loadShows, 300));

function debounce(fn, ms) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), ms);
    };
}

// Initial load
loadStats();
loadShows();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def get_stats():
    stats = store.get_stats()
    # Get shows by year
    shows = store.all_shows()
    shows_by_year = {}
    for show in shows:
        if show.date:
            year = show.date[:4]
            shows_by_year[year] = shows_by_year.get(year, 0) + 1
    stats['shows_by_year'] = shows_by_year
    return jsonify(stats)

@app.route('/api/shows')
def get_shows():
    filter_type = request.args.get('filter', 'review')
    year = request.args.get('year', '')
    search = request.args.get('search', '').lower()

    if filter_type == 'review':
        shows = store.shows_needing_review()
    else:
        shows = store.all_shows()

    # Filter by year
    if year:
        shows = [s for s in shows if s.date and s.date.startswith(year)]

    # Filter by search
    if search:
        shows = [s for s in shows if
                 search in (s.title or '').lower() or
                 search in (s.raw_artists_text or '').lower() or
                 any(search in store.get_artist(a.artist_id).name.lower()
                     for a in s.artists if store.get_artist(a.artist_id))]

    # Sort by date
    shows = sorted(shows, key=lambda s: s.date or '', reverse=True)

    # Convert to JSON-serializable format
    result = []
    for show in shows:
        artists = []
        for sa in show.artists:
            artist = store.get_artist(sa.artist_id)
            if artist:
                artists.append({
                    'id': artist.id,
                    'name': artist.name,
                    'is_headliner': sa.is_headliner,
                    'set_notes': sa.set_notes
                })

        result.append({
            'id': show.id,
            'date': show.date,
            'title': show.title,
            'event_type': show.event_type,
            'artists': artists,
            'raw_artists_text': show.raw_artists_text,
            'review_notes': show.review_notes,
            'needs_review': show.needs_review
        })

    return jsonify(result)

@app.route('/api/shows/<show_id>', methods=['PUT'])
def update_show(show_id):
    show = store.get_show(show_id)
    if not show:
        return jsonify({'error': 'Show not found'}), 404

    data = request.json

    # Update artists
    if 'artists' in data:
        new_artists = []
        for i, artist_data in enumerate(data['artists']):
            name = artist_data.get('name', '').strip()
            if not name:
                continue
            artist = store.get_or_create_artist(name)
            new_artists.append(ShowArtist(
                artist_id=artist.id,
                billing_order=i,
                is_headliner=artist_data.get('is_headliner', False),
                set_notes=artist_data.get('set_notes')
            ))
        show.artists = new_artists

    # Update review status
    if 'needs_review' in data:
        show.needs_review = data['needs_review']
        if not data['needs_review']:
            show.review_notes = None

    store.update_show(show)
    store.save()

    return jsonify({'success': True})

@app.route('/api/shows/<show_id>/approve', methods=['POST'])
def approve_show(show_id):
    show = store.get_show(show_id)
    if not show:
        return jsonify({'error': 'Show not found'}), 404

    show.needs_review = False
    show.review_notes = None
    store.update_show(show)
    store.save()

    return jsonify({'success': True})

@app.route('/api/shows/<show_id>/not-music', methods=['POST'])
def mark_not_music(show_id):
    show = store.get_show(show_id)
    if not show:
        return jsonify({'error': 'Show not found'}), 404

    show.is_music_event = False
    show.event_type = 'other'
    show.artists = []
    show.needs_review = False
    show.review_notes = None
    store.update_show(show)
    store.save()

    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("Show Review Tool")
    print("=" * 50)
    print(f"\nOpen http://127.0.0.1:5001 in your browser")
    print("Press Ctrl+C to stop\n")
    app.run(host='127.0.0.1', port=5001, debug=False)
