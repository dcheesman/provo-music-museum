// Artist Detail Page with Similarity Search
let artistsData = [];
let networkData = null;
let showsData = []; // Load show data for timeline
let currentArtist = null;

// Initialize
async function init() {
    await loadData();
    setupEventListeners();
    
    // Check if we should view a specific artist (from editor page or shows page)
    const viewArtist = sessionStorage.getItem('viewArtist');
    if (viewArtist) {
        sessionStorage.removeItem('viewArtist'); // Clear it after use
        // Wait a moment for data to be fully loaded, then find and display the artist
        setTimeout(() => {
            // Try to find by normalized name first
            let artist = artistsData.find(a => a.normalized_name === viewArtist);
            
            // If not found, try to find by artist name (case-insensitive)
            if (!artist) {
                artist = artistsData.find(a => 
                    a.artist_name.toLowerCase().trim() === viewArtist ||
                    a.normalized_name === viewArtist.toLowerCase().trim()
                );
            }
            
            if (artist) {
                displayArtistDetail(artist);
                findSimilarArtists(artist);
                findConnectedArtists(artist);
                // Set the search input
                document.getElementById('artistSearch').value = artist.artist_name;
                // Hide search results
                document.getElementById('searchResults').classList.remove('show');
            } else {
                console.warn('Artist not found:', viewArtist);
                // Still try to show timeline if we have shows data
                if (showsData.length > 0) {
                    // Create a temporary artist object for display
                    const tempArtist = {
                        artist_name: viewArtist,
                        normalized_name: viewArtist.toLowerCase().trim(),
                        total_shows: 0,
                        connection_count: 0
                    };
                    displayArtistDetail(tempArtist);
                }
            }
        }, 200); // Increased timeout to ensure shows data is loaded
    }
    
    // Also check for editArtist (from "Edit in Editor" button)
    const editArtist = sessionStorage.getItem('editArtist');
    if (editArtist) {
        sessionStorage.removeItem('editArtist');
        setTimeout(() => {
            selectArtist(editArtist);
        }, 100);
    }
}

// Load data
async function loadData() {
    try {
        // Load artists data
        let response = await fetch('artists_data.csv');
        if (!response.ok) {
            response = await fetch('../data/processed/artists_20260102_211457.csv');
        }
        if (!response.ok) {
            throw new Error('Could not load artists data');
        }
        
        const csvText = await response.text();
        artistsData = parseCSV(csvText);
        console.log(`Loaded ${artistsData.length} artists`);
        
        // Load network data for connections
        response = await fetch('network_data.json');
        if (!response.ok) {
            response = await fetch('../data/processed/artist_network_enhanced_20260102_211457.json');
        }
        if (response.ok) {
            networkData = await response.json();
            console.log('Loaded network data');
        }
        
        // Load shows data for timeline
        response = await fetch('shows_data.csv');
        if (!response.ok) {
            response = await fetch('../data/exports/velour_complete_historical_20251011_150605.csv');
        }
        if (response.ok) {
            const showsCsv = await response.text();
            showsData = parseShowsCSV(showsCsv);
            console.log(`Loaded ${showsData.length} shows for timeline`);
        } else {
            console.warn('Could not load shows data for timeline');
        }
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading data. Please make sure the data files exist.');
    }
}

// Parse shows CSV
function parseShowsCSV(csvText) {
    const lines = csvText.split('\n').filter(line => line.trim());
    if (lines.length === 0) return [];
    
    const headers = lines[0].split(',').map(h => h.trim());
    
    return lines.slice(1).map(line => {
        const values = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                values.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        values.push(current.trim());
        
        const obj = {};
        headers.forEach((header, index) => {
            let value = values[index] || '';
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1);
            }
            obj[header] = value;
        });
        
        // Parse artists_list if it exists, or create from artists field
        if (obj.artists_list) {
            try {
                obj.artists_list = JSON.parse(obj.artists_list);
            } catch (e) {
                obj.artists_list = [];
            }
        } else if (obj.artists) {
            obj.artists_list = obj.artists.split(',').map(a => a.trim()).filter(a => a);
        } else {
            obj.artists_list = [];
        }
        
        return obj;
    });
}

// Simple CSV parser
function parseCSV(csvText) {
    const lines = csvText.split('\n').filter(line => line.trim());
    const headers = lines[0].split(',').map(h => h.trim());
    
    return lines.slice(1).map(line => {
        const values = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                values.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        values.push(current.trim());
        
        const obj = {};
        headers.forEach((header, index) => {
            let value = values[index] || '';
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1);
            }
            obj[header] = value;
        });
        
        // Parse years_active
        if (obj.years_active) {
            try {
                obj.years_active = JSON.parse(obj.years_active);
            } catch (e) {
                obj.years_active = [];
            }
        }
        
        // Convert numbers
        obj.total_shows = parseInt(obj.total_shows) || 0;
        obj.connection_count = parseInt(obj.connection_count) || 0;
        obj.first_year = obj.first_year ? parseInt(obj.first_year) : null;
        obj.last_year = obj.last_year ? parseInt(obj.last_year) : null;
        obj.years_span = parseInt(obj.years_span) || 0;
        
        return obj;
    });
}

// Setup event listeners
function setupEventListeners() {
    // Search
    document.getElementById('searchBtn').addEventListener('click', performSearch);
    document.getElementById('artistSearch').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Modal
    document.getElementById('closeMergeModal').addEventListener('click', closeMergeModal);
    document.getElementById('cancelMerge').addEventListener('click', closeMergeModal);
    document.getElementById('confirmMerge').addEventListener('click', confirmMerge);
    
    // Merge direction change
    document.querySelectorAll('input[name="mergeDirection"]').forEach(radio => {
        radio.addEventListener('change', updateMergePreview);
    });
    
    // Edit in editor
    document.getElementById('editInEditor').addEventListener('click', () => {
        if (currentArtist) {
            // Store current artist in sessionStorage and redirect
            sessionStorage.setItem('editArtist', currentArtist.normalized_name);
            window.location.href = 'editor.html';
        }
    });
    
    // Close modal on outside click
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('mergeModal');
        if (e.target === modal) closeMergeModal();
    });
}

// Perform search
function performSearch() {
    const query = document.getElementById('artistSearch').value.trim().toLowerCase();
    if (!query) return;
    
    const results = searchArtists(query);
    displaySearchResults(results);
}

// Search artists with similarity scoring
function searchArtists(query) {
    if (!query) return [];
    
    const results = artistsData.map(artist => {
        const name = artist.artist_name.toLowerCase();
        const normalized = artist.normalized_name.toLowerCase();
        
        // Calculate similarity score
        let score = 0;
        
        // Exact match
        if (name === query || normalized === query) {
            score = 100;
        }
        // Starts with query
        else if (name.startsWith(query) || normalized.startsWith(query)) {
            score = 80;
        }
        // Contains query
        else if (name.includes(query) || normalized.includes(query)) {
            score = 60;
        }
        // Levenshtein distance (simple)
        else {
            const distance = levenshteinDistance(query, name);
            const maxLen = Math.max(query.length, name.length);
            score = Math.max(0, (1 - distance / maxLen) * 50);
        }
        
        // Boost score for similar words
        const queryWords = query.split(/\s+/);
        const nameWords = name.split(/\s+/);
        const commonWords = queryWords.filter(qw => nameWords.some(nw => nw.includes(qw) || qw.includes(nw)));
        if (commonWords.length > 0) {
            score += commonWords.length * 10;
        }
        
        return {
            artist: artist,
            score: Math.min(100, score)
        };
    })
    .filter(result => result.score > 20) // Only show results with some similarity
    .sort((a, b) => b.score - a.score)
    .slice(0, 20); // Top 20 results
    
    return results;
}

// Simple Levenshtein distance
function levenshteinDistance(str1, str2) {
    const matrix = [];
    const len1 = str1.length;
    const len2 = str2.length;
    
    for (let i = 0; i <= len2; i++) {
        matrix[i] = [i];
    }
    
    for (let j = 0; j <= len1; j++) {
        matrix[0][j] = j;
    }
    
    for (let i = 1; i <= len2; i++) {
        for (let j = 1; j <= len1; j++) {
            if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1,
                    matrix[i][j - 1] + 1,
                    matrix[i - 1][j] + 1
                );
            }
        }
    }
    
    return matrix[len2][len1];
}

// Display search results
function displaySearchResults(results) {
    const container = document.getElementById('searchResults');
    
    if (results.length === 0) {
        container.innerHTML = '<div class="search-result-item">No similar artists found</div>';
        container.classList.add('show');
        return;
    }
    
    container.innerHTML = results.map(result => {
        const a = result.artist;
        return `
            <div class="search-result-item" onclick="selectArtist('${a.normalized_name}')">
                <div class="search-result-name">${escapeHtml(a.artist_name)}</div>
                <div class="search-result-details">
                    ${a.total_shows} shows • ${a.connection_count} connections • 
                    Similarity: ${Math.round(result.score)}%
                </div>
            </div>
        `;
    }).join('');
    
    container.classList.add('show');
}

// Select artist
function selectArtist(normalizedName) {
    const artist = artistsData.find(a => a.normalized_name === normalizedName);
    if (!artist) return;
    
    currentArtist = artist;
    displayArtistDetail(artist);
    findSimilarArtists(artist);
    findConnectedArtists(artist);
    
    // Hide search results
    document.getElementById('searchResults').classList.remove('show');
}

// Display artist detail
function displayArtistDetail(artist) {
    currentArtist = artist;
    document.getElementById('artistDetail').style.display = 'block';
    
    // Update header
    document.getElementById('artistName').textContent = artist.artist_name;
    
    // Update stats (use recalculated stats if available, otherwise use artist data)
    const normalized = artist.normalized_name || artist.artist_name.toLowerCase().trim();
    const recalculatedStats = getRecalculatedStats(normalized);
    
    const totalShows = recalculatedStats ? recalculatedStats.total_shows : (artist.total_shows || 0);
    document.getElementById('totalShows').textContent = totalShows;
    document.getElementById('connectionCount').textContent = artist.connection_count || 0;
    
    const yearsActive = recalculatedStats ? recalculatedStats.years_active : (artist.years_active || []);
    document.getElementById('yearsActive').textContent = yearsActive.length > 0 ? yearsActive.join(', ') : '-';
    
    const firstYear = recalculatedStats ? recalculatedStats.first_year : (artist.first_year || null);
    const lastYear = recalculatedStats ? recalculatedStats.last_year : (artist.last_year || null);
    document.getElementById('firstYear').textContent = firstYear || '-';
    document.getElementById('lastYear').textContent = lastYear || '-';
    
    // Find similar and connected artists
    findSimilarArtists(artist);
    findConnectedArtists(artist);
    
    // Render timeline
    renderTimeline(artist);
    
    // Scroll to detail
    document.getElementById('artistDetail').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Get recalculated stats from shows data
function getRecalculatedStats(normalized) {
    if (!showsData || showsData.length === 0) return null;
    
    const stats = {
        total_shows: 0,
        years_active: new Set(),
        first_year: null,
        last_year: null
    };
    
    showsData.forEach(show => {
        if (!show.artists_list || show.artists_list.length === 0) return;
        
        const hasArtist = show.artists_list.some(a => a.toLowerCase().trim() === normalized);
        if (!hasArtist) return;
        
        const year = show.year ? parseInt(show.year) : null;
        if (!year) return;
        
        stats.total_shows++;
        stats.years_active.add(year);
        
        if (!stats.first_year || year < stats.first_year) {
            stats.first_year = year;
        }
        if (!stats.last_year || year > stats.last_year) {
            stats.last_year = year;
        }
    });
    
    return {
        total_shows: stats.total_shows,
        years_active: Array.from(stats.years_active).sort(),
        first_year: stats.first_year,
        last_year: stats.last_year
    };
}

// Render timeline visualization
function renderTimeline(artist) {
    const normalized = artist.normalized_name || artist.artist_name.toLowerCase().trim();
    
    // Find all shows for this artist
    const artistShows = showsData.filter(show => {
        if (!show.artists_list || show.artists_list.length === 0) return false;
        return show.artists_list.some(a => a.toLowerCase().trim() === normalized);
    });
    
    if (artistShows.length === 0) {
        // Remove timeline if it exists
        const existingTimeline = document.getElementById('timelineSection');
        if (existingTimeline) {
            existingTimeline.remove();
        }
        return;
    }
    
    // Group shows by year
    const showsByYear = {};
    artistShows.forEach(show => {
        const year = show.year ? parseInt(show.year) : null;
        if (!year) return;
        
        if (!showsByYear[year]) {
            showsByYear[year] = [];
        }
        showsByYear[year].push(show);
    });
    
    // Get year range
    const years = Object.keys(showsByYear).map(y => parseInt(y)).sort();
    if (years.length === 0) return;
    
    const minYear = years[0];
    const maxYear = years[years.length - 1];
    
    // Create or update timeline section
    let timelineSection = document.getElementById('timelineSection');
    if (!timelineSection) {
        timelineSection = document.createElement('div');
        timelineSection.id = 'timelineSection';
        timelineSection.className = 'timeline-section';
        timelineSection.innerHTML = '<h3>Performance Timeline</h3><div id="timelineContainer"></div>';
        
        // Insert after connections section
        const connectionsSection = document.querySelector('.connections-section');
        if (connectionsSection) {
            connectionsSection.insertAdjacentElement('afterend', timelineSection);
        } else {
            document.getElementById('artistDetail').appendChild(timelineSection);
        }
    }
    
    const container = document.getElementById('timelineContainer');
    container.innerHTML = '';
    
    // Create timeline visualization
    const maxShows = Math.max(...Object.values(showsByYear).map(s => s.length));
    
    const timelineHTML = `
        <div class="timeline-stats">
            <div class="timeline-stat">
                <span class="stat-label">Shows:</span>
                <span class="stat-value">${artistShows.length}</span>
            </div>
            <div class="timeline-stat">
                <span class="stat-label">Years:</span>
                <span class="stat-value">${years.length}</span>
            </div>
            <div class="timeline-stat">
                <span class="stat-label">Span:</span>
                <span class="stat-value">${minYear} - ${maxYear}</span>
            </div>
        </div>
        <div class="timeline-visualization">
            ${years.map(year => {
                const shows = showsByYear[year];
                const showCount = shows.length;
                const heightPercent = maxShows > 0 ? (showCount / maxShows) * 100 : 0;
                
                return `
                    <div class="timeline-year" title="${year}: ${showCount} show${showCount !== 1 ? 's' : ''}">
                        <div class="timeline-bar" style="height: ${heightPercent}%"></div>
                        <div class="timeline-label">${year}</div>
                        <div class="timeline-count">${showCount}</div>
                    </div>
                `;
            }).join('')}
        </div>
        <div class="timeline-shows-list">
            <h4>Shows by Year</h4>
            ${years.map(year => {
                const shows = showsByYear[year];
                return `
                    <div class="year-group">
                        <h5>${year} (${shows.length} show${shows.length !== 1 ? 's' : ''})</h5>
                        <div class="shows-list">
                            ${shows.map(show => {
                                const dateStr = show.date || `${show.month} ${show.day}, ${show.year}`;
                                return `
                                    <div class="show-item">
                                        <span class="show-date">${escapeHtml(dateStr)}</span>
                                        <span class="show-title">${escapeHtml(show.title || 'Untitled')}</span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    
    container.innerHTML = timelineHTML;
}

// Escape HTML helper
function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Find similar artists
function findSimilarArtists(artist) {
    const similar = searchArtists(artist.artist_name)
        .filter(result => result.artist.normalized_name !== artist.normalized_name)
        .slice(0, 10);
    
    const container = document.getElementById('similarArtists');
    
    if (similar.length === 0) {
        container.innerHTML = '<p style="color: #666;">No similar artists found.</p>';
        return;
    }
    
    container.innerHTML = similar.map(result => {
        const a = result.artist;
        return `
            <div class="artist-card">
                <div class="artist-card-header">
                    <span class="artist-card-name">${escapeHtml(a.artist_name)}</span>
                    <span class="similarity-score">${Math.round(result.score)}% similar</span>
                </div>
                <div class="artist-card-stats">
                    <span>${a.total_shows} shows</span>
                    <span>${a.connection_count} connections</span>
                    <span>${a.first_year || '?'} - ${a.last_year || '?'}</span>
                </div>
                <div class="artist-card-actions">
                    <button class="btn btn-primary" onclick="openMergeModal('${artist.normalized_name}', '${a.normalized_name}')">
                        Merge Artists
                    </button>
                    <button class="btn btn-secondary" onclick="selectArtist('${a.normalized_name}')">
                        View Details
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Find connected artists
function findConnectedArtists(artist) {
    if (!networkData) {
        document.getElementById('connectedArtists').innerHTML = '<p style="color: #666;">Network data not available.</p>';
        return;
    }
    
    const connected = [];
    const artistId = artist.normalized_name;
    
    // Find all edges connected to this artist
    networkData.edges.forEach(edge => {
        const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
        const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
        
        if (sourceId === artistId) {
            const connectedArtist = artistsData.find(a => a.normalized_name === targetId);
            if (connectedArtist) {
                connected.push({
                    artist: connectedArtist,
                    showsTogether: edge.shows_together || edge.weight || 1
                });
            }
        } else if (targetId === artistId) {
            const connectedArtist = artistsData.find(a => a.normalized_name === sourceId);
            if (connectedArtist) {
                connected.push({
                    artist: connectedArtist,
                    showsTogether: edge.shows_together || edge.weight || 1
                });
            }
        }
    });
    
    // Sort by shows together
    connected.sort((a, b) => b.showsTogether - a.showsTogether);
    
    const container = document.getElementById('connectedArtists');
    
    if (connected.length === 0) {
        container.innerHTML = '<p style="color: #666;">No connected artists found.</p>';
        return;
    }
    
    container.innerHTML = connected.slice(0, 20).map(item => {
        const a = item.artist;
        return `
            <div class="artist-card">
                <div class="artist-card-header">
                    <span class="artist-card-name">${escapeHtml(a.artist_name)}</span>
                </div>
                <div class="artist-card-stats">
                    <span>${item.showsTogether} show${item.showsTogether !== 1 ? 's' : ''} together</span>
                    <span>${a.total_shows} total shows</span>
                </div>
                <div class="artist-card-actions">
                    <button class="btn btn-secondary" onclick="selectArtist('${a.normalized_name}')">
                        View Details
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Open merge modal
function openMergeModal(sourceNormalized, targetNormalized) {
    const source = artistsData.find(a => a.normalized_name === sourceNormalized);
    const target = artistsData.find(a => a.normalized_name === targetNormalized);
    
    if (!source || !target) return;
    
    // Set up merge modal
    document.getElementById('sourceName1').textContent = source.artist_name;
    document.getElementById('sourceName1b').textContent = source.artist_name;
    document.getElementById('sourceName1d').textContent = source.artist_name;
    document.getElementById('targetName1').textContent = target.artist_name;
    document.getElementById('targetName1b').textContent = target.artist_name;
    document.getElementById('targetName1c').textContent = target.artist_name;
    
    document.getElementById('sourceName2').textContent = target.artist_name;
    document.getElementById('sourceName2b').textContent = target.artist_name;
    document.getElementById('sourceName2c').textContent = source.artist_name;
    document.getElementById('targetName2').textContent = source.artist_name;
    document.getElementById('targetName2b').textContent = source.artist_name;
    document.getElementById('targetName2d').textContent = target.artist_name;
    
    // Store merge data
    window.mergeSource = source;
    window.mergeTarget = target;
    
    updateMergePreview();
    document.getElementById('mergeModal').classList.add('show');
}

// Update merge preview
function updateMergePreview() {
    if (!window.mergeSource || !window.mergeTarget) return;
    
    const direction = document.querySelector('input[name="mergeDirection"]:checked').value;
    const source = direction === 'into' ? window.mergeSource : window.mergeTarget;
    const target = direction === 'into' ? window.mergeTarget : window.mergeSource;
    
    document.getElementById('previewSourceName').textContent = source.artist_name;
    document.getElementById('previewSourceShows').textContent = source.total_shows;
    document.getElementById('previewSourceConnections').textContent = source.connection_count;
    
    document.getElementById('previewTargetName').textContent = target.artist_name;
    document.getElementById('previewTargetShows').textContent = target.total_shows;
    document.getElementById('previewTargetConnections').textContent = target.connection_count;
    
    document.getElementById('previewResultName').textContent = target.artist_name;
    document.getElementById('previewResultShows').textContent = source.total_shows + target.total_shows;
    document.getElementById('previewResultConnections').textContent = Math.max(source.connection_count, target.connection_count);
}

// Close merge modal
function closeMergeModal() {
    document.getElementById('mergeModal').classList.remove('show');
    window.mergeSource = null;
    window.mergeTarget = null;
}

// Confirm merge
function confirmMerge() {
    if (!window.mergeSource || !window.mergeTarget) return;
    
    const direction = document.querySelector('input[name="mergeDirection"]:checked').value;
    const source = direction === 'into' ? window.mergeSource : window.mergeTarget;
    const target = direction === 'into' ? window.mergeTarget : window.mergeSource;
    
    // Create merge change
    const change = {
        type: 'merge',
        source: { ...source },
        target: { ...target },
        sourceIndex: artistsData.indexOf(source),
        targetIndex: artistsData.indexOf(target)
    };
    
    // Apply merge locally
    target.total_shows += source.total_shows;
    target.connection_count = Math.max(target.connection_count, source.connection_count);
    
    if (source.first_year && (!target.first_year || source.first_year < target.first_year)) {
        target.first_year = source.first_year;
    }
    if (source.last_year && (!target.last_year || source.last_year > target.last_year)) {
        target.last_year = source.last_year;
    }
    
    // Merge years_active
    if (source.years_active && Array.isArray(source.years_active)) {
        const combinedYears = new Set([...(target.years_active || []), ...source.years_active]);
        target.years_active = Array.from(combinedYears).sort();
        target.years_span = target.years_active.length;
    }
    
    // Remove source
    artistsData.splice(artistsData.indexOf(source), 1);
    
    // Save to localStorage (same as editor)
    try {
        const existingChanges = JSON.parse(localStorage.getItem('velour_artist_changes') || '[]');
        existingChanges.push(change);
        localStorage.setItem('velour_artist_changes', JSON.stringify(existingChanges));
        localStorage.setItem('velour_artists_data', JSON.stringify(artistsData));
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
    
    closeMergeModal();
    
    // Update display
    if (currentArtist && currentArtist.normalized_name === source.normalized_name) {
        // If we merged the current artist, switch to target
        selectArtist(target.normalized_name);
    } else {
        // Otherwise refresh the current view
        selectArtist(currentArtist.normalized_name);
    }
    
    alert(`Merge completed! Changes saved to localStorage.\n\nTo apply permanently, go to the Editor and click "Save Changes".`);
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions available globally
window.selectArtist = selectArtist;
window.openMergeModal = openMergeModal;

// Check if we should edit an artist from editor
window.addEventListener('load', () => {
    const editArtist = sessionStorage.getItem('editArtist');
    if (editArtist) {
        sessionStorage.removeItem('editArtist');
        selectArtist(editArtist);
    }
});

// Initialize
init();

