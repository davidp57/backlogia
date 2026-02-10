# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Comprehensive test coverage for labels system**: 62 new tests covering all metadata and bulk operations:
  - API integration tests (32 tests): All priority, rating, manual tag, and bulk operation endpoints
  - Database migration tests (12 tests): Collections→labels migration, metadata columns, CASCADE behavior
  - Manual tag persistence tests (5 tests): Auto vs manual tag conflict resolution, non-Steam games
  - Edge case tests (13 tests): Games with all metadata, system label deletion, NULL playtime handling, large library performance
- **Complete API documentation**: New `docs/api-metadata-endpoints.md` with request/response examples, curl commands, and error codes for all 13 metadata endpoints
- **Enhanced user documentation**: 
  - Quick Start guide with step-by-step workflows (auto-tagging, priorities, ratings, bulk actions, collections)
  - FAQ section with 12 common questions (e.g., "Why aren't my Epic games auto-tagged?", "Do manual tags get overwritten?")
  - Keyboard shortcuts documentation for multi-select mode (Shift-click range selection)
- **Developer contribution guide**: New `docs/contributing-labels-system.md` with:
  - System architecture diagrams (database schema, auto column lifecycle)
  - Tutorial for adding new system labels with code examples
  - Tutorial for adding new metadata fields (completion_status example)
  - Performance optimization techniques (batch processing, caching, indexing)
  - Migration best practices (idempotency, testing, rollback procedures)
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
- **Documentation**: Complete technical documentation in `.copilot-docs/` covering filter system architecture, SQL reference, and database schema

### Changed
- **Filter behavior**: Removed "Apply filters globally" checkbox—filters are now always global for simpler UX
- **Filter application**: Auto-apply with 300ms debounce using event delegation for better reliability
- **Random page**: Converted from redirect to full HTML page with game grid and filter integration
- **Filter bar**: Custom dropdowns with dark theme styling and count badges
- **Custom dropdowns**: Replaced native select elements with styled dropdowns for consistent dark theme

### Fixed
- Filter state persistence across page navigations
- Event listeners for dynamically loaded filter checkboxes using event delegation
- Recently Updated filter now works for all stores (uses `last_modified` field instead of Epic-specific `game_update_at`)

### Technical Details
- **New files**:
  - `tests/test_api_metadata_endpoints.py`: API integration tests for metadata endpoints (32 tests)
  - `tests/test_database_migrations.py`: Database migration tests (12 tests)
  - `tests/test_edge_cases_labels.py`: Edge case tests for labels system (13 tests)
  - `docs/api-metadata-endpoints.md`: Complete API reference with examples and error codes
  - `docs/contributing-labels-system.md`: Developer guide for labels system contributions
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
- **Modified files**:
  - `tests/test_system_labels_auto_tagging.py`: Added 5 manual tag persistence tests
  - `docs/system-labels-auto-tagging.md`: Added Quick Start guide, FAQ (12 questions), keyboard shortcuts
- **Modified routes**: `library.py`, `discover.py`, `collections.py`, `settings.py` to support `queries` parameter
- **Database**: Added `popularity_cache` table and `ensure_predefined_query_indexes()` in `database.py`
