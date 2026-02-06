# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Desktop Application Mode**: Backlogia can now run as a standalone desktop application
  - PyWebView-based native window wrapper for Windows, macOS, and Linux
  - Automatic server startup and port management
  - Elegant loading screen with animated gradient design
  - **Single instance lock** - Prevents multiple instances from running simultaneously
  - **System tray icon** - Optional tray menu for quick access (requires pystray)
- Desktop executable packaging with PyInstaller
  - One-folder distribution with all dependencies bundled
  - Custom application icon
  - Windows GUI mode (no console window)
  - Persistent data storage in user directories (`%APPDATA%\Backlogia` on Windows)
- Automated build script (`build.py`) for creating desktop executables
- Loading screen route (`/loading`) for smooth app startup experience
- Enhanced bookmarklet UI detection for desktop vs browser mode
- **Predefined query filters system**: 18 quick filters organized in 4 categories for better library organization:
  - **Gameplay** (5 filters): Unplayed, Played, Started, Well-Played, Heavily-Played
  - **Ratings** (7 filters): Highly-Rated, Well-Rated, Below-Average, Unrated, Hidden Gems, Critic Favorites, Community Favorites
  - **Dates** (5 filters): Recently Added, Older Library, Recent Releases, Recently Updated, Classics
  - **Content** (2 filters): NSFW, Safe
- **Global filter persistence**: Filters always apply across all pages (Library, Discover, Collections, Random) and persist via localStorage
- **Random page**: New `/random` endpoint with full page displaying configurable number of random games (default 12, max 50) with filter support
- **Reusable filter components**: Component-based architecture with `_filter_bar.html`, `filters.css`, and `filters.js` for consistent UX
- **Performance optimizations**:
  - Database indexes on frequently filtered columns (playtime_hours, total_rating, added_at, release_date, nsfw, last_modified)
  - Discover page: reduced from 5+ queries to 1 UNION ALL query
  - IGDB popularity data: 24-hour caching system to reduce API calls
- **Comprehensive test suite**: 69 tests covering:
  - Filter definitions and SQL generation (26 unit tests)
  - Filter combinations and edge cases (26 integration tests)
  - Empty library handling (7 tests)
  - Performance with 10,000 games (6 tests)
  - Recently Updated filter edge cases (4 tests)
- **Editable local games paths in Settings**: Configure local game folder paths through web UI without editing .env files
- **Documentation**: Complete technical documentation in `.copilot-docs/` covering filter system architecture, SQL reference, and database schema
- **Game News & Status Tracking**: Comprehensive system for tracking game development status and news
  - **Steam News Feed**: Fetch and display recent news articles for Steam games with rate-limited API client (200 req/5min)
  - **Development Status Tracking**: Automatic detection of Early Access, Alpha, Beta, and Released status across Steam, Epic, and GOG
  - **Game Update History**: Track depot updates via `last_modified` timestamps with automatic change detection
  - **New Status Filters** (4 filters): Early Access, Leaving Early Access, In Development, Released
  - **Database Schema**: Two new tables (`game_news`, `game_depot_updates`) with indexed columns + 3 new columns on `games` table
  - **Game Detail View**: Collapsible News and Update History sections with auto-fetching via API
  - **Library View**: Compact status badges on game cards (EA/α/β/✓) with store-specific colors and tooltips
  - **Sync Endpoints**: REST API endpoints for news sync (`/api/sync/news/{mode}`) and status sync (`/api/sync/status/{mode}`)
  - **Settings Integration**: Dedicated "Game News & Status Tracking" section with manual sync buttons and cache controls
  - **Multi-Store Support**: News (Steam only), Status detection (Steam/Epic/GOG), Update tracking (Steam/Epic with Epic native support via Legendary CLI)
  - **Performance**: 24-hour news cache, 7-day status cache, ThreadPoolExecutor parallel processing (5 workers), URL-based deduplication
  - **Smart Caching**: Incremental sync with skip logic to minimize redundant API calls while allowing forced full resync

### Changed
- Settings page now shows different bookmarklet instructions for desktop app users
- Application data directory logic updated to support both dev and frozen (PyInstaller) modes
- Log files now stored in `%APPDATA%\Backlogia\logs\` when running as desktop app
- **Filter behavior**: Removed "Apply filters globally" checkbox—filters are now always global for simpler UX
- **Filter application**: Auto-apply with 300ms debounce using event delegation for better reliability
- **Random page**: Converted from redirect to full HTML page with game grid and filter integration
- **Filter bar**: Custom dropdowns with dark theme styling and count badges
- **Settings**: `LOCAL_GAMES_PATHS` now editable via web interface, stored in database (environment variables still take precedence for Docker)
- **Custom dropdowns**: Replaced native select elements with styled dropdowns for consistent dark theme

### Fixed
- Filter state persistence across page navigations
- Event listeners for dynamically loaded filter checkboxes using event delegation
- Recently Updated filter now works for all stores (uses `last_modified` field instead of Epic-specific `game_update_at`)

### Technical Details
- Added `desktop.py` launcher with threading-based server management
- Added PyInstaller configuration (`backlogia.spec`)
- Added development dependencies: `pywebview`, `pyinstaller`
- Server startup now waits for port availability before showing window
- Loading screen served via FastAPI endpoint for better compatibility
- **New files**:
  - `web/utils/filters.py`: Filter definitions (PREDEFINED_QUERIES, QUERY_DISPLAY_NAMES, QUERY_CATEGORIES, QUERY_DESCRIPTIONS)
  - `web/templates/_filter_bar.html`: Reusable filter bar component
  - `web/templates/random.html`: Random games page with grid layout
  - `web/static/css/filters.css`: Filter-specific styles
  - `web/static/js/filters.js`: Filter management with global state
  - `tests/test_predefined_filters.py`: Unit tests (26)
  - `tests/test_predefined_filters_integration.py`: Integration tests (26)
  - `tests/test_empty_library.py`: Empty library tests (7)
  - `tests/test_large_library_performance.py`: Performance tests (6)
  - `tests/test_recently_updated_edge_case.py`: Edge case tests (4)
  - `.copilot-docs/filter-system.md`: Filter system architecture
  - `.copilot-docs/filter-sql-reference.md`: SQL conditions reference
  - `.copilot-docs/database-schema.md`: Database schema documentation
- **Modified routes**: `library.py`, `discover.py`, `collections.py`, `settings.py` to support `queries` parameter
- **Database**: Added `popularity_cache` table and `ensure_predefined_query_indexes()` in `database.py`

## [0.1.0] - Previous Version

### Added
- Initial release with web-based game library management
- Support for multiple game stores (Steam, GOG, Epic, etc.)
- IGDB integration for game metadata
- Collections and custom organization
- Bookmarklet for quick game additions
