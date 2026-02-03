// Global filter management functions

function saveCurrentFilters() {
    const currentUrl = new URL(window.location.href);
    const filters = {
        stores: currentUrl.searchParams.getAll('stores'),
        genres: currentUrl.searchParams.getAll('genres'),
        queries: currentUrl.searchParams.getAll('queries')
    };
    localStorage.setItem('globalFilters', JSON.stringify(filters));
}

function getGlobalFilters() {
    const stored = localStorage.getItem('globalFilters');
    return stored ? JSON.parse(stored) : { stores: [], genres: [], queries: [] };
}

// Apply global filters on page load if no filters in URL
function applyGlobalFiltersOnLoad() {
    const currentUrl = new URL(window.location.href);
    const hasFilters = currentUrl.searchParams.has('stores') || 
                     currentUrl.searchParams.has('genres') || 
                     currentUrl.searchParams.has('queries');
    
    if (!hasFilters) {
        const filters = getGlobalFilters();
        const hasGlobalFilters = filters.stores.length > 0 || 
                               filters.genres.length > 0 || 
                               filters.queries.length > 0;
        
        if (hasGlobalFilters) {
            // Redirect to same page with filters
            filters.stores.forEach(store => currentUrl.searchParams.append('stores', store));
            filters.genres.forEach(genre => currentUrl.searchParams.append('genres', genre));
            filters.queries.forEach(query => currentUrl.searchParams.append('queries', query));
            window.location.href = currentUrl.toString();
            return;
        }
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

function buildUrl(stores, genres, queries, search, sort, order) {
    const params = new URLSearchParams();
    stores.forEach(store => params.append('stores', store));
    genres.forEach(genre => params.append('genres', genre));
    queries.forEach(query => params.append('queries', query));
    if (search) params.set('search', search);
    if (sort) params.set('sort', sort);
    if (order) params.set('order', order);
    
    // Always save filters to localStorage (filters are always global now)
    localStorage.setItem('globalFilters', JSON.stringify({
        stores: stores,
        genres: genres,
        queries: queries
    }));
    
    return window.location.pathname + '?' + params.toString();
}

function applyStoreFilter() {
    const stores = getSelectedStores();
    const genres = getSelectedGenres();
    const queries = window.currentQueries || [];
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    window.location.href = buildUrl(stores, genres, queries, search, sort, order);
}

function clearStoreFilter() {
    const genres = getSelectedGenres();
    const queries = window.currentQueries || [];
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    window.location.href = buildUrl([], genres, queries, search, sort, order);
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
    const queries = window.currentQueries || [];
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    window.location.href = buildUrl(stores, genres, queries, search, sort, order);
}

function clearGenreFilter() {
    const stores = getSelectedStores();
    const queries = window.currentQueries || [];
    const search = window.currentSearch || '';
    const sort = window.currentSort || 'name';
    const order = window.currentOrder || 'asc';
    window.location.href = buildUrl(stores, [], queries, search, sort, order);
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
    const stores = window.currentStores || [];
    const genres = window.currentGenres || [];
    const queries = window.currentQueries || [];
    const search = window.currentSearch || '';
    window.location.href = buildUrl(stores, genres, queries, search, sort, order);
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
    const stores = window.currentStores || [];
    const genres = window.currentGenres || [];
    let queries = window.currentQueries || [];
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
    
    window.location.href = buildUrl(stores, genres, queries, search, sort, order);
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
                             filters.queries.length > 0;
            
            if (hasFilters) {
                event.preventDefault();
                const url = new URL('/random', window.location.origin);
                filters.stores.forEach(store => url.searchParams.append('stores', store));
                filters.genres.forEach(genre => url.searchParams.append('genres', genre));
                filters.queries.forEach(query => url.searchParams.append('queries', query));
                window.location.href = url.toString();
            }
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    applyGlobalFiltersOnLoad();
    interceptRandomLinks();
    
    // Save current filters
    saveCurrentFilters();
    
    // Use event delegation for store checkboxes (more reliable)
    const storeDropdown = document.getElementById('store-dropdown');
    if (storeDropdown) {
        storeDropdown.addEventListener('change', function(event) {
            if (event.target.type === 'checkbox' && event.target.name === 'stores') {
                // Small delay to allow multiple quick selections
                clearTimeout(window.storeFilterTimeout);
                window.storeFilterTimeout = setTimeout(() => {
                    applyStoreFilter();
                }, 300);
            }
        });
    }
    
    // Use event delegation for genre checkboxes (more reliable)
    const genreDropdown = document.getElementById('genre-dropdown');
    if (genreDropdown) {
        genreDropdown.addEventListener('change', function(event) {
            if (event.target.type === 'checkbox' && event.target.name === 'genres') {
                // Small delay to allow multiple quick selections
                clearTimeout(window.genreFilterTimeout);
                window.genreFilterTimeout = setTimeout(() => {
                    applyGenreFilter();
                }, 300);
            }
        });
    }
});

