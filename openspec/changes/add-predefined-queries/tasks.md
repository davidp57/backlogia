## 1. Backend - Filter Definitions

- [x] 1.1 Create filter constants dictionary with 18 predefined queries (PREDEFINED_QUERIES) in web/utils/filters.py or web/routes/library.py
- [x] 1.2 Create display names dictionary (QUERY_DISPLAY_NAMES) mapping filter IDs to user-friendly names
- [x] 1.3 Create category grouping dictionary (QUERY_CATEGORIES) organizing filters into 4 categories
- [x] 1.4 Add unit tests for filter definition structure and completeness

## 2. Backend - Query Parameter Handling

- [x] 2.1 Add `queries` parameter to library() route in web/routes/library.py (list[str] with Query(default=[]))
- [x] 2.2 Implement validation logic to filter out invalid query IDs
- [x] 2.3 Add SQL WHERE clause building logic for predefined queries
- [x] 2.4 Integrate predefined query clauses with existing filter logic (stores, genres, search)
- [x] 2.5 Test query parameter handling with single and multiple filter combinations
- [x] 2.6 Test that invalid filter IDs are gracefully ignored
- [x] 2.7 Add query parameter support to discover() route
- [x] 2.8 Add query parameter support to collection_detail() route
- [x] 2.9 Add query parameter support to random_game() route

## 3. Backend - Result Counting

- [x] 3.1 Update stats calculation to include filtered count vs total count
- [x] 3.2 Pass filter counts to template context for display
- [x] 3.3 Test count accuracy with various filter combinations

## 4. Frontend - Filter UI Components

- [x] 4.1 Add "Quick Filters" section HTML structure in web/templates/index.html below existing filters
- [x] 4.2 Add category headers for each filter group (Gameplay, Ratings, Dates, Content)
- [x] 4.3 Create filter tag pills for all 18 predefined queries using existing .filter-tag styles
- [x] 4.4 Add active state highlighting for selected filters using .active class
- [x] 4.5 Add CSS for category grouping and responsive mobile layout
- [x] 4.6 Test UI layout on desktop and mobile devices
- [x] 4.7 Convert native select dropdowns to custom dropdowns for consistent dark theme styling
- [x] 4.8 Add date sorting options (Recently Added, Oldest in Library, Release Date)
- [x] 4.9 Add "Apply filters globally" checkbox

## 5. Frontend - Filter Toggle Behavior

- [x] 5.1 Add JavaScript function to handle filter tag clicks
- [x] 5.2 Implement URL parameter manipulation (add/remove queries parameter)
- [x] 5.3 Implement page reload with updated URL on filter toggle
- [x] 5.4 Preserve existing filters (stores, genres, search, sort) when toggling queries
- [x] 5.5 Test multi-select behavior (multiple filters can be active)
- [x] 5.6 Test browser back/forward button behavior with filter changes
- [x] 5.7 Implement exclusive category selection (only one filter per category can be active)

## 6. Global Filters Architecture

- [x] 6.1 Implement localStorage persistence for global filter state
- [x] 6.2 Add global filter scope toggle (library-only vs global)
- [x] 6.3 Apply global filters to /random route
- [x] 6.4 Refactor from click interception to auto-apply on page load
- [x] 6.5 Save current filters to localStorage when in global mode

## 7. Reusable Filter Components

- [x] 7.1 Create _filter_bar.html template component
- [x] 7.2 Create filters.css with all filter styles
- [x] 7.3 Create filters.js with all filter management functions
- [x] 7.4 Update discover.py to provide filter context data (store_counts, genre_counts, etc.)
- [x] 7.5 Update collections.py to provide filter context data
- [x] 7.6 Integrate filter components into discover.html
- [x] 7.7 Integrate filter components into collection_detail.html
- [x] 7.8 Integrate filter components into index.html (library)
- [x] 7.9 Hide filter bar on non-library pages when global filters are disabled

## 8. Performance Optimization

- [x] 8.1 Optimize discover page SQL queries (combined 5 queries into 1 UNION ALL)
- [x] 8.2 Create popularity_cache table for IGDB API data
- [x] 8.3 Implement get_cached_popularity() and cache_popularity_data() functions
- [x] 8.4 Add 24-hour cache expiration for popularity data
- [x] 8.5 Add database indexes for filter columns (playtime_hours, total_rating, added_at, release_date, nsfw)

## 9. Integration Testing

- [x] 9.1 Test all 18 individual filters work correctly with expected SQL conditions
- [x] 9.2 Test filter combinations (2-3 filters active simultaneously)
- [x] 9.3 Test filters with existing store/genre filters active
- [x] 9.4 Test filters with search and sorting active
- [x] 9.5 Test URL persistence and bookmarking
- [x] 9.6 Test that hidden games are still excluded with filters active
- [x] 9.7 Test that IGDB game grouping still works with filters active
- [x] 9.8 Test NULL value handling in date and rating filters
- [x] 9.9 Test empty result sets (no games match filters)
- [x] 9.10 Test global filters across all pages (library, discover, collections, random)

## 10. Edge Cases and Error Handling

- [x] 10.1 Test conflicting filter combinations (e.g., unplayed + heavily-played)
- [x] 10.2 Test filters with missing/NULL database fields
- [x] 10.3 Test Recently Updated filter with non-Epic games (should show no results)
- [x] 10.4 Test with empty library (no games)
- [x] 10.5 Test with very large library (performance)
- [x] 10.6 Test "Clear All Filters" button resets global filters in localStorage

## 11. UI Polish and User Experience

- [x] 11.1 Add tooltips to filter tags explaining criteria (optional)
- [x] 11.2 Add "(Epic only)" suffix to Recently Updated filter label
- [x] 11.3 Add result count badges to active filter pills (optional)
- [x] 11.4 Consider adding "Clear All Filters" button
- [x] 11.5 Test keyboard navigation and accessibility

## 12. Documentation and Deployment

- [x] 12.1 Update CHANGELOG.md with feature description
- [x] 12.2 Add documentation in .copilot-docs/ explaining filter system
- [x] 12.3 Document filter SQL conditions for transparency
- [x] 12.4 Update README.md if needed to mention predefined filters
- [x] 12.5 Commit changes with conventional commit message
- [ ] 12.6 Test in Docker environment before deployment
- [ ] 12.7 Deploy to production and monitor query performance
