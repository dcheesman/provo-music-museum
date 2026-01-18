#!/usr/bin/env python3
"""
Admin Tool for Provo Music Museum

Provides tools for:
- Merging duplicate artists
- Managing artist data
- Adding artists to shows (integrated from review_server.py)

Usage:
    python admin_server.py

Then open http://localhost:5002 in your browser.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, jsonify, request, render_template_string
from data_model import DataStore, ShowArtist, Artist
from typing import Optional

app = Flask(__name__)
store = DataStore()

# Navigation HTML component
NAV_HTML = """
<nav class="nav">
    <a href="/" class="nav-link">Artists</a>
    <a href="/shows" class="nav-link">Shows</a>
</nav>
"""

# Shared CSS
SHARED_CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a1a;
    color: #e5e5e5;
    margin: 0;
    padding: 0;
    line-height: 1.5;
}
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
h1 { color: #fff; margin-bottom: 10px; }
h2 { color: #fff; margin: 20px 0 10px; }
.stats { color: #888; margin-bottom: 20px; }

.nav {
    background: #2a2a2a;
    padding: 15px 20px;
    border-bottom: 2px solid #BF0404;
    margin-bottom: 20px;
    display: flex;
    gap: 20px;
}
.nav-link {
    color: #e5e5e5;
    text-decoration: none;
    font-weight: 500;
    padding: 5px 10px;
    border-radius: 4px;
}
.nav-link:hover {
    background: #333;
    color: #fff;
}

.controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    align-items: center;
}
input, select, button, textarea {
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
button:disabled {
    background: #666;
    cursor: not-allowed;
    opacity: 0.5;
}
button.secondary { background: #444; border-color: #555; }
button.secondary:hover { background: #555; }
button.success { background: #065f46; border-color: #065f46; }
button.success:hover { background: #047857; }
button.danger { background: #991b1b; border-color: #991b1b; }
button.danger:hover { background: #b91c1c; }

.card {
    background: #2a2a2a;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
}
.card.selected {
    border-color: #BF0404;
    background: #331a1a;
}

.artist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}
.artist-card {
    background: #2a2a2a;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 15px;
    cursor: pointer;
    transition: all 0.2s;
}
.artist-card:hover {
    border-color: #666;
}
.artist-card.selected {
    border-color: #BF0404;
    background: #331a1a;
}
.artist-name {
    font-size: 18px;
    font-weight: bold;
    color: #fff;
    margin-bottom: 8px;
}
.artist-stats {
    color: #888;
    font-size: 13px;
    display: flex;
    gap: 15px;
}
.artist-aliases {
    color: #666;
    font-size: 12px;
    margin-top: 5px;
    font-style: italic;
}

.merge-panel {
    position: fixed;
    right: 0;
    top: 0;
    height: 100vh;
    width: 400px;
    background: #2a2a2a;
    border-left: 2px solid #BF0404;
    padding: 20px;
    transform: translateX(100%);
    transition: transform 0.3s;
    overflow-y: auto;
    z-index: 100;
}
.merge-panel.open {
    transform: translateX(0);
}
.merge-panel h2 {
    margin-top: 0;
}
.merge-list {
    list-style: none;
    padding: 0;
}
.merge-list li {
    background: #333;
    padding: 10px;
    margin: 5px 0;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.merge-preview {
    background: #222;
    padding: 15px;
    border-radius: 4px;
    margin: 15px 0;
}
.merge-preview h3 {
    color: #BF0404;
    margin: 0 0 10px;
    font-size: 16px;
}

.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    z-index: 200;
    align-items: center;
    justify-content: center;
}
.modal.show {
    display: flex;
}
.modal-content {
    background: #2a2a2a;
    border: 2px solid #BF0404;
    border-radius: 8px;
    padding: 30px;
    max-width: 600px;
    width: 90%;
}
.modal-content h2 {
    margin-top: 0;
}
.form-group {
    margin: 15px 0;
}
.form-group label {
    display: block;
    margin-bottom: 5px;
    color: #888;
}
.form-group input,
.form-group textarea {
    width: 100%;
}
textarea {
    min-height: 100px;
    resize: vertical;
}

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

table {
    width: 100%;
    border-collapse: collapse;
    background: #2a2a2a;
}
th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #444;
}
th {
    background: #333;
    color: #888;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 12px;
}
tr:hover {
    background: #333;
}
"""

ARTISTS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Artist Management - Provo Music Museum</title>
    <style>
    """ + SHARED_CSS + """
    </style>
</head>
<body>
    """ + NAV_HTML + """
    <div class="container">
        <h1>Artist Management</h1>
        <div class="stats" id="stats">Loading...</div>

        <div class="controls">
            <input type="text" id="search" placeholder="Search artists..." style="width: 300px;">
            <button onclick="loadArtists()" class="secondary">Refresh</button>
            <button onclick="showAddArtistModal()" class="secondary">+ Add New Artist</button>
            <div style="flex: 1"></div>
            <button id="mergeBtn" onclick="openMergePanel()" disabled>Merge Selected (<span id="selectedCount">0</span>)</button>
        </div>

        <div class="artist-grid" id="artistGrid"></div>
    </div>

    <!-- Merge Panel -->
    <div class="merge-panel" id="mergePanel">
        <h2>Merge Artists</h2>
        <p style="color: #888; font-size: 14px;">Select the primary artist to keep. All shows from other artists will be merged into this one.</p>

        <div id="mergeArtistsList"></div>

        <div class="merge-preview" id="mergePreview" style="display: none;">
            <h3>Merged Artist Preview</h3>
            <div id="previewContent"></div>
        </div>

        <div style="margin-top: 20px; display: flex; gap: 10px;">
            <button onclick="performMerge()" class="danger" id="confirmMergeBtn" disabled>Confirm Merge</button>
            <button onclick="closeMergePanel()" class="secondary">Cancel</button>
        </div>
    </div>

    <!-- Add Artist Modal -->
    <div class="modal" id="addArtistModal">
        <div class="modal-content">
            <h2>Add New Artist</h2>
            <div class="form-group">
                <label>Artist Name *</label>
                <input type="text" id="newArtistName" placeholder="Enter artist name">
            </div>
            <div class="form-group">
                <label>Aliases (comma-separated)</label>
                <input type="text" id="newArtistAliases" placeholder="Alt spellings, former names...">
            </div>
            <div class="form-group">
                <label>Spotify URL</label>
                <input type="text" id="newArtistSpotify" placeholder="https://open.spotify.com/artist/...">
            </div>
            <div class="form-group">
                <label>Website</label>
                <input type="text" id="newArtistWebsite" placeholder="https://...">
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button onclick="createArtist()" class="success">Create Artist</button>
                <button onclick="closeAddArtistModal()" class="secondary">Cancel</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

<script>
let artists = [];
let selectedArtists = new Set();
let primaryArtistId = null;

async function loadStats() {
    const res = await fetch('/api/stats');
    const stats = await res.json();
    document.getElementById('stats').textContent =
        `${stats.total_artists.toLocaleString()} artists | ${stats.total_shows.toLocaleString()} shows`;
}

async function loadArtists() {
    const search = document.getElementById('search').value;
    let url = '/api/artists';
    if (search) url += `?search=${encodeURIComponent(search)}`;

    const res = await fetch(url);
    artists = await res.json();
    renderArtists();
}

function renderArtists() {
    const grid = document.getElementById('artistGrid');

    if (artists.length === 0) {
        grid.innerHTML = '<div class="empty-state"><h2>No artists found</h2><p>Try a different search.</p></div>';
        return;
    }

    grid.innerHTML = artists.map(artist => `
        <div class="artist-card ${selectedArtists.has(artist.id) ? 'selected' : ''}"
             onclick="toggleSelectArtist('${artist.id}')">
            <div class="artist-name">${escapeHtml(artist.name)}</div>
            <div class="artist-stats">
                <span>${artist.show_count} shows</span>
                ${artist.aliases && artist.aliases.length > 0 ? `<span>${artist.aliases.length} aliases</span>` : ''}
            </div>
            ${artist.aliases && artist.aliases.length > 0 ?
                `<div class="artist-aliases">aka: ${artist.aliases.map(escapeHtml).join(', ')}</div>` : ''}
        </div>
    `).join('');
}

function toggleSelectArtist(artistId) {
    if (selectedArtists.has(artistId)) {
        selectedArtists.delete(artistId);
    } else {
        selectedArtists.add(artistId);
    }

    document.getElementById('selectedCount').textContent = selectedArtists.size;
    document.getElementById('mergeBtn').disabled = selectedArtists.size < 2;
    renderArtists();
}

function openMergePanel() {
    if (selectedArtists.size < 2) return;

    const selectedList = Array.from(selectedArtists).map(id =>
        artists.find(a => a.id === id)
    ).filter(Boolean);

    // Default to artist with most shows as primary
    primaryArtistId = selectedList.sort((a, b) => b.show_count - a.show_count)[0].id;

    const listHtml = selectedList.map(artist => `
        <div class="card ${artist.id === primaryArtistId ? 'selected' : ''}"
             onclick="selectPrimaryArtist('${artist.id}')"
             style="cursor: pointer; margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: bold; color: ${artist.id === primaryArtistId ? '#BF0404' : '#fff'};">
                        ${escapeHtml(artist.name)}
                        ${artist.id === primaryArtistId ? ' ★' : ''}
                    </div>
                    <div style="color: #888; font-size: 13px;">${artist.show_count} shows</div>
                </div>
            </div>
        </div>
    `).join('');

    document.getElementById('mergeArtistsList').innerHTML = listHtml;
    updateMergePreview();
    document.getElementById('mergePanel').classList.add('open');
}

function closeMergePanel() {
    document.getElementById('mergePanel').classList.remove('open');
    primaryArtistId = null;
}

function selectPrimaryArtist(artistId) {
    primaryArtistId = artistId;
    openMergePanel(); // Re-render
}

function updateMergePreview() {
    if (!primaryArtistId) return;

    const primary = artists.find(a => a.id === primaryArtistId);
    const others = Array.from(selectedArtists)
        .filter(id => id !== primaryArtistId)
        .map(id => artists.find(a => a.id === id))
        .filter(Boolean);

    const totalShows = others.reduce((sum, a) => sum + a.show_count, primary.show_count);
    const allAliases = new Set([
        ...(primary.aliases || []),
        ...others.map(a => a.name),
        ...others.flatMap(a => a.aliases || [])
    ]);

    const preview = document.getElementById('mergePreview');
    preview.style.display = 'block';
    document.getElementById('previewContent').innerHTML = `
        <div style="margin: 10px 0;">
            <strong>Name:</strong> ${escapeHtml(primary.name)}
        </div>
        <div style="margin: 10px 0;">
            <strong>Total Shows:</strong> ${totalShows}
        </div>
        <div style="margin: 10px 0;">
            <strong>Aliases:</strong><br>
            ${Array.from(allAliases).map(escapeHtml).join(', ') || 'None'}
        </div>
        <div style="margin: 10px 0; color: #f87171;">
            <strong>Artists to Delete:</strong><br>
            ${others.map(a => escapeHtml(a.name)).join(', ')}
        </div>
    `;

    document.getElementById('confirmMergeBtn').disabled = false;
}

async function performMerge() {
    if (!primaryArtistId || selectedArtists.size < 2) return;

    if (!confirm(`This will merge ${selectedArtists.size} artists into one. This action cannot be undone. Continue?`)) {
        return;
    }

    const res = await fetch('/api/artists/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            primary_id: primaryArtistId,
            merge_ids: Array.from(selectedArtists).filter(id => id !== primaryArtistId)
        })
    });

    if (res.ok) {
        showToast('Artists merged successfully');
        closeMergePanel();
        selectedArtists.clear();
        loadArtists();
        loadStats();
    } else {
        const error = await res.json();
        showToast(error.error || 'Error merging artists', true);
    }
}

function showAddArtistModal() {
    document.getElementById('addArtistModal').classList.add('show');
    document.getElementById('newArtistName').focus();
}

function closeAddArtistModal() {
    document.getElementById('addArtistModal').classList.remove('show');
    document.getElementById('newArtistName').value = '';
    document.getElementById('newArtistAliases').value = '';
    document.getElementById('newArtistSpotify').value = '';
    document.getElementById('newArtistWebsite').value = '';
}

async function createArtist() {
    const name = document.getElementById('newArtistName').value.trim();
    if (!name) {
        alert('Artist name is required');
        return;
    }

    const aliases = document.getElementById('newArtistAliases').value
        .split(',')
        .map(a => a.trim())
        .filter(Boolean);

    const res = await fetch('/api/artists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name,
            aliases,
            spotify_url: document.getElementById('newArtistSpotify').value.trim() || null,
            website: document.getElementById('newArtistWebsite').value.trim() || null
        })
    });

    if (res.ok) {
        showToast('Artist created successfully');
        closeAddArtistModal();
        loadArtists();
        loadStats();
    } else {
        const error = await res.json();
        showToast(error.error || 'Error creating artist', true);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show' + (isError ? ' error' : '');
    setTimeout(() => toast.className = 'toast', 3000);
}

// Event listeners
document.getElementById('search').addEventListener('input', debounce(loadArtists, 300));

function debounce(fn, ms) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), ms);
    };
}

// Initial load
loadStats();
loadArtists();
</script>
</body>
</html>
"""

SHOWS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Show Management - Provo Music Museum</title>
    <style>
    """ + SHARED_CSS + """
    .show-list { display: grid; gap: 15px; }
    .show-card { background: #2a2a2a; border: 1px solid #444; border-radius: 8px; padding: 15px; }
    .show-card.editing { border-color: #BF0404; }
    .show-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .show-date { color: #BF0404; font-weight: bold; font-size: 14px; }
    .show-title { font-size: 18px; color: #fff; margin: 5px 0; }
    .show-meta { color: #888; font-size: 13px; }
    .artists-section { margin-top: 15px; }
    .artists-section h4 { color: #888; font-size: 12px; text-transform: uppercase; margin: 0 0 8px 0; }
    .artist-list { display: flex; flex-direction: column; gap: 5px; }
    .artist-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px;
        background: #333;
        border-radius: 4px;
        position: relative;
    }
    .artist-autocomplete {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: #222;
        border: 1px solid #BF0404;
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
        z-index: 100;
        display: none;
    }
    .artist-autocomplete.show { display: block; }
    .artist-autocomplete-item {
        padding: 8px 12px;
        cursor: pointer;
        border-bottom: 1px solid #333;
    }
    .artist-autocomplete-item:hover { background: #333; }
    .artist-autocomplete-item .name { color: #fff; font-weight: bold; }
    .artist-autocomplete-item .stats { color: #888; font-size: 12px; }
    .artist-item input { flex: 1; background: #222; }
    .artist-item .headliner { color: #fbbf24; font-size: 12px; }
    .artist-item button { padding: 4px 8px; font-size: 12px; }
    .actions { display: flex; gap: 8px; margin-top: 15px; padding-top: 15px; border-top: 1px solid #444; }
    .pagination { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 20px; padding: 15px; background: #2a2a2a; border-radius: 8px; }
    .page-info { color: #888; }
    </style>
</head>
<body>
    """ + NAV_HTML + """
    <div class="container">
        <h1>Show Management</h1>
        <div class="stats" id="stats">Loading...</div>

        <div class="controls">
            <input type="text" id="search" placeholder="Search shows..." style="width: 200px;">
            <select id="filter">
                <option value="all">All Shows</option>
                <option value="review">Needs Review</option>
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
let allArtists = [];
let currentPage = 0;
const pageSize = 20;
let editingShow = null;

async function loadStats() {
    const res = await fetch('/api/stats');
    const stats = await res.json();
    document.getElementById('stats').textContent =
        `${stats.total_shows.toLocaleString()} shows | ${stats.total_artists.toLocaleString()} artists`;

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

async function loadArtists() {
    const res = await fetch('/api/artists-simple');
    allArtists = await res.json();
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
        list.innerHTML = '<div class="empty-state"><h2>No shows found</h2></div>';
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
                <div style="flex: 1; position: relative;">
                    <input type="text"
                           value="${escapeHtml(a.name)}"
                           data-index="${i}"
                           data-show="${show.id}"
                           oninput="handleArtistInput(this, '${show.id}', ${i})"
                           onblur="hideAutocomplete(this)"
                           onfocus="handleArtistInput(this, '${show.id}', ${i})">
                    <div class="artist-autocomplete" id="autocomplete-${show.id}-${i}"></div>
                </div>
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

            <div class="artists-section">
                <h4>Artists</h4>
                <div class="artist-list" id="artists-${show.id}">
                    ${artistsHtml}
                </div>
                ${isEditing ? `
                    <button onclick="addArtist('${show.id}')" class="secondary" style="margin-top: 8px;">+ Add Artist</button>
                ` : ''}
            </div>

            <div class="actions">
                ${isEditing ? `
                    <button onclick="saveShow('${show.id}')" class="success">Save Changes</button>
                    <button onclick="cancelEdit()" class="secondary">Cancel</button>
                ` : `
                    <button onclick="startEdit('${show.id}')">Edit Artists</button>
                `}
            </div>
        </div>
    `;
}

function handleArtistInput(input, showId, index) {
    const value = input.value.toLowerCase();
    const autocomplete = document.getElementById(`autocomplete-${showId}-${index}`);

    if (value.length < 2) {
        autocomplete.classList.remove('show');
        return;
    }

    // Filter artists
    const matches = allArtists.filter(a =>
        a.name.toLowerCase().includes(value) ||
        a.aliases.some(alias => alias.toLowerCase().includes(value))
    ).slice(0, 10);

    if (matches.length === 0) {
        autocomplete.classList.remove('show');
        return;
    }

    autocomplete.innerHTML = matches.map(artist => `
        <div class="artist-autocomplete-item" onmousedown="selectAutocompleteArtist('${showId}', ${index}, '${escapeHtml(artist.name).replace(/'/g, "\\'")}')">
            <div class="name">${escapeHtml(artist.name)}</div>
            <div class="stats">${artist.show_count} shows${artist.aliases.length > 0 ? ` | aka: ${artist.aliases.join(', ')}` : ''}</div>
        </div>
    `).join('');

    autocomplete.classList.add('show');
}

function selectAutocompleteArtist(showId, index, name) {
    const show = shows.find(s => s.id === showId);
    if (show) {
        show.artists[index].name = name;
        renderShows();
    }
}

function hideAutocomplete(input) {
    setTimeout(() => {
        const showId = input.dataset.show;
        const index = input.dataset.index;
        const autocomplete = document.getElementById(`autocomplete-${showId}-${index}`);
        if (autocomplete) autocomplete.classList.remove('show');
    }, 200);
}

function startEdit(showId) {
    editingShow = showId;
    renderShows();
}

function cancelEdit() {
    editingShow = null;
    loadShows();
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
            artists: show.artists
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

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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
loadArtists();
loadShows();
</script>
</body>
</html>
"""

# API Routes

@app.route('/')
def index():
    return render_template_string(ARTISTS_PAGE)

@app.route('/shows')
def shows_page():
    return render_template_string(SHOWS_PAGE)

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

@app.route('/api/artists-simple')
def get_artists_simple():
    """Lightweight artist list for autocomplete"""
    all_artists = store.all_artists()
    result = []
    for artist in all_artists:
        result.append({
            'id': artist.id,
            'name': artist.name,
            'aliases': artist.aliases or [],
            'show_count': store.get_artist_show_count(artist.id)
        })
    return jsonify(result)

@app.route('/api/shows')
def get_shows():
    filter_type = request.args.get('filter', 'all')
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
                    'is_headliner': sa.is_headliner
                })

        result.append({
            'id': show.id,
            'date': show.date,
            'title': show.title,
            'event_type': show.event_type,
            'artists': artists
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
                is_headliner=artist_data.get('is_headliner', False)
            ))
        show.artists = new_artists

    store.update_show(show)
    store.save()

    return jsonify({'success': True})

@app.route('/api/artists')
def get_artists():
    search = request.args.get('search', '').lower()

    all_artists = store.all_artists()

    # Calculate show counts
    result = []
    for artist in all_artists:
        show_count = store.get_artist_show_count(artist.id)

        # Filter by search
        if search:
            name_match = search in artist.name.lower()
            alias_match = any(search in alias.lower() for alias in (artist.aliases or []))
            if not (name_match or alias_match):
                continue

        result.append({
            'id': artist.id,
            'name': artist.name,
            'aliases': artist.aliases or [],
            'show_count': show_count,
            'spotify_url': artist.spotify_url,
            'website': artist.website
        })

    # Sort by show count descending
    result.sort(key=lambda x: x['show_count'], reverse=True)

    return jsonify(result)

@app.route('/api/artists', methods=['POST'])
def create_artist():
    data = request.json
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Artist name is required'}), 400

    # Check if artist already exists
    existing = store.find_artist_by_name(name)
    if existing:
        return jsonify({'error': f'Artist "{name}" already exists'}), 400

    artist = Artist(
        name=name,
        aliases=data.get('aliases', []),
        spotify_url=data.get('spotify_url'),
        website=data.get('website')
    )

    store.add_artist(artist)
    store.save()

    return jsonify({'success': True, 'id': artist.id})

@app.route('/api/artists/merge', methods=['POST'])
def merge_artists():
    """
    Merge multiple artists into one.

    Body:
    {
        "primary_id": "artist-uuid-to-keep",
        "merge_ids": ["artist-uuid-1", "artist-uuid-2", ...]
    }
    """
    data = request.json
    primary_id = data.get('primary_id')
    merge_ids = data.get('merge_ids', [])

    if not primary_id or not merge_ids:
        return jsonify({'error': 'primary_id and merge_ids are required'}), 400

    # Get primary artist
    primary = store.get_artist(primary_id)
    if not primary:
        return jsonify({'error': 'Primary artist not found'}), 404

    # Get artists to merge
    merge_artists = []
    for artist_id in merge_ids:
        artist = store.get_artist(artist_id)
        if not artist:
            return jsonify({'error': f'Artist {artist_id} not found'}), 404
        merge_artists.append(artist)

    # Collect all aliases
    all_aliases = set(primary.aliases or [])
    for artist in merge_artists:
        # Add the artist's name as an alias
        all_aliases.add(artist.name)
        # Add their aliases
        if artist.aliases:
            all_aliases.update(artist.aliases)

    # Remove primary name from aliases if present
    all_aliases.discard(primary.name)
    primary.aliases = sorted(list(all_aliases))

    # Update all shows that reference merged artists to use primary
    all_shows = store.all_shows()
    updated_count = 0

    for show in all_shows:
        updated = False
        for i, show_artist in enumerate(show.artists):
            if show_artist.artist_id in merge_ids:
                # Replace with primary artist
                show.artists[i].artist_id = primary_id
                updated = True

        if updated:
            store.update_show(show)
            updated_count += 1

    # Update primary artist
    store.update_artist(primary)

    # Delete merged artists
    for artist in merge_artists:
        del store._artists[artist.id]

    # Rebuild index
    store._rebuild_index()

    # Save everything
    store.save()

    return jsonify({
        'success': True,
        'updated_shows': updated_count,
        'merged_count': len(merge_artists),
        'primary': {
            'id': primary.id,
            'name': primary.name,
            'aliases': primary.aliases
        }
    })

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("Provo Music Museum - Admin Tool")
    print("=" * 50)
    print(f"\nOpen http://127.0.0.1:5002 in your browser")
    print("Press Ctrl+C to stop\n")
    app.run(host='127.0.0.1', port=5002, debug=False)
