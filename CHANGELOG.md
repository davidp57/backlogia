# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Merge MAIN → feat-global-filters)

**From feat-global-filters branch:**
- **Predefined query filters system**: 18 quick filters organized in 4 categories for better library organization:
  - **Gameplay** (5 filters): Unplayed, Played, Started, Well-Played, Heavily-Played
  - **Ratings** (7 filters): Highly-Rated, Well-Rated, Below-Average, Unrated, Hidden Gems, Critic Favorites, Community Favorites
  - **Dates** (5 filters): Recently Added, Older Library, Recent Releases, Recently Updated, Classics
  - **Content** (2 filters): NSFW, Safe
- **Global filter persistence**: 6 global filters (stores, genres, queries, excludeStreaming, noIgdb, protondbTier) persist across all pages via localStorage
- **Random page**: New `/random` endpoint with full page displaying configurable number of random games (default 12, max 50) with filter support
- **Reusable filter components**: Component-based architecture with `_filter_bar.html`, `filters.css`, and `filters.js` for consistent UX

**From MAIN branch:**
- **2-tier caching system** for IGDB data:
  - **Tier 1 (Memory)**: 15-minute cache for instant page loads (~0ms)
  - **Tier 2 (Database)**: 24-hour persistent cache surviving restarts
  - Hash-based invalidation on library changes
  - Filter-specific caching (each filter combo gets own cache)
- **Advanced filter suite** (4 new filters):
  - **Collection filter**: Show games from specific user collections
  - **ProtonDB tier filter**: Hierarchical Steam Deck compatibility (Platinum > Gold > Silver > Bronze)
  - **Exclude streaming**: Hide cloud gaming services (Xbox Cloud, GeForce NOW)
  - **No IGDB data**: Show games missing IGDB metadata for curation
- **Xbox Game Pass integration**: Authentication via XSTS token, market/region selection, subscription plan configuration
- **CSS architecture refactoring**: Externalized 2000+ lines of inline CSS to shared files (`filters.css`, `shared-game-cards.css`, `discover-hero.css`)
- **Optional authentication system**: Password protection with bcrypt hashing and signed session tokens (opt-in via `ENABLE_AUTH`)
- **Docker environment detection**: Auto-detects Docker and disables LOCAL_GAMES_PATHS editing (use volume mounts instead)
- **Progressive Web App meta**: Theme color support for better mobile/PWA experience

**Combined features:**
- **Complete filter system**: 18 predefined queries + 4 advanced filters working in harmony
- **Performance optimizations**:
  - Database indexes on frequently filtered columns (playtime_hours, total_rating, added_at, release_date, nsfw, last_modified)
  - Discover page: 1 UNION ALL query for DB categories + parallel IGDB API fetching
  - 2-tier caching: 99.95% faster on cached loads
- **Comprehensive test suite**: 100+ tests covering filters, caching, edge cases, performance
- **Complete documentation**: Filter system architecture, SQL reference, merge documentation

### Changed
- **Filter behavior**: Filters are always global for simpler UX (no toggle needed)
- **Filter application**: Auto-apply with 300ms debounce using event delegation
- **Global filter count**: Expanded from 3 to 6 global filters (stores, genres, queries, excludeStreaming, noIgdb, protondbTier)
- **Discover page architecture**: Immediate render + AJAX for IGDB sections (non-blocking)
- **Filter bar**: Extended with 4 advanced filter UI components
- **JavaScript buildUrl()**: Signature extended from 6 to 10 parameters for advanced filters
- **Custom dropdowns**: Replaced native select elements with styled dropdowns for dark theme
- **Settings UI**: Conditional rendering based on Docker/bare-metal deployment
- **CSS organization**: Inline styles moved to external cacheable files

### Fixed
- **Global filter persistence**: Advanced filters (excludeStreaming, noIgdb) now persist across pages
- **Filter synchronization**: Defensive dual-save strategy (buildUrl + saveCurrentFilters) ensures robust persistence
- **Navigation link interception**: Global filters automatically added to Library/Discover/Collections/Random links
- **Docker localStorage conflicts**: Browser cache requires Ctrl+F5 hard refresh after code changes
- **Column validation**: PRAGMA-based sort column detection prevents SQL errors on schema changes
- **Filter state persistence**: Event delegation for dynamically loaded filter checkboxes
- **Recently Updated filter**: Works for all stores (uses `last_modified` field)

### Technical Details

**New files:**
- `web/utils/filters.py`: Filter definitions (PREDEFINED_QUERIES, QUERY_DISPLAY_NAMES, QUERY_CATEGORIES, QUERY_DESCRIPTIONS)
- `web/templates/_filter_bar.html`: Reusable filter bar component with 4 advanced filters
- `web/templates/random.html`: Random games page with grid layout
- `web/static/css/filters.css`: Filter bar styles (~500 lines)
- `web/static/css/shared-game-cards.css`: Game card components (~800 lines)
- `web/static/css/discover-hero.css`: Discover page hero section (~600 lines)
- `web/static/js/filters.js`: Global filter management with 6 global filters
- `tests/test_predefined_filters.py`: Unit tests (26)
- `tests/test_predefined_filters_integration.py`: Integration tests (26)
- `tests/test_empty_library.py`: Empty library tests (7)
- `tests/test_large_library_performance.py`: Performance tests (6)
- `tests/test_recently_updated_edge_case.py`: Edge case tests (4)
- `tests/test_advanced_filters.py`: Advanced filter tests (15+)
- `tests/test_caching_system.py`: 2-tier cache tests (20+)
- `.copilot-docs/filter-system.md`: Filter system architecture
- `.copilot-docs/filter-sql-reference.md`: SQL conditions reference
- `.copilot-docs/database-schema.md`: Database schema documentation
- `merge_MAIN_to_FEAT_GLOBAL_FILTERS.md`: Comprehensive merge documentation (temporary file, will be removed post-PR)

**Modified files:**
- `web/routes/library.py`: Added 4 advanced filters + PRAGMA column validation
- `web/routes/discover.py`: 2-tier caching + modular architecture + filter integration
- `web/routes/collections.py`: Advanced filter support in collection detail page
- `web/routes/settings.py`: Xbox credentials + Docker detection
- `web/main.py`: Auth router import + DB table creation calls
- `web/database.py`: Added `popularity_cache` table + `ensure_predefined_query_indexes()`
- `web/templates/discover.html`: Removed 1800 lines inline CSS, external CSS links
- `web/templates/index.html`: Removed 300 lines inline CSS, external CSS links
- `web/templates/collection_detail.html`: CSS links + PWA theme-color meta tag
- `requirements.txt`: Added pytest, bcrypt, itsdangerous

**Database schema:**
- New table: `popularity_cache` (for Tier 2 caching)
- New indexes: On playtime_hours, total_rating, added_at, release_date, nsfw, last_modified
- New tables: `collections`, `collection_games` (for collection filtering)

**API changes:**
- `buildUrl()` JavaScript function: 6 → 10 parameters
- New endpoint: `/api/discover/igdb-sections` (AJAX IGDB section loading)
- Extended parameters: All route handlers accept 6 global filter parameters
