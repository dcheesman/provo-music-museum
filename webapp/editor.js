// Artist Data Editor
let artistsData = [];
let originalData = [];
let currentEditIndex = null;
let changes = [];

// Load saved changes from localStorage on init
function loadSavedChanges() {
    try {
        const saved = localStorage.getItem('velour_artist_changes');
        if (saved) {
            changes = JSON.parse(saved);
            if (Array.isArray(changes)) {
                console.log(`Loaded ${changes.length} saved changes from localStorage`);
            } else {
                changes = [];
            }
        }
        
        const savedData = localStorage.getItem('velour_artists_data');
        if (savedData) {
            artistsData = JSON.parse(savedData);
            // Validate and clean data
            if (Array.isArray(artistsData)) {
                // Ensure all artists have required fields
                artistsData = artistsData.filter(artist => artist && artist.artist_name);
                artistsData.forEach(artist => {
                    // Ensure issues array exists
                    if (!artist.issues) {
                        artist.issues = detectIssues(artist);
                    }
                    // Ensure numeric fields
                    artist.total_shows = artist.total_shows || 0;
                    artist.connection_count = artist.connection_count || 0;
                });
                originalData = JSON.parse(JSON.stringify(artistsData)); // Deep copy
                console.log(`Loaded ${artistsData.length} artists from localStorage`);
                return true;
            } else {
                console.warn('Invalid artists data in localStorage, will reload from file');
                return false;
            }
        }
    } catch (e) {
        console.error('Error loading saved changes:', e);
        // Clear corrupted data
        localStorage.removeItem('velour_artist_changes');
        localStorage.removeItem('velour_artists_data');
    }
    return false;
}

// Save changes to localStorage
function saveChangesToStorage() {
    try {
        localStorage.setItem('velour_artist_changes', JSON.stringify(changes));
        localStorage.setItem('velour_artists_data', JSON.stringify(artistsData));
        console.log('Changes saved to localStorage');
        updateChangesCount();
        
        // Sync artist name changes to shows data
        syncArtistChangesToShows();
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
}

// Sync artist name changes from editor to shows data
function syncArtistChangesToShows() {
    try {
        // Get shows data from localStorage
        const showsDataStr = localStorage.getItem('velour_shows_data');
        if (!showsDataStr) {
            console.log('No shows data in localStorage to sync');
            return;
        }
        
        const showsData = JSON.parse(showsDataStr);
        let showsUpdated = 0;
        
        // Process all changes to find name changes
        changes.forEach(change => {
            if (change.type === 'edit' && change.original && change.updated) {
                const oldName = change.original.artist_name;
                const oldNormalized = change.original.normalized_name;
                const newName = change.updated.artist_name;
                const newNormalized = change.updated.normalized_name;
                
                // Update all shows that reference this artist
                showsData.forEach(show => {
                    if (show.artists_list && Array.isArray(show.artists_list)) {
                        let updated = false;
                        show.artists_list = show.artists_list.map(artist => {
                            // Match by normalized name for better accuracy
                            if (artist.toLowerCase().trim() === oldNormalized || 
                                artist.toLowerCase().trim() === oldName.toLowerCase().trim()) {
                                updated = true;
                                return newName;
                            }
                            return artist;
                        });
                        
                        if (updated) {
                            showsUpdated++;
                            // Update the string version too
                            show.artists = show.artists_list.join(', ');
                        }
                    } else if (show.artists) {
                        // Handle string-based artists field
                        const artistsStr = show.artists;
                        if (artistsStr.includes(oldName) || artistsStr.toLowerCase().includes(oldNormalized)) {
                            // Replace old name with new name
                            const regex = new RegExp(`\\b${oldName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
                            show.artists = artistsStr.replace(regex, newName);
                            // Rebuild artists_list if it exists
                            if (show.artists_list) {
                                show.artists_list = show.artists.split(', ').map(a => a.trim());
                            }
                            showsUpdated++;
                        }
                    }
                });
            } else if (change.type === 'merge' && change.source && change.target) {
                // When artists are merged, replace source with target in shows
                const sourceName = change.source.artist_name;
                const sourceNormalized = change.source.normalized_name;
                const targetName = change.target.artist_name;
                
                showsData.forEach(show => {
                    if (show.artists_list && Array.isArray(show.artists_list)) {
                        let updated = false;
                        show.artists_list = show.artists_list.map(artist => {
                            if (artist.toLowerCase().trim() === sourceNormalized || 
                                artist.toLowerCase().trim() === sourceName.toLowerCase().trim()) {
                                updated = true;
                                return targetName;
                            }
                            return artist;
                        });
                        
                        // Remove duplicates after merge
                        show.artists_list = [...new Set(show.artists_list)];
                        
                        if (updated) {
                            showsUpdated++;
                            show.artists = show.artists_list.join(', ');
                        }
                    } else if (show.artists) {
                        const artistsStr = show.artists;
                        if (artistsStr.includes(sourceName) || artistsStr.toLowerCase().includes(sourceNormalized)) {
                            const regex = new RegExp(`\\b${sourceName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
                            show.artists = artistsStr.replace(regex, targetName);
                            if (show.artists_list) {
                                show.artists_list = show.artists.split(', ').map(a => a.trim());
                            }
                            showsUpdated++;
                        }
                    }
                });
            }
        });
        
        if (showsUpdated > 0) {
            // Save updated shows data back to localStorage
            localStorage.setItem('velour_shows_data', JSON.stringify(showsData));
            console.log(`✅ Synced artist changes to ${showsUpdated} shows`);
        }
    } catch (e) {
        console.error('Error syncing artist changes to shows:', e);
    }
}

// Initialize
async function init() {
    // Try to load saved data first
    const hasSavedData = loadSavedChanges();
    
    if (!hasSavedData) {
        await loadArtistsData();
    } else {
        // Update stats and render
        updateStats();
        renderTable();
    }
    
    setupEventListeners();
    
    if (!hasSavedData) {
        renderTable();
    }
    
    // Show indicator if there are unsaved changes
    updateSaveIndicator();
    updateChangesCount();
}

// Load artists data
async function loadArtistsData() {
    try {
        // Try to load from local file first, then relative path
        let response = await fetch('artists_data.csv');
        if (!response.ok) {
            response = await fetch('../data/processed/artists_20260102_211457.csv');
        }
        if (!response.ok) {
            throw new Error('Could not load artists data');
        }
        
        const csvText = await response.text();
        artistsData = parseCSV(csvText);
        originalData = JSON.parse(JSON.stringify(artistsData)); // Deep copy
        
        // Sync any new artists from shows data on load
        syncNewArtistsFromShowsOnLoad();
        
        updateStats();
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading artists data. Please make sure the CSV file exists.');
    }
}

// Sync new artists from shows data when editor loads
function syncNewArtistsFromShowsOnLoad() {
    try {
        const showsDataStr = localStorage.getItem('velour_shows_data');
        if (!showsDataStr) return;
        
        const showsData = JSON.parse(showsDataStr);
        const showsArtists = new Map();
        
        // Collect all artists from shows
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
                if (!artist.first_year || year < artist.first_year) artist.first_year = year;
                if (!artist.last_year || year > artist.last_year) artist.last_year = year;
            });
        });
        
        // Add missing artists to dataset
        let added = 0;
        showsArtists.forEach((showArtist, normalized) => {
            const exists = artistsData.find(a => a.normalized_name === normalized);
            if (!exists) {
                artistsData.push({
                    artist_name: showArtist.artist_name,
                    normalized_name: normalized,
                    total_shows: showArtist.total_shows,
                    connection_count: 0,
                    years_active: Array.from(showArtist.years_active).sort(),
                    first_year: showArtist.first_year,
                    last_year: showArtist.last_year,
                    years_span: showArtist.last_year && showArtist.first_year ? 
                        showArtist.last_year - showArtist.first_year : 0
                });
                added++;
            }
        });
        
        if (added > 0) {
            originalData = JSON.parse(JSON.stringify(artistsData));
            saveChangesToStorage();
            console.log(`✅ Loaded ${added} new artists from shows data`);
        }
    } catch (e) {
        console.error('Error syncing artists from shows on load:', e);
    }
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
            // Remove quotes if present
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1);
            }
            obj[header] = value;
        });
        
        // Parse years_active array
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
        
        // Detect issues
        obj.issues = detectIssues(obj);
        
        return obj;
    });
}

// Detect potential issues with artist names
function detectIssues(artist) {
    const issues = [];
    const name = artist.artist_name.toLowerCase();
    
    // Check for "w/" in name
    if (name.includes(' w/ ') || name.includes('w/')) {
        issues.push({ type: 'has-w', label: 'Contains "w/"' });
    }
    
    // Check for common typos or issues
    if (name.includes('  ') || name.trim() !== name) {
        issues.push({ type: 'has-typo', label: 'Extra spaces' });
    }
    
    // Check for special characters that might be issues
    if (/[^\w\s&'-]/.test(artist.artist_name) && !/[a-zA-Z]/.test(artist.artist_name)) {
        issues.push({ type: 'has-special', label: 'Special chars' });
    }
    
    // Check if normalized doesn't match
    const expectedNormalized = artist.artist_name.toLowerCase().trim();
    if (artist.normalized_name !== expectedNormalized) {
        issues.push({ type: 'normalized-mismatch', label: 'Normalized mismatch' });
    }
    
    return issues;
}

// Setup event listeners
function setupEventListeners() {
    // Search
    document.getElementById('searchInput').addEventListener('input', handleSearch);
    document.getElementById('clearSearch').addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        handleSearch();
    });
    
    // Filters
    document.getElementById('minShows').addEventListener('input', renderTable);
    
    // View changes button
    document.getElementById('viewChangesBtn').addEventListener('click', () => {
        renderChangesView();
        document.getElementById('changesModal').classList.add('show');
    });
    
    // Changes modal
    document.getElementById('closeChangesModal').addEventListener('click', closeChangesModal);
    document.getElementById('closeChangesBtn').addEventListener('click', closeChangesModal);
    document.getElementById('clearAllChangesBtn2').addEventListener('click', () => {
        if (confirm('Clear all changes and reload original data? This cannot be undone.')) {
            localStorage.removeItem('velour_artist_changes');
            localStorage.removeItem('velour_artists_data');
            changes = [];
            location.reload();
        }
    });
    
    // Save and export
    document.getElementById('saveBtn').addEventListener('click', saveChanges);
    document.getElementById('exportBtn').addEventListener('click', exportCSV);
    
    // Clear changes button
    document.getElementById('clearChangesBtn').addEventListener('click', () => {
        if (confirm('Clear all changes and reload original data? This cannot be undone.')) {
            localStorage.removeItem('velour_artist_changes');
            localStorage.removeItem('velour_artists_data');
            changes = [];
            location.reload();
        }
    });
    
    // Modal
    document.getElementById('closeModal').addEventListener('click', closeEditModal);
    document.getElementById('cancelEdit').addEventListener('click', closeEditModal);
    document.getElementById('saveEdit').addEventListener('click', saveEdit);
    document.getElementById('deleteArtist').addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        console.log('Delete button clicked');
        showDeleteConfirmation();
    });
    
    // Delete confirmation modal
    document.getElementById('cancelDelete').addEventListener('click', (e) => {
        e.stopPropagation();
        hideDeleteConfirmation();
    });
    document.getElementById('confirmDelete').addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        console.log('Confirm delete button clicked, currentEditIndex:', currentEditIndex);
        performDelete();
    });
    
    // Split modal
    document.getElementById('closeSplitModal').addEventListener('click', (e) => {
        e.stopPropagation();
        closeSplitModal();
    });
    document.getElementById('cancelSplit').addEventListener('click', (e) => {
        e.stopPropagation();
        closeSplitModal();
    });
    document.getElementById('confirmSplit').addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        confirmSplit();
    });
    document.getElementById('addSplitArtist').addEventListener('click', (e) => {
        e.stopPropagation();
        addSplitArtistInput();
    });
    document.getElementById('splitArtist').addEventListener('click', (e) => {
        e.stopPropagation();
        openSplitModal();
    });
    
    // Merge modal
    document.getElementById('closeMergeModal').addEventListener('click', closeMergeModal);
    document.getElementById('cancelMerge').addEventListener('click', closeMergeModal);
    document.getElementById('confirmMerge').addEventListener('click', confirmMerge);
    
    // Merge search
    document.getElementById('mergeArtist').addEventListener('input', handleMergeSearch);
    
    // Close modals on outside click (but not on drag/select or clicks inside modal)
    let mouseDownOnModal = false;
    let mouseDownTarget = null;
    
    window.addEventListener('mousedown', (e) => {
        const editModal = document.getElementById('editModal');
        const mergeModal = document.getElementById('mergeModal');
        const splitModal = document.getElementById('splitModal');
        const confirmDeleteModal = document.getElementById('confirmDeleteModal');
        const changesModal = document.getElementById('changesModal');
        // Track if mousedown was on the modal background (not content)
        // Check if click is on modal itself, not on any child elements
        if (e.target === editModal || e.target === mergeModal || e.target === splitModal || e.target === confirmDeleteModal || e.target === changesModal) {
            mouseDownOnModal = true;
            mouseDownTarget = e.target;
        } else {
            mouseDownOnModal = false;
            mouseDownTarget = null;
        }
    });
    
    window.addEventListener('click', (e) => {
        const editModal = document.getElementById('editModal');
        const mergeModal = document.getElementById('mergeModal');
        
        // Don't close if clicking inside modal content (any child of modal)
        if (editModal && editModal.contains(e.target) && e.target !== editModal) {
            // Click was inside modal content, don't close
            mouseDownOnModal = false;
            mouseDownTarget = null;
            return;
        }
        if (mergeModal && mergeModal.contains(e.target) && e.target !== mergeModal) {
            // Click was inside modal content, don't close
            mouseDownOnModal = false;
            mouseDownTarget = null;
            return;
        }
        
        // Only close if the click target is the modal background AND mousedown was also on it
        // This prevents closing when selecting text and releasing outside
        if (e.target === editModal && mouseDownTarget === editModal) {
            closeEditModal();
        }
        if (e.target === mergeModal && mouseDownTarget === mergeModal) {
            closeMergeModal();
        }
        
        const splitModal = document.getElementById('splitModal');
        if (splitModal && splitModal.contains(e.target) && e.target !== splitModal) {
            mouseDownOnModal = false;
            mouseDownTarget = null;
            return;
        }
        if (e.target === splitModal && mouseDownTarget === splitModal) {
            closeSplitModal();
        }
        // Reset tracking
        mouseDownOnModal = false;
        mouseDownTarget = null;
    });
}

// Handle search
function handleSearch() {
    renderTable();
}

// Render table
function renderTable() {
    const tbody = document.getElementById('artistsTableBody');
    if (!tbody) {
        console.error('Table body not found');
        return;
    }
    
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const minShows = parseInt(document.getElementById('minShows').value) || 1;
    
    console.log('renderTable called. artistsData length:', artistsData.length);
    
    let filtered = artistsData.filter(artist => {
        // Safety check
        if (!artist) return false;
        
        // Search filter
        if (searchTerm) {
            const artistName = (artist.artist_name || '').toLowerCase();
            const normalizedName = (artist.normalized_name || '').toLowerCase();
            const matches = artistName.includes(searchTerm) || normalizedName.includes(searchTerm);
            if (!matches) return false;
        }
        
        // Min shows filter
        const totalShows = artist.total_shows || 0;
        if (totalShows < minShows) return false;
        
        return true;
    });
    
    console.log('Filtered artists count:', filtered.length);
    
    // Sort by issues first, then by show count
    filtered.sort((a, b) => {
        const aIssues = (a && a.issues) ? a.issues.length : 0;
        const bIssues = (b && b.issues) ? b.issues.length : 0;
        if (aIssues !== bIssues) {
            return bIssues - aIssues;
        }
        const aShows = (a && a.total_shows) ? a.total_shows : 0;
        const bShows = (b && b.total_shows) ? b.total_shows : 0;
        return bShows - aShows;
    });
    
    tbody.innerHTML = filtered.map((artist, index) => {
        if (!artist) return '';
        
        const issues = artist.issues || [];
        const issuesHTML = issues.map(issue => 
            `<span class="issue-badge ${issue.type}">${issue.label}</span>`
        ).join(' ');
        
        const artistIndex = artistsData.indexOf(artist);
        if (artistIndex === -1) return '';
        
        return `
            <tr class="${issues.length > 0 ? 'issue-row' : ''}" data-index="${artistIndex}">
                <td>
                    <span class="artist-name" onclick="openEditModal(${artistIndex})">
                        ${escapeHtml(artist.artist_name || '')}
                    </span>
                </td>
                <td><span class="normalized-name">${escapeHtml(artist.normalized_name || '')}</span></td>
                <td>${artist.total_shows || 0}</td>
                <td>${artist.connection_count || 0}</td>
                <td>${artist.first_year || '-'}</td>
                <td>${artist.last_year || '-'}</td>
                <td>${issuesHTML || '<span style="color: #28a745;">✓</span>'}</td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn" onclick="viewArtist('${escapeHtml(artist.normalized_name)}')">View</button>
                        <button class="action-btn" onclick="openEditModal(${artistIndex})">Edit</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    document.getElementById('filteredArtists').textContent = filtered.length;
}

// Open edit modal
function openEditModal(index) {
    currentEditIndex = index;
    const artist = artistsData[index];
    
    document.getElementById('editArtistName').value = artist.artist_name;
    document.getElementById('editNormalized').value = artist.normalized_name;
    document.getElementById('editNotes').value = artist.notes || '';
    document.getElementById('mergeArtist').value = '';
    document.getElementById('mergeSuggestions').innerHTML = '';
    document.getElementById('mergeSuggestions').classList.remove('show');
    
    document.getElementById('editModal').classList.add('show');
}

// Close edit modal
function closeEditModal() {
    console.log('closeEditModal called');
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.classList.remove('show');
        console.log('Modal class removed, has show class:', modal.classList.contains('show'));
    }
    currentEditIndex = null;
    console.log('Modal closed, currentEditIndex reset');
}

// Save edit
function saveEdit() {
    if (currentEditIndex === null) return;
    
    const artist = artistsData[currentEditIndex];
    const newName = document.getElementById('editArtistName').value.trim();
    const newNormalized = document.getElementById('editNormalized').value.trim().toLowerCase();
    
    if (!newName) {
        alert('Artist name cannot be empty');
        return;
    }
    
    // Track change
    const original = originalData[currentEditIndex];
    if (newName !== original.artist_name || newNormalized !== original.normalized_name) {
        changes.push({
            type: 'edit',
            original: { ...original },
            updated: {
                artist_name: newName,
                normalized_name: newNormalized
            },
            index: currentEditIndex
        });
        
        artist.artist_name = newName;
        artist.normalized_name = newNormalized;
        artist.issues = detectIssues(artist);
    }
    
    // Save to localStorage
    saveChangesToStorage();
    updateSaveIndicator();
    
    closeEditModal();
    renderTable();
    updateStats();
}

// Delete artist
// Show delete confirmation modal
function showDeleteConfirmation() {
    console.log('showDeleteConfirmation called, currentEditIndex:', currentEditIndex);
    
    if (currentEditIndex === null) {
        console.error('Cannot delete: currentEditIndex is null');
        alert('Error: No artist selected for deletion.');
        return;
    }
    
    if (currentEditIndex < 0 || currentEditIndex >= artistsData.length) {
        console.error('Cannot delete: invalid index', currentEditIndex, 'artistsData.length:', artistsData.length);
        alert(`Error: Invalid artist index (${currentEditIndex}). Please try again.`);
        return;
    }
    
    const artist = artistsData[currentEditIndex];
    if (!artist) {
        console.error('Cannot delete: artist not found at index', currentEditIndex);
        alert('Error: Artist not found at that index.');
        return;
    }
    
    console.log('Showing delete confirmation for:', artist.artist_name, 'at index', currentEditIndex);
    
    // Show artist name in confirmation
    document.getElementById('deleteArtistName').textContent = artist.artist_name;
    
    // Hide edit modal and show delete confirmation
    document.getElementById('editModal').classList.remove('show');
    document.getElementById('confirmDeleteModal').classList.add('show');
}

// Hide delete confirmation modal
function hideDeleteConfirmation() {
    document.getElementById('confirmDeleteModal').classList.remove('show');
    // Reopen edit modal
    if (currentEditIndex !== null) {
        document.getElementById('editModal').classList.add('show');
    }
}

// Make performDelete available globally for debugging
window.performDelete = performDelete;

// Perform the actual deletion
function performDelete() {
    console.log('performDelete called', { currentEditIndex, artistsDataLength: artistsData.length });
    
    if (currentEditIndex === null) {
        console.error('Cannot delete: currentEditIndex is null');
        hideDeleteConfirmation();
        return;
    }
    
    if (currentEditIndex < 0 || currentEditIndex >= artistsData.length) {
        console.error('Cannot delete: invalid index', currentEditIndex, 'artistsData.length:', artistsData.length);
        hideDeleteConfirmation();
        return;
    }
    
    const artist = artistsData[currentEditIndex];
    if (!artist) {
        console.error('Cannot delete: artist not found at index', currentEditIndex);
        hideDeleteConfirmation();
        return;
    }
    
    const artistName = artist.artist_name;
    const indexToDelete = currentEditIndex; // SAVE THE INDEX BEFORE CLOSING MODALS
    console.log('Deleting artist:', artistName, 'at index', indexToDelete);
    
    // Close both modals (but don't reset currentEditIndex yet - we'll do that after deletion)
    hideDeleteConfirmation();
    document.getElementById('editModal').classList.remove('show'); // Just hide, don't call closeEditModal()
    
    // Now do the deletion with the saved index
    const artistToDelete = artistsData[indexToDelete];
        
    if (!artistToDelete) {
        console.error('Artist not found at index', indexToDelete);
        currentEditIndex = null; // Reset only on error
        return;
    }
    
    console.log('About to delete:', artistToDelete.artist_name, 'at index', indexToDelete);
    console.log('artistsData length before:', artistsData.length);
    
    // Track change
    changes.push({
        type: 'delete',
        artist: { ...artistToDelete },
        index: indexToDelete
    });
    
    // Remove from array
    const deletedCount = artistsData.splice(indexToDelete, 1).length;
    currentEditIndex = null; // Reset after deletion
    
    console.log('Artist deleted. Removed', deletedCount, 'item(s). Remaining artists:', artistsData.length);
    console.log('Verifying deletion - artist still in array?', artistsData.some(a => a && a.artist_name === artistName));
    console.log('First 5 artist names:', artistsData.slice(0, 5).map(a => a?.artist_name));
    
    // Save to localStorage IMMEDIATELY
    saveChangesToStorage();
    console.log('Saved to localStorage. Verifying save...');
    
    // Verify localStorage was updated
    const savedData = JSON.parse(localStorage.getItem('velour_artists_data') || '[]');
    console.log('localStorage now has', savedData.length, 'artists');
    console.log('Deleted artist in localStorage?', savedData.some(a => a && a.artist_name === artistName));
    
    updateSaveIndicator();
    updateChangesCount();
    
    // Force immediate UI update
    renderTable();
    updateStats();
    
    // Force a re-render after a tiny delay to ensure DOM updates
    setTimeout(() => {
        console.log('Force re-render after deletion');
        renderTable();
    }, 10);
    
    // Show success message (using a custom notification would be better, but alert works)
    alert(`Artist "${artistName}" has been deleted. Remember to save your changes!`);
}

// Handle merge search
function handleMergeSearch(e) {
    const searchTerm = e.target.value.toLowerCase().trim();
    const suggestions = document.getElementById('mergeSuggestions');
    
    if (searchTerm.length < 2) {
        suggestions.classList.remove('show');
        return;
    }
    
    const matches = artistsData
        .filter(a => a.normalized_name.includes(searchTerm) && 
                     artistsData.indexOf(a) !== currentEditIndex)
        .slice(0, 10);
    
    if (matches.length === 0) {
        suggestions.innerHTML = '<div class="suggestion-item">No matches found</div>';
    } else {
        suggestions.innerHTML = matches.map(artist => 
            `<div class="suggestion-item" onclick="selectMergeTarget(${artistsData.indexOf(artist)})">
                ${escapeHtml(artist.artist_name)} (${artist.total_shows} shows)
            </div>`
        ).join('');
    }
    
    suggestions.classList.add('show');
}

// Select merge target
function selectMergeTarget(targetIndex) {
    if (currentEditIndex === null) return;
    
    const source = artistsData[currentEditIndex];
    const target = artistsData[targetIndex];
    
    document.getElementById('mergeSource').textContent = source.artist_name;
    document.getElementById('mergeTarget').textContent = target.artist_name;
    document.getElementById('mergeSourceShows').textContent = source.total_shows;
    document.getElementById('mergeSourceConnections').textContent = source.connection_count;
    document.getElementById('mergeTargetShows').textContent = target.total_shows;
    document.getElementById('mergeTargetConnections').textContent = target.connection_count;
    
    document.getElementById('editModal').classList.remove('show');
    document.getElementById('mergeModal').classList.add('show');
    
    window.mergeSourceIndex = currentEditIndex;
    window.mergeTargetIndex = targetIndex;
}

// Confirm merge
function confirmMerge() {
    const sourceIndex = window.mergeSourceIndex;
    const targetIndex = window.mergeTargetIndex;
    
    if (sourceIndex === undefined || targetIndex === undefined) return;
    
    const source = artistsData[sourceIndex];
    const target = artistsData[targetIndex];
    
    // Merge: combine shows and connections
    target.total_shows += source.total_shows;
    target.connection_count = Math.max(target.connection_count, source.connection_count);
    
    // Update years
    if (source.first_year && (!target.first_year || source.first_year < target.first_year)) {
        target.first_year = source.first_year;
    }
    if (source.last_year && (!target.last_year || source.last_year > target.last_year)) {
        target.last_year = source.last_year;
    }
    
    // Merge years_active arrays
    if (source.years_active && Array.isArray(source.years_active)) {
        const combinedYears = new Set([...(target.years_active || []), ...source.years_active]);
        target.years_active = Array.from(combinedYears).sort();
        target.years_span = target.years_active.length;
    }
    
    changes.push({
        type: 'merge',
        source: { ...source },
        target: { ...target },
        sourceIndex: sourceIndex,
        targetIndex: targetIndex
    });
    
    // Remove source artist
    artistsData.splice(sourceIndex, 1);
    
    // Immediately sync merge to shows
    syncArtistMergeToShows(source.artist_name, source.normalized_name, target.artist_name);
    
    // Save to localStorage
    saveChangesToStorage();
    updateSaveIndicator();
    
    closeMergeModal();
    renderTable();
    updateStats();
}

// Sync artist merge to shows (called immediately on merge)
function syncArtistMergeToShows(sourceName, sourceNormalized, targetName) {
    try {
        const showsDataStr = localStorage.getItem('velour_shows_data');
        if (!showsDataStr) return;
        
        const showsData = JSON.parse(showsDataStr);
        let showsUpdated = 0;
        
        showsData.forEach(show => {
            if (show.artists_list && Array.isArray(show.artists_list)) {
                let updated = false;
                show.artists_list = show.artists_list.map(artist => {
                    if (artist.toLowerCase().trim() === sourceNormalized || 
                        artist.toLowerCase().trim() === sourceName.toLowerCase().trim()) {
                        updated = true;
                        return targetName;
                    }
                    return artist;
                });
                
                // Remove duplicates after merge
                show.artists_list = [...new Set(show.artists_list)];
                
                if (updated) {
                    showsUpdated++;
                    show.artists = show.artists_list.join(', ');
                }
            } else if (show.artists) {
                const artistsStr = show.artists;
                if (artistsStr.includes(sourceName) || artistsStr.toLowerCase().includes(sourceNormalized)) {
                    const regex = new RegExp(`\\b${sourceName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
                    show.artists = artistsStr.replace(regex, targetName);
                    if (show.artists_list) {
                        show.artists_list = show.artists.split(', ').map(a => a.trim());
                    }
                    showsUpdated++;
                }
            }
        });
        
        if (showsUpdated > 0) {
            localStorage.setItem('velour_shows_data', JSON.stringify(showsData));
            console.log(`✅ Synced artist merge "${sourceName}" → "${targetName}" to ${showsUpdated} shows`);
        }
    } catch (e) {
        console.error('Error syncing artist merge:', e);
    }
}

// Close merge modal
function closeMergeModal() {
    document.getElementById('mergeModal').classList.remove('show');
    window.mergeSourceIndex = undefined;
    window.mergeTargetIndex = undefined;
}

// Save changes
async function saveChanges() {
    if (changes.length === 0) {
        alert('No changes to save');
        return;
    }
    
    // Convert to CSV
    const csv = convertToCSV(artistsData);
    
    // Create download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `artists_edited_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    // Also save changes log
    const changesLog = JSON.stringify(changes, null, 2);
    const changesBlob = new Blob([changesLog], { type: 'application/json' });
    const changesUrl = window.URL.createObjectURL(changesBlob);
    const changesA = document.createElement('a');
    changesA.href = changesUrl;
    changesA.download = `artist_changes_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(changesA);
    changesA.click();
    document.body.removeChild(changesA);
    window.URL.revokeObjectURL(changesUrl);
    
    // Sync to shows before final save
    syncArtistChangesToShows();
    
    alert(`Saved ${changes.length} changes!\n\nFiles downloaded:\n- Edited CSV\n- Changes log JSON\n\n✅ Artist name changes have been synced to shows data.\n\nYou can now use these files to update the network data.`);
    
    // Clear changes after saving
    changes = [];
    saveChangesToStorage();
    updateSaveIndicator();
}

// Export CSV
function exportCSV() {
    const csv = convertToCSV(artistsData);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `artists_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Convert to CSV
function convertToCSV(data) {
    const headers = ['artist_name', 'normalized_name', 'total_shows', 'connection_count', 
                     'years_active', 'first_year', 'last_year', 'years_span'];
    
    const rows = data.map(artist => {
        const yearsActive = artist.years_active ? JSON.stringify(artist.years_active) : '[]';
        // Properly quote all fields that might contain commas or special characters
        return [
            `"${(artist.artist_name || '').replace(/"/g, '""')}"`,
            `"${(artist.normalized_name || '').replace(/"/g, '""')}"`,
            artist.total_shows || 0,
            artist.connection_count || 0,
            `"${yearsActive.replace(/"/g, '""')}"`,  // Quote the JSON array
            artist.first_year || '',
            artist.last_year || '',
            artist.years_span || 0
        ].join(',');
    });
    
    return [headers.join(','), ...rows].join('\n');
}

// Update stats
function updateStats() {
    document.getElementById('totalArtists').textContent = artistsData.length;
}

// Update save indicator
function updateSaveIndicator() {
    const saveBtn = document.getElementById('saveBtn');
    if (changes.length > 0) {
        saveBtn.textContent = `Save Changes (${changes.length})`;
        saveBtn.style.background = '#dc3545'; // Red to indicate unsaved
    } else {
        saveBtn.textContent = 'Save Changes';
        saveBtn.style.background = '#667eea'; // Back to normal
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Split artist functionality
let splitArtists = [];
let splitSourceArtist = null;

function openSplitModal() {
    if (currentEditIndex === null) return;
    
    splitSourceArtist = artistsData[currentEditIndex];
    splitArtists = []; // Reset split artists
    
    document.getElementById('splitSourceName').textContent = splitSourceArtist.artist_name;
    
    // Add initial split artist input
    addSplitArtistInput();
    
    document.getElementById('editModal').classList.remove('show');
    document.getElementById('splitModal').classList.add('show');
}

function addSplitArtistInput() {
    const container = document.getElementById('splitArtistsList');
    const index = splitArtists.length;
    
    const div = document.createElement('div');
    div.className = 'split-artist-input';
    div.innerHTML = `
        <input type="text" class="form-input split-artist-name" 
               placeholder="New artist name" 
               data-index="${index}">
        <input type="text" class="form-input split-artist-normalized" 
               placeholder="Normalized name (auto-generated)" 
               data-index="${index}"
               readonly>
        <button class="btn btn-danger btn-small" onclick="removeSplitArtist(${index})">Remove</button>
    `;
    
    container.appendChild(div);
    
    // Add to splitArtists array
    splitArtists.push({
        name: '',
        normalized: ''
    });
    
    // Add event listener for name input
    const nameInput = div.querySelector('.split-artist-name');
    nameInput.addEventListener('input', (e) => {
        const idx = parseInt(e.target.dataset.index);
        splitArtists[idx].name = e.target.value.trim();
        splitArtists[idx].normalized = normalizeNameForSplit(splitArtists[idx].name);
        
        // Update normalized field
        const normalizedInput = div.querySelector('.split-artist-normalized');
        normalizedInput.value = splitArtists[idx].normalized;
        
        updateSplitPreview();
    });
}

function removeSplitArtist(index) {
    splitArtists.splice(index, 1);
    renderSplitArtists();
    updateSplitPreview();
}

function renderSplitArtists() {
    const container = document.getElementById('splitArtistsList');
    container.innerHTML = '';
    
    splitArtists.forEach((artist, index) => {
        const div = document.createElement('div');
        div.className = 'split-artist-input';
        div.innerHTML = `
            <input type="text" class="form-input split-artist-name" 
                   placeholder="New artist name" 
                   data-index="${index}"
                   value="${escapeHtml(artist.name)}">
            <input type="text" class="form-input split-artist-normalized" 
                   placeholder="Normalized name (auto-generated)" 
                   data-index="${index}"
                   value="${escapeHtml(artist.normalized)}"
                   readonly>
            <button class="btn btn-danger btn-small" onclick="removeSplitArtist(${index})">Remove</button>
        `;
        
        container.appendChild(div);
        
        // Re-add event listener
        const nameInput = div.querySelector('.split-artist-name');
        nameInput.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.index);
            splitArtists[idx].name = e.target.value.trim();
            splitArtists[idx].normalized = normalizeNameForSplit(splitArtists[idx].name);
            
            const normalizedInput = div.querySelector('.split-artist-normalized');
            normalizedInput.value = splitArtists[idx].normalized;
            
            updateSplitPreview();
        });
    });
}

function normalizeNameForSplit(name) {
    if (!name) return '';
    return name.toLowerCase().trim().replace(/[^\w\s-]/g, '');
}

function updateSplitPreview() {
    const preview = document.getElementById('splitPreview');
    
    if (splitArtists.length === 0 || splitArtists.every(a => !a.name)) {
        preview.innerHTML = '<p style="color: #666;">Add at least one new artist name to see preview.</p>';
        return;
    }
    
    const validArtists = splitArtists.filter(a => a.name);
    
    let html = '<div class="split-preview-list">';
    html += `<div class="preview-item original"><strong>Original:</strong> ${escapeHtml(splitSourceArtist.artist_name)} (${splitSourceArtist.total_shows} shows)</div>`;
    
    validArtists.forEach(artist => {
        // Check if this normalized name already exists
        const exists = artistsData.find(a => a.normalized_name === artist.normalized);
        const existsWarning = exists ? ' <span style="color: #dc3545;">(⚠ Already exists!)</span>' : '';
        
        html += `<div class="preview-item new"><strong>New:</strong> ${escapeHtml(artist.name)}${existsWarning}</div>`;
    });
    
    html += '</div>';
    html += '<p class="help-text">Note: You will need to manually distribute shows between artists after splitting.</p>';
    
    preview.innerHTML = html;
}

function closeSplitModal() {
    document.getElementById('splitModal').classList.remove('show');
    splitArtists = [];
    splitSourceArtist = null;
}

function confirmSplit() {
    console.log('confirmSplit called', { splitSourceArtist, splitArtists });
    
    if (!splitSourceArtist) {
        console.error('No source artist to split');
        alert('Error: No artist selected for splitting.');
        return;
    }
    
    if (splitArtists.length === 0) {
        alert('Please add at least one new artist to split into.');
        return;
    }
    
    const validArtists = splitArtists.filter(a => a.name && a.normalized);
    if (validArtists.length === 0) {
        alert('Please enter valid artist names.');
        return;
    }
    
    // Check for duplicates
    const duplicates = validArtists.filter(a => {
        return artistsData.some(existing => existing.normalized_name === a.normalized);
    });
    
    if (duplicates.length > 0) {
        const names = duplicates.map(a => a.name).join(', ');
        if (!confirm(`Warning: These artists already exist: ${names}\n\nContinue anyway?`)) {
            return;
        }
    }
    
    if (!confirm(`Split "${splitSourceArtist.artist_name}" into ${validArtists.length} separate artist${validArtists.length > 1 ? 's' : ''}?\n\nThis will create new artist entries. You'll need to manually distribute shows.`)) {
        return;
    }
    
    // Create new artists
    const sourceIndex = artistsData.indexOf(splitSourceArtist);
    
    let createdCount = 0;
    validArtists.forEach(newArtist => {
        // Check if artist already exists
        const existing = artistsData.find(a => a.normalized_name === newArtist.normalized);
        
        if (!existing) {
            // Create new artist entry - copy show data from source artist
            const newEntry = {
                artist_name: newArtist.name,
                normalized_name: newArtist.normalized,
                total_shows: splitSourceArtist.total_shows || 0, // Copy show count from source
                connection_count: 0, // Will be recalculated when network is regenerated
                first_year: splitSourceArtist.first_year,
                last_year: splitSourceArtist.last_year,
                years_span: splitSourceArtist.years_span || 0,
                years_active: splitSourceArtist.years_active ? [...splitSourceArtist.years_active] : [], // Copy years_active array
                issues: detectIssues({
                    artist_name: newArtist.name,
                    normalized_name: newArtist.normalized
                })
            };
            
            artistsData.push(newEntry);
            createdCount++;
            
            // Track change
            changes.push({
                type: 'split',
                source: { ...splitSourceArtist },
                new_artist: { ...newEntry },
                sourceIndex: sourceIndex
            });
        } else {
            // If artist already exists, merge the show data
            existing.total_shows = (existing.total_shows || 0) + (splitSourceArtist.total_shows || 0);
            // Update years_active to include source artist's years
            if (splitSourceArtist.years_active && Array.isArray(splitSourceArtist.years_active)) {
                const combinedYears = [...new Set([...(existing.years_active || []), ...splitSourceArtist.years_active])].sort();
                existing.years_active = combinedYears;
                if (combinedYears.length > 0) {
                    existing.first_year = Math.min(existing.first_year || 9999, splitSourceArtist.first_year || 9999);
                    existing.last_year = Math.max(existing.last_year || 0, splitSourceArtist.last_year || 0);
                    existing.years_span = existing.last_year - existing.first_year;
                }
            }
            
            // Track change for existing artist update
            changes.push({
                type: 'split_merge',
                source: { ...splitSourceArtist },
                existing_artist: { ...existing },
                sourceIndex: sourceIndex
            });
        }
    });
    
    console.log(`Created ${createdCount} new artists`);
    
    // Save to localStorage
    saveChangesToStorage();
    updateSaveIndicator();
    
    closeSplitModal();
    renderTable();
    updateStats();
    
    const totalCreated = createdCount + (validArtists.length - createdCount);
    alert(`Split complete! Created ${createdCount} new artist${createdCount > 1 ? 's' : ''}.\n\nAll new artists have been automatically associated with the source artist's shows (${splitSourceArtist.total_shows || 0} shows).\n\nNote: You may want to manually adjust show counts if the shows should be distributed differently. The network connections will be updated when you save and regenerate the network data.`);
}

// Render changes view
function renderChangesView() {
    const changesList = document.getElementById('changesList');
    const changesSummary = document.getElementById('changesSummary');
    
    if (changes.length === 0) {
        changesList.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No pending changes.</p>';
        changesSummary.innerHTML = '<p><strong>No pending changes.</strong></p>';
        return;
    }
    
    // Count by type
    const counts = {
        edit: 0,
        merge: 0,
        split: 0,
        delete: 0
    };
    
    changes.forEach(change => {
        if (counts.hasOwnProperty(change.type)) {
            counts[change.type]++;
        }
    });
    
    // Summary
    const summaryParts = [];
    if (counts.edit > 0) summaryParts.push(`${counts.edit} edit${counts.edit > 1 ? 's' : ''}`);
    if (counts.merge > 0) summaryParts.push(`${counts.merge} merge${counts.merge > 1 ? 's' : ''}`);
    if (counts.split > 0) summaryParts.push(`${counts.split} split${counts.split > 1 ? 's' : ''}`);
    if (counts.delete > 0) summaryParts.push(`${counts.delete} deletion${counts.delete > 1 ? 's' : ''}`);
    
    changesSummary.innerHTML = `
        <div class="changes-summary-content">
            <p><strong>Total Changes: ${changes.length}</strong></p>
            <p>${summaryParts.join(', ')}</p>
        </div>
    `;
    
    // Render each change
    changesList.innerHTML = changes.map((change, index) => {
        let html = '<div class="change-item">';
        
        switch (change.type) {
            case 'edit':
                html += `
                    <div class="change-header">
                        <span class="change-type-badge edit">Edit</span>
                        <strong>${escapeHtml(change.original.artist_name)}</strong>
                    </div>
                    <div class="change-details">
                        <div class="change-field">
                            <span class="change-label">Name:</span>
                            <span class="change-old">${escapeHtml(change.original.artist_name)}</span>
                            <span class="change-arrow">→</span>
                            <span class="change-new">${escapeHtml(change.updated.artist_name)}</span>
                        </div>
                        ${change.original.normalized_name !== change.updated.normalized_name ? `
                        <div class="change-field">
                            <span class="change-label">Normalized:</span>
                            <span class="change-old">${escapeHtml(change.original.normalized_name)}</span>
                            <span class="change-arrow">→</span>
                            <span class="change-new">${escapeHtml(change.updated.normalized_name)}</span>
                        </div>
                        ` : ''}
                    </div>
                `;
                break;
                
            case 'merge':
                html += `
                    <div class="change-header">
                        <span class="change-type-badge merge">Merge</span>
                        <strong>${escapeHtml(change.source.artist_name)}</strong> → <strong>${escapeHtml(change.target.artist_name)}</strong>
                    </div>
                    <div class="change-details">
                        <p>Merging <strong>${escapeHtml(change.source.artist_name)}</strong> into <strong>${escapeHtml(change.target.artist_name)}</strong></p>
                        <p class="change-info">Source: ${change.source.total_shows || 0} shows, ${change.source.connection_count || 0} connections</p>
                        <p class="change-info">Target: ${change.target.total_shows || 0} shows, ${change.target.connection_count || 0} connections</p>
                    </div>
                `;
                break;
                
            case 'split':
                html += `
                    <div class="change-header">
                        <span class="change-type-badge split">Split</span>
                        <strong>${escapeHtml(change.source.artist_name)}</strong>
                    </div>
                    <div class="change-details">
                        <p>Splitting <strong>${escapeHtml(change.source.artist_name)}</strong> into:</p>
                        <p class="change-new">• ${escapeHtml(change.new_artist.artist_name)}</p>
                    </div>
                `;
                break;
                
            case 'delete':
                html += `
                    <div class="change-header">
                        <span class="change-type-badge delete">Delete</span>
                        <strong>${escapeHtml(change.artist.artist_name)}</strong>
                    </div>
                    <div class="change-details">
                        <p>Will delete <strong>${escapeHtml(change.artist.artist_name)}</strong></p>
                        <p class="change-info">${change.artist.total_shows || 0} shows, ${change.artist.connection_count || 0} connections</p>
                    </div>
                `;
                break;
        }
        
        html += '</div>';
        return html;
    }).join('');
}

function closeChangesModal() {
    document.getElementById('changesModal').classList.remove('show');
}

// Update changes count in button
function updateChangesCount() {
    const count = changes.length;
    document.getElementById('changesCount').textContent = count;
    const btn = document.getElementById('viewChangesBtn');
    if (count > 0) {
        btn.classList.add('has-changes');
    } else {
        btn.classList.remove('has-changes');
    }
}

// View artist in detail page
function viewArtist(normalizedName) {
    // Store the artist name in sessionStorage so artist.html can find it
    sessionStorage.setItem('viewArtist', normalizedName);
    window.location.href = 'artist.html';
}

// Make functions available globally
window.openEditModal = openEditModal;
window.selectMergeTarget = selectMergeTarget;
window.removeSplitArtist = removeSplitArtist;
window.viewArtist = viewArtist;

// Check if we should jump to an artist from detail page
window.addEventListener('load', () => {
    const editArtist = sessionStorage.getItem('editArtist');
    if (editArtist) {
        sessionStorage.removeItem('editArtist');
        // Find and scroll to artist
        const artist = artistsData.find(a => a.normalized_name === editArtist);
        if (artist) {
            document.getElementById('searchInput').value = artist.artist_name;
            handleSearch();
            // Scroll to the artist row
            setTimeout(() => {
                const row = document.querySelector(`tr[data-index="${artistsData.indexOf(artist)}"]`);
                if (row) {
                    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    row.style.background = '#fff3cd';
                    setTimeout(() => {
                        row.style.background = '';
                    }, 2000);
                }
            }, 100);
        }
    }
});

// Initialize on load
init();

