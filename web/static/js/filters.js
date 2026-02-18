// ========================================================================
// GLOBAL FILTER MANAGEMENT SYSTEM
// ========================================================================
//
// This system manages two types of filters:
//
// 1. GLOBAL FILTERS (persisted in localStorage across pages):
//    - stores: Selected game stores (Steam, Epic, GOG, etc.)
//    - genres: Selected game genres
//    - queries: Smart filters (unplayed, highly-rated, etc.)
//    - excludeStreaming: Exclude Xbox Cloud/streaming games
//    - noIgdb: Show only games without IGDB metadata
//    - protondbTier: ProtonDB compatibility tier filter
//
// 2. CONTEXTUAL FILTERS (URL-only, page-specific):
//    - collection: Collection ID (specific to collection detail page)
//    - search: Search query (temporary search context)
//    - sort/order: Sorting preferences (could be global in future)
//
// PERSISTENCE STRATEGY:
// - buildUrl(): Saves global filters to localStorage when user changes a filter
// - saveCurrentFilters(): Syncs localStorage with URL on page load
// - applyGlobalFiltersOnLoad(): Restores missing global filters from localStorage to URL
// - interceptNavigationLinks(): Adds global filters when navigating between pages
//
// ========================================================================

function saveCurrentFilters() {
    const currentUrl = new URL(window.location.href);
    const filters = {
        stores: currentUrl.searchParams.getAll('stores'),
        genres: currentUrl.searchParams.getAll('genres'),
        queries: currentUrl.searchParams.getAll('queries'),
        excludeStreaming: currentUrl.searchParams.get('exclude_streaming') === 'true',
        noIgdb: currentUrl.searchParams.get('no_igdb') === 'true',
        protondbTier: currentUrl.searchParams.get('protondb_tier') || ''
    };
    localStorage.setItem('globalFilters', JSON.stringify(filters));
}

function getGlobalFilters() {
    const stored = localStorage.getItem('globalFilters');
    return stored ? JSON.parse(stored) : { 
        stores: [], 
        genres: [], 
        queries: [],
        excludeStreaming: false,
        noIgdb: false,
        protondbTier: ''
    };
}

// Apply global filters on page load if no filters in URL
function applyGlobalFiltersOnLoad() {
    const currentUrl = new URL(window.location.href);
    const filters = getGlobalFilters();
    
    let needsRedirect = false;
    
    // Add stores from localStorage if not in URL
    if (!currentUrl.searchParams.has('stores') && filters.stores.length > 0) {
        filters.stores.forEach(store => currentUrl.searchParams.append('stores', store));
        needsRedirect = true;
    }
    
    // Add genres from localStorage if not in URL
    if (!currentUrl.searchParams.has('genres') && filters.genres.length > 0) {
        filters.genres.forEach(genre => currentUrl.searchParams.append('genres', genre));
        needsRedirect = true;
    }
    
    // Add queries from localStorage if not in URL
    if (!currentUrl.searchParams.has('queries') && filters.queries.length > 0) {
        filters.queries.forEach(query => currentUrl.searchParams.append('queries', query));
        needsRedirect = true;
    }
    
    // Add exclude_streaming from localStorage if not in URL
    if (!currentUrl.searchParams.has('exclude_streaming') && filters.excludeStreaming) {
        currentUrl.searchParams.set('exclude_streaming', 'true');
        needsRedirect = true;
    }
    
    // Add no_igdb from localStorage if not in URL
    if (!currentUrl.searchParams.has('no_igdb') && filters.noIgdb) {
        currentUrl.searchParams.set('no_igdb', 'true');
        needsRedirect = true;
    }
    
    // Add protondb_tier from localStorage if not in URL
    if (!currentUrl.searchParams.has('protondb_tier') && filters.protondbTier) {
        currentUrl.searchParams.set('protondb_tier', filters.protondbTier);
        needsRedirect = true;
    }
    
    if (needsRedirect) {
        window.location.href = currentUrl.toString();
        return;
    }
}

// Store dropdown functionality
function toggleStoreDropdown() {
    const dropdown = document.getElementById('store-dropdown');
    const btn = dropdown.querySelector('.store-dropdown-btn');
    const isOpen = dropdown.classList.contains('open');
    
    dropdown.classList.toggle('open');
    btn.setAttribute('aria-expanded', !isOpen);
}

function getSelectedStores() {
    const checkboxes = document.querySelectorAll('#store-dropdown input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function getSelectedGenres() {
    const checkboxes = document.querySelectorAll('#genre-dropdown input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function buildUrl(stores, genres, queries, search, sort, order, excludeStreaming, collection, protondbTier, noIgdb) {
    const params = new URLSearchParams();
    stores.forEach(store => params.append('stores', store));
    genres.forEach(genre => params.append('genres', genre));
    queries.forEach(query => params.append('queries', query));
    if (search) params.set('search', search);
    if (sort) params.set('sort', sort);
    if (order) params.set('order', order);
    if (excludeStreaming) params.set('exclude_streaming', 'true');
    if (collection) params.set('collection', collection);
    if (protondbTier) params.set('protondb_tier', protondbTier);
    if (noIgdb) params.set('no_igdb', 'true');
    
    // Always save global filters to localStorage
    // Note: 'collection' is NOT saved (page-specific context)
    localStorage.setItem('globalFilters', JSON.stringify({
        stores: stores,
        genres: genres,
        queries: queries,
        excludeStreaming: excludeStreaming || false,
        noIgdb: noIgdb || false,
        protondbTier: protondbTier || ''
    }));
    
    return window.location.pathname + '?' + params.toString();
}

// Helper to get current advanced filter values from URL or localStorage
function getAdvancedFilters() {
    const params = new URLSearchParams(window.location.search);
    const globalFilters = getGlobalFilters();
    
    return {
        excludeStreaming: params.get('exclude_streaming') === 'true' || globalFilters.excludeStreaming || false,
        collection: parseInt(params.get('collection') || '0'),
        protondbTier: params.get('protondb_tier') || globalFilters.protondbTier || '',
        noIgdb: params.get('no_igdb') === 'true' || globalFilters.noIgdb || false
    };
}

function applyStoreFilter() {
    const stores = getSelectedStores();
    const genres = getSelectedGenres();
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, genres, queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

function clearStoreFilter() {
    const genres = getSelectedGenres();
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl([], genres, queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

// Genre dropdown functionality
function toggleGenreDropdown() {
    const dropdown = document.getElementById('genre-dropdown');
    const btn = dropdown.querySelector('.store-dropdown-btn');
    const isOpen = dropdown.classList.contains('open');
    
    dropdown.classList.toggle('open');
    btn.setAttribute('aria-expanded', !isOpen);
}

function applyGenreFilter() {
    const stores = getSelectedStores();
    const genres = getSelectedGenres();
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, genres, queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

function clearGenreFilter() {
    const stores = getSelectedStores();
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, [], queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

function getSelectedQueries() {
    const checkboxes = document.querySelectorAll('#queries-dropdown input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function applyQueryFilter() {
    const stores = getSelectedStores();
    const genres = getSelectedGenres();
    const queries = getSelectedQueries();
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, genres, queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

function clearQueryFilter() {
    const stores = getSelectedStores();
    const genres = getSelectedGenres();
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, genres, [], search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

function filterGenreOptions() {
    const searchInput = document.getElementById('genre-search-input');
    const searchTerm = searchInput.value.toLowerCase();
    const options = document.querySelectorAll('.genre-option');

    options.forEach(option => {
        const label = option.querySelector('.store-label').textContent.toLowerCase();
        if (label.includes(searchTerm)) {
            option.classList.remove('hidden');
        } else {
            option.classList.add('hidden');
        }
    });
}

function applySort(value) {
    // Close dropdown
    const dropdown = document.getElementById('sort-dropdown');
    if (dropdown) dropdown.style.display = 'none';
    
    const [sort, order] = value.split('-');
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const stores = window.currentStores && window.currentStores.length > 0 ? window.currentStores : globalFilters.stores;
    const genres = window.currentGenres && window.currentGenres.length > 0 ? window.currentGenres : globalFilters.genres;
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, genres, queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

// Query categories - will be set by each page
window.queryCategories = {};

// Function to find which category a query belongs to
function getCategoryForQuery(queryId) {
    for (const [category, filters] of Object.entries(window.queryCategories)) {
        if (filters.includes(queryId)) {
            return category;
        }
    }
    return null;
}

// Toggle query filter from dropdown (exclusive per category)
function toggleQueryFilterFromDropdown(queryId) {
    const checkbox = document.getElementById('query-' + queryId);
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const stores = window.currentStores && window.currentStores.length > 0 ? window.currentStores : globalFilters.stores;
    const genres = window.currentGenres && window.currentGenres.length > 0 ? window.currentGenres : globalFilters.genres;
    let queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    
    // Get the category of the clicked filter
    const category = getCategoryForQuery(queryId);
    
    if (category) {
        // Remove all filters from this category
        const categoryFilters = window.queryCategories[category];
        queries = queries.filter(q => !categoryFilters.includes(q));
        
        // Uncheck all checkboxes in this category
        categoryFilters.forEach(filterId => {
            const cb = document.getElementById('query-' + filterId);
            if (cb && cb !== checkbox) {
                cb.checked = false;
            }
        });
        
        // If checkbox is checked, add this filter
        if (checkbox.checked) {
            queries.push(queryId);
        }
    }
    
    const advanced = getAdvancedFilters();
    window.location.href = buildUrl(stores, genres, queries, search, sort, order, advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb);
}

// Dropdown toggle functionality
function toggleDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const isCurrentlyOpen = dropdown.style.display === 'block';
    
    // Close all dropdowns first
    document.querySelectorAll('.dropdown-content').forEach(function(dd) {
        dd.style.display = 'none';
        const btn = dd.previousElementSibling;
        if (btn && btn.hasAttribute('aria-expanded')) {
            btn.setAttribute('aria-expanded', 'false');
        }
    });
    
    // Open the clicked one if it was closed
    if (!isCurrentlyOpen) {
        dropdown.style.display = 'block';
        const btn = dropdown.previousElementSibling;
        if (btn && btn.hasAttribute('aria-expanded')) {
            btn.setAttribute('aria-expanded', 'true');
        }
    }
}

// Clear all filters
function clearAllFilters() {
    // Clear global filters from localStorage
    localStorage.removeItem('filterScope');
    localStorage.removeItem('globalFilters');
    
    // Redirect to clean page without any filters
    window.location.href = window.location.pathname;
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    const storeDropdown = document.getElementById('store-dropdown');
    if (storeDropdown && !storeDropdown.contains(event.target)) {
        storeDropdown.classList.remove('open');
        const btn = storeDropdown.querySelector('.store-dropdown-btn');
        if (btn) btn.setAttribute('aria-expanded', 'false');
    }
    const genreDropdown = document.getElementById('genre-dropdown');
    if (genreDropdown && !genreDropdown.contains(event.target)) {
        genreDropdown.classList.remove('open');
        const btn = genreDropdown.querySelector('.store-dropdown-btn');
        if (btn) btn.setAttribute('aria-expanded', 'false');
    }
    
    // Close other dropdowns
    if (!event.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown-content').forEach(function(dropdown) {
            dropdown.style.display = 'none';
            const btn = dropdown.previousElementSibling;
            if (btn && btn.hasAttribute('aria-expanded')) {
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    }
});

// Keyboard navigation support
document.addEventListener('keydown', function(event) {
    // ESC key - close all open dropdowns
    if (event.key === 'Escape') {
        // Close store/genre dropdowns
        const storeDropdown = document.getElementById('store-dropdown');
        if (storeDropdown) {
            storeDropdown.classList.remove('open');
            const btn = storeDropdown.querySelector('.store-dropdown-btn');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        }
        const genreDropdown = document.getElementById('genre-dropdown');
        if (genreDropdown) {
            genreDropdown.classList.remove('open');
            const btn = genreDropdown.querySelector('.store-dropdown-btn');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        }
        
        // Close other dropdowns
        document.querySelectorAll('.dropdown-content').forEach(function(dropdown) {
            dropdown.style.display = 'none';
            const btn = dropdown.previousElementSibling;
            if (btn && btn.hasAttribute('aria-expanded')) {
                btn.setAttribute('aria-expanded', 'false');
            }
        });
        
        // Remove focus from any focused element
        if (document.activeElement) {
            document.activeElement.blur();
        }
    }
    
    // Arrow key navigation within dropdowns
    const activeDropdown = document.querySelector('.dropdown-content[style*="display: block"]');
    if (activeDropdown && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
        event.preventDefault();
        
        const items = Array.from(activeDropdown.querySelectorAll('.dropdown-item input[type="checkbox"]'));
        const currentIndex = items.findIndex(item => item === document.activeElement || item.parentElement === document.activeElement);
        
        let nextIndex;
        if (event.key === 'ArrowDown') {
            nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        } else {
            nextIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        }
        
        items[nextIndex].focus();
    }
    
    // Enter/Space on checkbox to toggle
    if ((event.key === 'Enter' || event.key === ' ') && event.target.type === 'checkbox') {
        event.preventDefault();
        event.target.checked = !event.target.checked;
        // Trigger change event
        event.target.dispatchEvent(new Event('change', { bubbles: true }));
    }
});


// Intercept random game link clicks to add global filters
// Intercept random game link clicks to add global filters
function interceptRandomLinks() {
    const randomLinks = document.querySelectorAll('a[href="/random"]');
    randomLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            const filters = getGlobalFilters();
            const hasFilters = filters.stores.length > 0 || 
                             filters.genres.length > 0 || 
                             filters.queries.length > 0 ||
                             filters.excludeStreaming ||
                             filters.noIgdb ||
                             filters.protondbTier;
            
            if (hasFilters) {
                event.preventDefault();
                const url = new URL('/random', window.location.origin);
                filters.stores.forEach(store => url.searchParams.append('stores', store));
                filters.genres.forEach(genre => url.searchParams.append('genres', genre));
                filters.queries.forEach(query => url.searchParams.append('queries', query));
                if (filters.excludeStreaming) url.searchParams.set('exclude_streaming', 'true');
                if (filters.noIgdb) url.searchParams.set('no_igdb', 'true');
                if (filters.protondbTier) url.searchParams.set('protondb_tier', filters.protondbTier);
                window.location.href = url.toString();
            }
        });
    });
}

// Intercept navigation links to add global filters
function interceptNavigationLinks() {
    const navLinks = document.querySelectorAll('a[href="/library"], a[href="/discover"], a[href^="/collection/"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            const filters = getGlobalFilters();
            const hasFilters = filters.stores.length > 0 || 
                             filters.genres.length > 0 || 
                             filters.queries.length > 0 ||
                             filters.excludeStreaming ||
                             filters.noIgdb ||
                             filters.protondbTier;
            
            if (hasFilters) {
                event.preventDefault();
                const url = new URL(link.getAttribute('href'), window.location.origin);
                filters.stores.forEach(store => url.searchParams.append('stores', store));
                filters.genres.forEach(genre => url.searchParams.append('genres', genre));
                filters.queries.forEach(query => url.searchParams.append('queries', query));
                if (filters.excludeStreaming) url.searchParams.set('exclude_streaming', 'true');
                if (filters.noIgdb) url.searchParams.set('no_igdb', 'true');
                if (filters.protondbTier) url.searchParams.set('protondb_tier', filters.protondbTier);
                window.location.href = url.toString();
            }
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    applyGlobalFiltersOnLoad();
    interceptRandomLinks();
    interceptNavigationLinks();
    
    // Save current filters
    saveCurrentFilters();
});

// ========== Advanced Filters Support (MAIN branch integration) ==========

// Collection filter
function applyCollectionFilter(collectionId) {
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const stores = window.currentStores && window.currentStores.length > 0 ? window.currentStores : globalFilters.stores;
    const genres = window.currentGenres && window.currentGenres.length > 0 ? window.currentGenres : globalFilters.genres;
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    
    window.location.href = buildUrl(
        stores, genres, queries, search, sort, order,
        advanced.excludeStreaming, collectionId, advanced.protondbTier, advanced.noIgdb
    );
}

// ProtonDB tier filter
function applyProtonDBFilter(tier) {
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const stores = window.currentStores && window.currentStores.length > 0 ? window.currentStores : globalFilters.stores;
    const genres = window.currentGenres && window.currentGenres.length > 0 ? window.currentGenres : globalFilters.genres;
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    
    window.location.href = buildUrl(
        stores, genres, queries, search, sort, order,
        advanced.excludeStreaming, advanced.collection, tier, advanced.noIgdb
    );
}

// Toggle exclude streaming
function toggleExcludeStreaming() {
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const stores = window.currentStores && window.currentStores.length > 0 ? window.currentStores : globalFilters.stores;
    const genres = window.currentGenres && window.currentGenres.length > 0 ? window.currentGenres : globalFilters.genres;
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    
    window.location.href = buildUrl(
        stores, genres, queries, search, sort, order,
        !advanced.excludeStreaming, advanced.collection, advanced.protondbTier, advanced.noIgdb
    );
}

// Toggle no IGDB filter
function toggleNoIGDB() {
    // Merge current URL params with localStorage
    const globalFilters = getGlobalFilters();
    const stores = window.currentStores && window.currentStores.length > 0 ? window.currentStores : globalFilters.stores;
    const genres = window.currentGenres && window.currentGenres.length > 0 ? window.currentGenres : globalFilters.genres;
    const queries = window.currentQueries && window.currentQueries.length > 0 ? window.currentQueries : globalFilters.queries;
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    const advanced = getAdvancedFilters();
    
    window.location.href = buildUrl(
        stores, genres, queries, search, sort, order,
        advanced.excludeStreaming, advanced.collection, advanced.protondbTier, !advanced.noIgdb
    );
}
