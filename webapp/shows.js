// Shows Management Page
let showsData = [];
let originalShowsData = [];
let artistsData = [];
let artistsStats = {}; // Cache of artist statistics calculated from shows
let changes = [];
let currentEditIndex = null;

// Initialize
async function init() {
    await loadData();
    setupEventListeners();
    renderTable();
    updateStats();
    updateChangesCount();
}

// Load data
async function loadData() {
    try {
        // Load shows data - try multiple paths
        let response = await fetch('shows_data.csv');
        if (!response.ok) {
            response = await fetch('../data/exports/velour_complete_historical_20251011_150605.csv');
        }
        if (!response.ok) {
            throw new Error('Could not load shows data');
        }
        
        const csvText = await response.text();
        showsData = parseShowsCSV(csvText);
        
        // Filter out invalid shows
        showsData = filterInvalidShows(showsData);
        
        originalShowsData = JSON.parse(JSON.stringify(showsData));
        
        // Load artists data for suggestions
        let artistsResponse = await fetch('artists_data.csv');
        if (!artistsResponse.ok) {
            artistsResponse = await fetch('../data/processed/artists_20260102_211457.csv');
        }
        if (artistsResponse.ok) {
            const artistsCsv = await artistsResponse.text();
            artistsData = parseArtistsCSV(artistsCsv);
        } else {
            console.warn('Could not load artists data for suggestions');
        }
        
        // Calculate initial artist statistics
        recalculateArtistStats();
        
        // Load saved changes
        const loadedFromStorage = loadSavedChanges();
        
        if (loadedFromStorage) {
            console.log('Loaded shows data from localStorage');
            // Recalculate stats after loading from storage
            recalculateArtistStats();
        } else {
            console.log('Loaded shows data from CSV file');
        }
        
        // Populate year filter
        populateYearFilter();
        
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading shows data. Please make sure the CSV file exists.');
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
        
        // Parse artists string into array
        if (obj.artists) {
            obj.artists_list = obj.artists.split(',').map(a => a.trim()).filter(a => a);
        } else {
            obj.artists_list = [];
        }
        
        // Parse date
        if (obj.date) {
            try {
                const date = new Date(obj.date);
                obj.dateObj = date;
                obj.year = date.getFullYear();
            } catch (e) {
                obj.dateObj = null;
                obj.year = parseInt(obj.year) || null;
            }
        }
        
        return obj;
    }).filter(show => show.title && show.title.trim());
}

// Filter out invalid shows
function filterInvalidShows(shows) {
    return shows.filter(show => {
        const title = (show.title || '').trim();
        const description = (show.description || '').trim();
        const titleLower = title.toLowerCase();
        const descLower = description.toLowerCase();
        
        // Filter out navigation elements
        if (titleLower.includes('find a month') || descLower.includes('find a month')) {
            return false;
        }
        
        // Filter out entries that are just month names or month/year
        if (/^(january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{0,4}$/i.test(title.trim())) {
            return false;
        }
        
        // Filter out entries that match pattern like "Jan 2006" or "January 2006"
        if (/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}$/i.test(title.trim())) {
            return false;
        }
        
        // Filter out very short or empty titles
        if (title.length < 5) {
            return false;
        }
        
        // Filter out entries that are just dates or navigation
        if (title === description && title.length < 20) {
            // Could be a navigation element
            if (!title.includes('pm') && !title.includes('»') && !title.includes('w/')) {
                return false;
            }
        }
        
        return true;
    });
}

// Extract artists from title/description text
function extractArtistsFromText(text) {
    if (!text) return [];
    
    const artists = [];
    const normalizedText = text.toLowerCase();
    
    // Skip if it's clearly not a show description
    if (normalizedText.includes('find a month') || 
        normalizedText.length < 10 ||
        /^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*\d{4}$/i.test(text.trim())) {
        return [];
    }
    
    // Try to match against known artists first
    const knownArtists = [];
    artistsData.forEach(artist => {
        const artistName = artist.artist_name || '';
        const normalizedName = (artist.normalized_name || '').toLowerCase();
        const nameLower = artistName.toLowerCase();
        
        // Check if artist name appears in text (case insensitive)
        if (nameLower.length > 2 && normalizedText.includes(normalizedName)) {
            knownArtists.push(artistName);
        }
    });
    
    if (knownArtists.length > 0) {
        return [...new Set(knownArtists)]; // Remove duplicates
    }
    
    // Fallback: try to extract from common patterns
    const extracted = [];
    
    // Pattern 1: "Artist w/ Artist2, Artist3"
    const wPattern = /\b([A-Z][a-zA-Z\s&'.-]+?)\s+w\/\s+([A-Z][a-zA-Z\s&'.,-]+)/gi;
    let match;
    while ((match = wPattern.exec(text)) !== null) {
        extracted.push(match[1].trim());
        // Split the second part by comma
        match[2].split(',').forEach(a => {
            const cleaned = a.trim().replace(/\s*\$\d+.*$/i, '').replace(/\s*sold out.*$/i, '');
            if (cleaned.length > 1) extracted.push(cleaned);
        });
    }
    
    // Pattern 2: Comma-separated list (after removing genre prefix)
    if (extracted.length === 0 && text.includes(',')) {
        // Remove genre prefix like "(indie-rock) " or "8pm» "
        const cleaned = text.replace(/^\([^)]+\)\s*/, '').replace(/^\d+pm[»\s]*/i, '');
        const parts = cleaned.split(',');
        parts.forEach(part => {
            part = part.trim();
            // Remove price info, "SOLD OUT", etc.
            part = part.replace(/\s*\$\d+.*$/i, '').replace(/\s*\*?\s*sold out.*$/i, '');
            part = part.replace(/\s*w\/\s*/gi, ' '); // Remove "w/" but keep the artists
            if (part.length > 2 && part.length < 100) {
                extracted.push(part);
            }
        });
    }
    
    // Pattern 3: Single artist name (if no commas or "w/")
    if (extracted.length === 0 && !text.includes(',') && !text.toLowerCase().includes('w/')) {
        // Remove common prefixes
        let cleaned = text.replace(/^\([^)]+\)\s*/, '').replace(/^\d+pm[»\s]*/i, '');
        cleaned = cleaned.replace(/\s*\$\d+.*$/i, '').replace(/\s*sold out.*$/i, '');
        cleaned = cleaned.trim();
        if (cleaned.length > 2 && cleaned.length < 100) {
            extracted.push(cleaned);
        }
    }
    
    // Clean up extracted names
    return extracted
        .map(name => {
            // Remove quotes
            name = name.replace(/^["']|["']$/g, '');
            // Remove trailing punctuation except apostrophes
            name = name.replace(/[.,;:!?]+$/, '');
            return name.trim();
        })
        .filter(name => {
            // Filter out invalid names
            if (name.length < 2 || name.length > 100) return false;
            if (/^\d+$/.test(name)) return false; // Just numbers
            if (name.toLowerCase() === 'open-mic' || name.toLowerCase() === 'open mic') return false;
            if (name.toLowerCase().includes('find a month')) return false;
            return true;
        })
        .slice(0, 10); // Limit to 10 artists
}

// Parse artists CSV (simplified version)
function parseArtistsCSV(csvText) {
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
        
        return obj;
    }).filter(artist => artist.artist_name);
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', renderTable);
    document.getElementById('clearSearch').addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        renderTable();
    });
    
    document.getElementById('yearFilter').addEventListener('change', renderTable);
    document.getElementById('minArtists').addEventListener('input', renderTable);
    document.getElementById('showOpenMic').addEventListener('change', renderTable);
    
    document.getElementById('saveChangesBtn').addEventListener('click', saveChanges);
    document.getElementById('exportCSVBtn').addEventListener('click', exportCSV);
    document.getElementById('clearChangesBtn').addEventListener('click', clearAllChanges);
    document.getElementById('viewChangesBtn').addEventListener('click', openChangesModal);
    document.getElementById('autoDetectBtn').addEventListener('click', autoDetectAllArtists);
    document.getElementById('autoDetectShowBtn').addEventListener('click', autoDetectShowArtists);
    
    // Edit show modal
    document.getElementById('closeEditShowModal').addEventListener('click', closeEditModal);
    document.getElementById('cancelEditShow').addEventListener('click', closeEditModal);
    document.getElementById('saveShow').addEventListener('click', saveShow);
    
    // Add artist controls
    document.getElementById('addArtistInput').addEventListener('input', handleArtistSearch);
    document.getElementById('addArtistBtn').addEventListener('click', addArtistToShow);
    
    // Changes modal
    document.getElementById('closeChangesModal').addEventListener('click', closeChangesModal);
    document.getElementById('closeChangesModalFooter').addEventListener('click', closeChangesModal);
    document.getElementById('saveChangesFromModal').addEventListener('click', () => {
        closeChangesModal();
        saveChanges();
    });
    
    // Close modals on background click
    window.addEventListener('click', (e) => {
        const editModal = document.getElementById('editShowModal');
        const changesModal = document.getElementById('changesModal');
        if (e.target === editModal) {
            closeEditModal();
        }
        if (e.target === changesModal) {
            closeChangesModal();
        }
    });
}

// Populate year filter
function populateYearFilter() {
    const yearFilter = document.getElementById('yearFilter');
    const years = [...new Set(showsData.map(s => s.year).filter(y => y))].sort((a, b) => b - a);
    
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
}

// Render table
function renderTable() {
    const tbody = document.getElementById('showsTableBody');
    if (!tbody) return;
    
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const yearFilter = document.getElementById('yearFilter').value;
    const minArtists = parseInt(document.getElementById('minArtists').value) || 0;
    const showOpenMic = document.getElementById('showOpenMic').checked;
    
    let filtered = showsData.filter(show => {
        // Search filter
        if (searchTerm) {
            const title = (show.title || '').toLowerCase();
            const description = (show.description || '').toLowerCase();
            const artists = (show.artists || '').toLowerCase();
            const matches = title.includes(searchTerm) || 
                          description.includes(searchTerm) || 
                          artists.includes(searchTerm);
            if (!matches) return false;
        }
        
        // Year filter
        if (yearFilter && show.year != yearFilter) return false;
        
        // Min artists filter
        const artistCount = show.artists_list ? show.artists_list.length : 0;
        if (artistCount < minArtists) return false;
        
        // Open mic filter
        if (!showOpenMic && (show.title || '').toLowerCase().includes('open-mic')) return false;
        
        return true;
    });
    
    // Sort by date (newest first)
    filtered.sort((a, b) => {
        if (a.dateObj && b.dateObj) {
            return b.dateObj - a.dateObj;
        }
        if (a.year && b.year) {
            return b.year - a.year;
        }
        return 0;
    });
    
    tbody.innerHTML = filtered.map((show, index) => {
        const actualIndex = showsData.indexOf(show);
        const dateStr = show.date || `${show.month} ${show.day}, ${show.year}`;
        const artists = show.artists_list || [];
        
        return `
            <tr>
                <td class="show-date">${escapeHtml(dateStr)}</td>
                <td>
                    <div class="show-title">${escapeHtml(show.title || '')}</div>
                    ${show.genre ? `<div style="color: #999; font-size: 12px;">${escapeHtml(show.genre)}</div>` : ''}
                </td>
                <td class="show-description">${escapeHtml(show.description || '')}</td>
                <td>
                    <div class="show-artists">
                        ${artists.length > 0 
                            ? artists.map((artist, artistIdx) => `
                                <span class="artist-tag">
                                    <a href="artist.html" class="artist-link" onclick="viewArtistFromShow('${escapeHtml(artist)}', event)">${escapeHtml(artist)}</a>
                                    <span class="remove-artist-inline" onclick="removeArtistFromShowInline(${actualIndex}, ${artistIdx})" title="Remove artist">×</span>
                                </span>
                            `).join('')
                            : '<span class="no-artists">No artists</span>'
                        }
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="openEditModal(${actualIndex})">Edit</button>
                </td>
            </tr>
        `;
    }).join('');
    
    updateStats();
}

// Open edit modal
function openEditModal(index) {
    currentEditIndex = index;
    const show = showsData[index];
    
    document.getElementById('editShowDate').value = show.date || '';
    document.getElementById('editShowTitle').value = show.title || '';
    document.getElementById('editShowDescription').value = show.description || '';
    document.getElementById('editShowGenre').value = show.genre || '';
    
    renderShowArtists(show.artists_list || []);
    
    document.getElementById('editShowModal').classList.add('show');
    document.getElementById('addArtistInput').value = '';
    document.getElementById('artistSuggestions').classList.remove('show');
}

// Render show artists in modal
function renderShowArtists(artists) {
    const container = document.getElementById('showArtistsList');
    if (artists.length === 0) {
        container.innerHTML = '<div class="no-artists">No artists added yet</div>';
        return;
    }
    
    container.innerHTML = artists.map((artist, idx) => `
        <span class="artist-tag">
            ${escapeHtml(artist)}
            <span class="remove-artist" onclick="removeArtistFromShow(${idx})" title="Remove artist">×</span>
        </span>
    `).join('');
}

// Remove artist from show (from edit modal)
function removeArtistFromShow(index) {
    if (currentEditIndex === null) return;
    const show = showsData[currentEditIndex];
    if (!show.artists_list) show.artists_list = [];
    
    show.artists_list.splice(index, 1);
    renderShowArtists(show.artists_list);
    
    // Track change
    trackChange('edit', currentEditIndex, show);
}

// Remove artist from show (from table view)
function removeArtistFromShowInline(showIndex, artistIndex) {
    if (showIndex === null || showIndex < 0 || showIndex >= showsData.length) return;
    
    const show = showsData[showIndex];
    if (!show.artists_list || artistIndex < 0 || artistIndex >= show.artists_list.length) return;
    
    // Remove the artist
    const removedArtist = show.artists_list[artistIndex];
    show.artists_list.splice(artistIndex, 1);
    
    // Update the artists string if it exists
    if (show.artists) {
        show.artists = show.artists_list.join(', ');
    }
    
    // Track change
    trackChange('edit', showIndex, show);
    
    // Re-render the table
    renderTable();
    
    // Save to storage
    saveChangesToStorage();
}

// Handle artist search
function handleArtistSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    const suggestions = document.getElementById('artistSuggestions');
    
    if (query.length < 2) {
        suggestions.classList.remove('show');
        return;
    }
    
    // Search artists
    const matches = artistsData
        .filter(artist => {
            const name = (artist.artist_name || '').toLowerCase();
            const normalized = (artist.normalized_name || '').toLowerCase();
            return name.includes(query) || normalized.includes(query);
        })
        .slice(0, 10)
        .map(artist => artist.artist_name);
    
    // Also include the query itself if it doesn't match
    if (query && !matches.includes(query)) {
        matches.unshift(query);
    }
    
    if (matches.length > 0) {
        suggestions.innerHTML = matches.map(name => `
            <div class="suggestion-item" onclick="selectArtistSuggestion('${escapeHtml(name)}')">
                ${escapeHtml(name)}
            </div>
        `).join('');
        suggestions.classList.add('show');
    } else {
        suggestions.classList.remove('show');
    }
}

// Select artist suggestion
function selectArtistSuggestion(name) {
    document.getElementById('addArtistInput').value = name;
    document.getElementById('artistSuggestions').classList.remove('show');
    addArtistToShow();
}

// Add artist to show
function addArtistToShow() {
    if (currentEditIndex === null) return;
    
    const input = document.getElementById('addArtistInput');
    const artistName = input.value.trim();
    
    if (!artistName) return;
    
    const show = showsData[currentEditIndex];
    if (!show.artists_list) show.artists_list = [];
    
    // Check if already added
    if (show.artists_list.includes(artistName)) {
        alert('This artist is already added to the show.');
        return;
    }
    
    show.artists_list.push(artistName);
    renderShowArtists(show.artists_list);
    
    input.value = '';
    document.getElementById('artistSuggestions').classList.remove('show');
    
    // Track change
    trackChange('edit', currentEditIndex, show);
}

// Save show
function saveShow() {
    if (currentEditIndex === null) return;
    
    const show = showsData[currentEditIndex];
    
    // Update show data
    show.date = document.getElementById('editShowDate').value;
    show.title = document.getElementById('editShowTitle').value;
    show.description = document.getElementById('editShowDescription').value;
    show.genre = document.getElementById('editShowGenre').value;
    
    // Update artists string
    show.artists = show.artists_list.join(', ');
    
    // Update date parsing
    if (show.date) {
        try {
            const date = new Date(show.date);
            show.dateObj = date;
            show.year = date.getFullYear();
        } catch (e) {
            // Keep existing year if date parsing fails
        }
    }
    
    // Track change
    trackChange('edit', currentEditIndex, show);
    
    // Sync new artists immediately
    syncNewArtistsToDataset();
    
    closeEditModal();
    renderTable();
    saveChangesToStorage();
}

// Close edit modal
function closeEditModal() {
    document.getElementById('editShowModal').classList.remove('show');
    currentEditIndex = null;
}

// Track change and update artist stats
function trackChange(type, index, data) {
    // Remove existing change for this show
    changes = changes.filter(c => !(c.type === type && c.index === index));
    
    changes.push({
        type: type,
        index: index,
        data: JSON.parse(JSON.stringify(data)),
        timestamp: new Date().toISOString()
    });
    
    // Recalculate artist statistics when shows change
    recalculateArtistStats();
    
    updateChangesCount();
    saveChangesToStorage();
}

// Recalculate artist statistics from current shows data
function recalculateArtistStats() {
    const stats = {};
    
    showsData.forEach(show => {
        if (!show.artists_list || show.artists_list.length === 0) return;
        
        const year = show.year ? parseInt(show.year) : null;
        if (!year) return;
        
        show.artists_list.forEach(artistName => {
            if (!artistName || artistName.trim() === '') return;
            
            const normalized = artistName.toLowerCase().trim();
            
            if (!stats[normalized]) {
                stats[normalized] = {
                    artist_name: artistName,
                    normalized_name: normalized,
                    total_shows: 0,
                    years_active: new Set(),
                    first_year: null,
                    last_year: null
                };
            }
            
            stats[normalized].total_shows++;
            stats[normalized].years_active.add(year);
            
            if (!stats[normalized].first_year || year < stats[normalized].first_year) {
                stats[normalized].first_year = year;
            }
            if (!stats[normalized].last_year || year > stats[normalized].last_year) {
                stats[normalized].last_year = year;
            }
        });
    });
    
    // Convert Set to sorted array and calculate years_span
    Object.keys(stats).forEach(normalized => {
        const stat = stats[normalized];
        stat.years_active = Array.from(stat.years_active).sort();
        stat.years_span = stat.last_year && stat.first_year ? stat.last_year - stat.first_year : 0;
    });
    
    artistsStats = stats;
    console.log(`Recalculated stats for ${Object.keys(stats).length} artists`);
}

// Sync artist name changes from editor when shows page loads
function syncArtistChangesFromEditorOnLoad() {
    try {
        const artistsDataStr = localStorage.getItem('velour_artists_data');
        if (!artistsDataStr) return;
        
        const artistsData = JSON.parse(artistsDataStr);
        const artistNameMap = new Map(); // normalized -> current name
        
        // Build map of current artist names
        artistsData.forEach(artist => {
            artistNameMap.set(artist.normalized_name, artist.artist_name);
        });
        
        // Update shows with current artist names
        let showsUpdated = 0;
        showsData.forEach(show => {
            if (show.artists_list && Array.isArray(show.artists_list)) {
                let updated = false;
                show.artists_list = show.artists_list.map(artistName => {
                    const normalized = artistName.toLowerCase().trim();
                    const currentName = artistNameMap.get(normalized);
                    if (currentName && currentName !== artistName) {
                        updated = true;
                        return currentName;
                    }
                    return artistName;
                });
                
                if (updated) {
                    showsUpdated++;
                    show.artists = show.artists_list.join(', ');
                }
            }
        });
        
        if (showsUpdated > 0) {
            localStorage.setItem('velour_shows_data', JSON.stringify(showsData));
            console.log(`✅ Synced artist name changes from editor to ${showsUpdated} shows on load`);
        }
    } catch (e) {
        console.error('Error syncing artist changes from editor on load:', e);
    }
}

// View artist from show (navigate to artist detail page)
function viewArtistFromShow(artistName, event) {
    event.preventDefault();
    event.stopPropagation();
    
    // Store artist name in sessionStorage for artist.html to pick up
    sessionStorage.setItem('viewArtist', artistName.toLowerCase().trim());
    
    // Navigate to artist page
    window.location.href = 'artist.html';
}

// Load saved changes
function loadSavedChanges() {
    try {
        const saved = localStorage.getItem('velour_show_changes');
        if (saved) {
            changes = JSON.parse(saved);
            console.log(`Loaded ${changes.length} pending changes from localStorage`);
        }
        
        const savedData = localStorage.getItem('velour_shows_data');
        if (savedData) {
            const parsed = JSON.parse(savedData);
            if (Array.isArray(parsed) && parsed.length > 0) {
                showsData = parsed;
                originalShowsData = JSON.parse(JSON.stringify(showsData));
                console.log(`Loaded ${showsData.length} shows from localStorage`);
                return true; // Indicate data was loaded from storage
            }
        }
        return false; // Data was loaded from CSV file
    } catch (e) {
        console.error('Error loading saved changes:', e);
        return false;
    }
}

// Save changes to storage
function saveChangesToStorage() {
    try {
        localStorage.setItem('velour_show_changes', JSON.stringify(changes));
        localStorage.setItem('velour_shows_data', JSON.stringify(showsData));
        console.log(`Saved ${changes.length} changes and ${showsData.length} shows to localStorage`);
        
        // Sync new artists from shows to artist dataset
        syncNewArtistsToDataset();
    } catch (e) {
        console.error('Error saving to localStorage:', e);
        // If localStorage is full, warn user
        if (e.name === 'QuotaExceededError') {
            alert('Warning: Browser storage is full. Please export your CSV to save your changes permanently.');
        }
    }
}

// Sync new artists from shows to artist dataset
function syncNewArtistsToDataset() {
    try {
        // Get artist data from localStorage
        const artistsDataStr = localStorage.getItem('velour_artists_data');
        let artistsData = [];
        
        if (artistsDataStr) {
            artistsData = JSON.parse(artistsDataStr);
        } else {
            // If no artist data in localStorage, try to load from the CSV we have
            if (artistsData.length === 0) {
                console.log('No artist data in localStorage to sync with');
                return;
            }
        }
        
        // Get all unique artists from shows
        const showsArtists = new Map(); // normalized_name -> { name, stats }
        
        showsData.forEach(show => {
            if (!show.artists_list || show.artists_list.length === 0) return;
            
            const year = show.year ? parseInt(show.year) : null;
            if (!year) return;
            
            show.artists_list.forEach(artistName => {
                if (!artistName || artistName.trim() === '') return;
                
                const normalized = artistName.toLowerCase().trim();
                
                if (!showsArtists.has(normalized)) {
                    showsArtists.set(normalized, {
                        artist_name: artistName,
                        normalized_name: normalized,
                        total_shows: 0,
                        years_active: new Set(),
                        first_year: null,
                        last_year: null
                    });
                }
                
                const artist = showsArtists.get(normalized);
                artist.total_shows++;
                artist.years_active.add(year);
                
                if (!artist.first_year || year < artist.first_year) {
                    artist.first_year = year;
                }
                if (!artist.last_year || year > artist.last_year) {
                    artist.last_year = year;
                }
            });
        });
        
        // Find new artists that don't exist in the dataset
        let newArtistsAdded = 0;
        showsArtists.forEach((showArtist, normalized) => {
            const exists = artistsData.find(a => 
                a.normalized_name === normalized || 
                a.normalized_name === showArtist.normalized_name
            );
            
            if (!exists) {
                // Create new artist entry
                const newArtist = {
                    artist_name: showArtist.artist_name,
                    normalized_name: showArtist.normalized_name,
                    total_shows: showArtist.total_shows,
                    connection_count: 0, // Will be calculated when network is regenerated
                    years_active: Array.from(showArtist.years_active).sort(),
                    first_year: showArtist.first_year,
                    last_year: showArtist.last_year,
                    years_span: showArtist.last_year && showArtist.first_year ? 
                        showArtist.last_year - showArtist.first_year : 0
                };
                
                artistsData.push(newArtist);
                newArtistsAdded++;
                console.log(`➕ Adding new artist: ${showArtist.artist_name}`);
            } else {
                // Update existing artist stats if shows data is more recent
                exists.total_shows = Math.max(exists.total_shows, showArtist.total_shows);
                if (showArtist.first_year && (!exists.first_year || showArtist.first_year < exists.first_year)) {
                    exists.first_year = showArtist.first_year;
                }
                if (showArtist.last_year && (!exists.last_year || showArtist.last_year > exists.last_year)) {
                    exists.last_year = showArtist.last_year;
                }
                // Merge years_active
                if (showArtist.years_active.size > 0) {
                    const combinedYears = new Set([...(exists.years_active || []), ...showArtist.years_active]);
                    exists.years_active = Array.from(combinedYears).sort();
                    exists.years_span = exists.years_active.length;
                }
            }
        });
        
        if (newArtistsAdded > 0 || showsArtists.size > 0) {
            // Save updated artist data back to localStorage
            localStorage.setItem('velour_artists_data', JSON.stringify(artistsData));
            console.log(`✅ Synced ${newArtistsAdded} new artists from shows to artist dataset`);
        }
    } catch (e) {
        console.error('Error syncing new artists to dataset:', e);
    }
}

// Update stats
function updateStats() {
    const total = showsData.length;
    const filtered = document.querySelectorAll('#showsTableBody tr').length;
    document.getElementById('statsText').textContent = `${total} shows, ${filtered} shown`;
}

// Update changes count
function updateChangesCount() {
    const count = changes.length;
    document.getElementById('changesCount').textContent = count;
    document.getElementById('changesCountSummary').textContent = count;
}

// Open changes modal
function openChangesModal() {
    const modal = document.getElementById('changesModal');
    const summary = document.getElementById('changesSummary');
    const list = document.getElementById('changesList');
    
    if (changes.length === 0) {
        summary.innerHTML = '<p>No pending changes.</p>';
        list.innerHTML = '';
    } else {
        summary.innerHTML = `<p><strong>${changes.length}</strong> pending change${changes.length > 1 ? 's' : ''}</p>`;
        list.innerHTML = changes.map((change, idx) => {
            const show = showsData[change.index];
            return `
                <div class="change-item">
                    <strong>${show.title || 'Untitled Show'}</strong> (${show.date || 'No date'})
                    <div style="font-size: 12px; color: #666; margin-top: 4px;">
                        ${change.type === 'edit' ? 'Modified' : change.type}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    modal.classList.add('show');
}

// Close changes modal
function closeChangesModal() {
    document.getElementById('changesModal').classList.remove('show');
}

// Save changes
function saveChanges() {
    if (changes.length === 0) {
        alert('No changes to save.');
        return;
    }
    
    // Changes are already saved to localStorage automatically
    // This button just clears the "pending changes" counter
    if (confirm(`Mark ${changes.length} change${changes.length > 1 ? 's' : ''} as saved? This will clear the changes counter, but your data is already saved in browser storage.`)) {
        // Clear the changes array (data is already in showsData and localStorage)
        changes = [];
        originalShowsData = JSON.parse(JSON.stringify(showsData));
        saveChangesToStorage();
        updateChangesCount();
        alert('Changes counter cleared. Your data is saved in browser storage.\n\n⚠️ IMPORTANT: Browser storage is temporary. Export the CSV to make changes permanent!');
    }
}

// Export CSV
function exportCSV() {
    if (showsData.length === 0) {
        alert('No shows data to export.');
        return;
    }
    
    try {
        // Get headers from first show, including all possible fields
        const sampleShow = showsData[0];
        const headers = Object.keys(sampleShow).filter(key => 
            key !== 'artists_list' && key !== 'dateObj' // Exclude internal fields
        );
        
        // Ensure artists field is included and properly formatted
        if (!headers.includes('artists')) {
            headers.push('artists');
        }
        
        // Convert to CSV
        const csvRows = [];
        
        // Add headers
        csvRows.push(headers.map(h => `"${h}"`).join(','));
        
        showsData.forEach(show => {
            const row = headers.map(header => {
                let value;
                
                // Handle artists field specially - convert array to comma-separated string
                if (header === 'artists') {
                    if (show.artists_list && Array.isArray(show.artists_list)) {
                        value = show.artists_list.join(', ');
                    } else if (show.artists) {
                        value = show.artists;
                    } else {
                        value = '';
                    }
                } else {
                    value = show[header] || '';
                }
                
                // Convert to string
                if (typeof value !== 'string') {
                    value = String(value);
                }
                
                // Escape quotes and wrap in quotes
                value = value.replace(/"/g, '""'); // Escape quotes
                return `"${value}"`; // Always wrap in quotes for CSV safety
            });
            csvRows.push(row.join(','));
        });
        
        const csvContent = csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
        a.download = `velour_shows_edited_${timestamp}.csv`;
        
        // Also try to save to data/downloads/ if possible (for server-side access)
        // Note: This won't work in browser, but the file will be in Downloads
        a.style.display = 'none';
        document.body.appendChild(a);
        
        // Trigger download with a small delay to ensure it works
        setTimeout(() => {
            try {
                a.click();
                setTimeout(() => {
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }, 100);
                
                // Sync new artists before showing success message
                syncNewArtistsToDataset();
                
                alert(`CSV exported successfully! ${showsData.length} shows exported.\n\n✅ New artists have been synced to the artist dataset.\n\nFile: velour_shows_edited_${timestamp}.csv\n\nCheck your Downloads folder.`);
            } catch (error) {
                console.error('Error triggering download:', error);
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                alert('Error exporting CSV. Please check the browser console for details.');
            }
        }, 10);
    } catch (error) {
        console.error('Error exporting CSV:', error);
        alert('Error exporting CSV: ' + error.message);
    }
}

// Clear all changes
function clearAllChanges() {
    if (changes.length === 0) {
        alert('No changes to clear.');
        return;
    }
    
    if (confirm('Clear all changes? This will revert to the original data.')) {
        showsData = JSON.parse(JSON.stringify(originalShowsData));
        changes = [];
        saveChangesToStorage();
        updateChangesCount();
        renderTable();
        alert('All changes cleared.');
    }
}

// Auto-detect artists for a single show
function autoDetectShowArtists() {
    if (currentEditIndex === null) return;
    
    const show = showsData[currentEditIndex];
    const title = show.title || '';
    const description = show.description || '';
    
    // Combine title and description for extraction
    const combinedText = `${title} ${description}`.trim();
    
    const detected = extractArtistsFromText(combinedText);
    
    if (detected.length === 0) {
        alert('No artists could be detected from the title or description.');
        return;
    }
    
    // Add detected artists (avoid duplicates)
    if (!show.artists_list) show.artists_list = [];
    detected.forEach(artist => {
        if (!show.artists_list.includes(artist)) {
            show.artists_list.push(artist);
        }
    });
    
    renderShowArtists(show.artists_list);
    trackChange('edit', currentEditIndex, show);
    
    // Sync new artists immediately
    syncNewArtistsToDataset();
    
    alert(`Detected ${detected.length} artist${detected.length > 1 ? 's' : ''}: ${detected.join(', ')}`);
}

// Auto-detect artists for all shows without artists (in batches)
let batchProcessing = false;
let batchQueue = [];
let currentBatch = 0;
const BATCH_SIZE = 20; // Process 20 shows at a time

function autoDetectAllArtists() {
    const showsWithoutArtists = showsData.filter(show => 
        !show.artists_list || show.artists_list.length === 0
    );
    
    if (showsWithoutArtists.length === 0) {
        alert('All shows already have artists assigned.');
        return;
    }
    
    if (batchProcessing) {
        alert('Batch processing is already in progress. Please wait for the current batch to complete.');
        return;
    }
    
    // Initialize batch processing
    batchQueue = showsWithoutArtists;
    currentBatch = 0;
    batchProcessing = true;
    
    // Update button text
    const btn = document.getElementById('autoDetectBtn');
    if (btn) {
        btn.textContent = 'Processing...';
        btn.disabled = true;
    }
    
    // Process first batch
    processBatch();
}

function processBatch() {
    const startIdx = currentBatch * BATCH_SIZE;
    const endIdx = Math.min(startIdx + BATCH_SIZE, batchQueue.length);
    const batch = batchQueue.slice(startIdx, endIdx);
    
    if (batch.length === 0) {
        // All done!
        batchProcessing = false;
        const btn = document.getElementById('autoDetectBtn');
        if (btn) {
            btn.textContent = 'Auto-Detect Artists';
            btn.disabled = false;
        }
        
        const detectedCount = batchQueue.filter((show, idx) => {
            const showIndex = showsData.indexOf(show);
            return showsData[showIndex].artists_list && showsData[showIndex].artists_list.length > 0;
        }).length;
        
        const totalArtists = batchQueue.reduce((sum, show) => {
            const showIndex = showsData.indexOf(show);
            return sum + (showsData[showIndex].artists_list ? showsData[showIndex].artists_list.length : 0);
        }, 0);
        
        // Final sync of all new artists
        syncNewArtistsToDataset();
        
        saveChangesToStorage();
        renderTable();
        
        alert(`Auto-detection complete!\n\n- ${detectedCount} shows updated\n- ${totalArtists} artists added\n- ${batchQueue.length - detectedCount} shows still need manual review\n\n✅ New artists have been synced to the artist dataset.`);
        return;
    }
    
    let batchDetectedCount = 0;
    let batchTotalArtists = 0;
    
    batch.forEach((show) => {
        const title = show.title || '';
        const description = show.description || '';
        const combinedText = `${title} ${description}`.trim();
        
        const detected = extractArtistsFromText(combinedText);
        
        if (detected.length > 0) {
            if (!show.artists_list) show.artists_list = [];
            const beforeCount = show.artists_list.length;
            detected.forEach(artist => {
                // Clean up artist name (remove leading/trailing punctuation)
                const cleaned = artist.trim().replace(/^[.,;:!?)\]]+/, '').replace(/[.,;:!?(\[]+$/, '').trim();
                if (cleaned && cleaned.length > 1 && !show.artists_list.includes(cleaned)) {
                    show.artists_list.push(cleaned);
                }
            });
            const afterCount = show.artists_list.length;
            const added = afterCount - beforeCount;
            
            if (added > 0) {
                batchDetectedCount++;
                batchTotalArtists += added;
                
                // Update artists string
                show.artists = show.artists_list.join(', ');
                
                // Track change
                const showIndex = showsData.indexOf(show);
                trackChange('edit', showIndex, show);
            }
        }
    });
    
    // Update progress
    const progress = Math.round(((endIdx) / batchQueue.length) * 100);
    const btn = document.getElementById('autoDetectBtn');
    if (btn) {
        btn.textContent = `Processing... ${endIdx}/${batchQueue.length} (${progress}%)`;
    }
    
    console.log(`Batch ${currentBatch + 1}: Processed ${batch.length} shows, detected artists for ${batchDetectedCount} shows, added ${batchTotalArtists} artists`);
    
    // Sync new artists after each batch
    syncNewArtistsToDataset();
    
    // Save progress
    saveChangesToStorage();
    renderTable();
    
    // Process next batch after a short delay
    currentBatch++;
    setTimeout(() => {
        processBatch();
    }, 100); // Small delay to allow UI to update
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on load
init();

