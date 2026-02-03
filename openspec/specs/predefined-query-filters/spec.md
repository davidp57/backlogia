# predefined-query-filters Specification

## Purpose
TBD - created by archiving change add-predefined-queries. Update Purpose after archive.
## Requirements
### Requirement: Predefined filter definitions
The system SHALL provide 18 predefined query filters organized into 4 categories (Gameplay, Ratings, Dates, Content). Each filter SHALL map to a specific SQL WHERE clause condition that filters games based on existing database fields.

#### Scenario: Filter definitions are available
- **WHEN** the library route initializes
- **THEN** all 18 predefined filters SHALL be defined with their SQL conditions and display names

#### Scenario: Filters are organized by category
- **WHEN** filters are rendered in the UI
- **THEN** filters SHALL be grouped into 4 categories: Gameplay (5 filters), Ratings (7 filters), Dates (5 filters), and Content (2 filters)

### Requirement: Query parameter handling
The system SHALL accept a `queries` parameter in the library route that contains a list of filter IDs. The route SHALL validate filter IDs against the predefined filter definitions.

#### Scenario: Single filter parameter
- **WHEN** user navigates to `/library?queries=unplayed`
- **THEN** system SHALL apply the "Unplayed" filter condition to the games query

#### Scenario: Multiple filter parameters
- **WHEN** user navigates to `/library?queries=unplayed&queries=highly-rated`
- **THEN** system SHALL apply both filter conditions using AND logic

#### Scenario: Invalid filter ID
- **WHEN** user provides an invalid filter ID in the queries parameter
- **THEN** system SHALL ignore the invalid filter ID and continue processing valid filters

#### Scenario: Empty queries parameter
- **WHEN** queries parameter is empty or not provided
- **THEN** system SHALL apply no predefined filters and show all games based on other filters

### Requirement: SQL filter application
The system SHALL build SQL WHERE clauses by combining predefined filter conditions with existing filters (stores, genres, search). All filters SHALL be combined using AND logic.

#### Scenario: Filter with existing store filter
- **WHEN** user applies queries=unplayed with stores=steam
- **THEN** system SHALL return only Steam games that are unplayed

#### Scenario: Filter with existing genre filter
- **WHEN** user applies queries=highly-rated with genres=Action
- **THEN** system SHALL return only Action games with rating >= 90

#### Scenario: Multiple predefined filters combined
- **WHEN** user applies queries=unplayed&queries=well-rated
- **THEN** system SHALL return games where (playtime_hours IS NULL OR playtime_hours = 0) AND total_rating >= 75

#### Scenario: Filter handles NULL values gracefully
- **WHEN** a filter condition references a field with NULL values
- **THEN** system SHALL handle NULL values according to SQL logic (e.g., "IS NULL" for Unrated filter)

### Requirement: Filter UI display
The system SHALL display predefined query filters in a dedicated filter section on the library page. Filters SHALL be organized by category with category headers.

#### Scenario: Filter section is visible
- **WHEN** user views the library page
- **THEN** system SHALL display a "Quick Filters" section below store and genre filters

#### Scenario: Filter tags are clickable
- **WHEN** user views filter tags
- **THEN** each filter SHALL be displayed as a clickable tag pill with the filter display name

#### Scenario: Active filters are highlighted
- **WHEN** a filter is active (present in URL queries parameter)
- **THEN** the filter tag SHALL have visual highlighting (active state)

#### Scenario: Filter categories have headers
- **WHEN** filters are displayed
- **THEN** each category SHALL have a visible header (e.g., "Gameplay:", "Ratings:")

### Requirement: Filter toggle behavior
The system SHALL allow users to toggle predefined filters on and off by clicking filter tags. Toggling a filter SHALL update the URL queries parameter and reload the filtered game list.

#### Scenario: Activate filter
- **WHEN** user clicks an inactive filter tag
- **THEN** system SHALL add the filter ID to the queries parameter and reload the page with filtered results

#### Scenario: Deactivate filter
- **WHEN** user clicks an active filter tag
- **THEN** system SHALL remove the filter ID from the queries parameter and reload the page

#### Scenario: Toggle preserves other filters
- **WHEN** user toggles a predefined filter while store or genre filters are active
- **THEN** system SHALL preserve all other active filters in the URL

#### Scenario: Multiple filters can be active
- **WHEN** user activates multiple predefined filters
- **THEN** system SHALL allow any combination of filters to be active simultaneously

### Requirement: URL persistence
The system SHALL persist active predefined filters in the URL using repeated `queries` parameters. URLs with active filters SHALL be bookmarkable and shareable.

#### Scenario: Bookmarked URL restores filters
- **WHEN** user bookmarks `/library?queries=unplayed&queries=highly-rated`
- **THEN** navigating to that URL SHALL apply both filters automatically

#### Scenario: Shared URL applies same filters
- **WHEN** user shares a library URL with queries parameters
- **THEN** other users opening that URL SHALL see the same filtered view

#### Scenario: URL updates on filter change
- **WHEN** user toggles any filter
- **THEN** the browser URL SHALL update to reflect the current filter state

#### Scenario: Browser back button works
- **WHEN** user clicks browser back button after changing filters
- **THEN** system SHALL restore the previous filter state from URL history

### Requirement: Filter result counting
The system SHALL display the count of games matching active filters in the existing stats area. The count SHALL update when filters are toggled.

#### Scenario: Count shows filtered results
- **WHEN** predefined filters are active
- **THEN** system SHALL display "Showing X games (Y total)" where X is filtered count and Y is total library count

#### Scenario: Count updates on filter toggle
- **WHEN** user activates or deactivates a filter
- **THEN** the displayed count SHALL update to reflect the new filtered result set

#### Scenario: No results message
- **WHEN** active filters result in zero matching games
- **THEN** system SHALL display an appropriate message indicating no games match the criteria

### Requirement: Gameplay filters
The system SHALL provide 5 gameplay-based filters that filter games by playtime_hours field values.

#### Scenario: Unplayed filter
- **WHEN** Unplayed filter is active
- **THEN** system SHALL show games where playtime_hours IS NULL OR playtime_hours = 0

#### Scenario: Played filter
- **WHEN** Played filter is active
- **THEN** system SHALL show games where playtime_hours > 0

#### Scenario: Started filter
- **WHEN** Started filter is active
- **THEN** system SHALL show games where playtime_hours > 0 AND playtime_hours < 5

#### Scenario: Well Played filter
- **WHEN** Well Played filter is active
- **THEN** system SHALL show games where playtime_hours >= 5

#### Scenario: Heavily Played filter
- **WHEN** Heavily Played filter is active
- **THEN** system SHALL show games where playtime_hours >= 20

### Requirement: Rating filters
The system SHALL provide 7 rating-based filters that filter games by rating field values (total_rating, aggregated_rating, igdb_rating).

#### Scenario: Highly Rated filter
- **WHEN** Highly Rated filter is active
- **THEN** system SHALL show games where total_rating >= 90

#### Scenario: Well Rated filter
- **WHEN** Well Rated filter is active
- **THEN** system SHALL show games where total_rating >= 75

#### Scenario: Below Average filter
- **WHEN** Below Average filter is active
- **THEN** system SHALL show games where total_rating < 75 AND total_rating IS NOT NULL

#### Scenario: Unrated filter
- **WHEN** Unrated filter is active
- **THEN** system SHALL show games where total_rating IS NULL

#### Scenario: Hidden Gems filter
- **WHEN** Hidden Gems filter is active
- **THEN** system SHALL show games where total_rating >= 75 AND total_rating < 90 AND aggregated_rating IS NULL

#### Scenario: Critic Favorites filter
- **WHEN** Critic Favorites filter is active
- **THEN** system SHALL show games where aggregated_rating >= 80

#### Scenario: Community Favorites filter
- **WHEN** Community Favorites filter is active
- **THEN** system SHALL show games where igdb_rating >= 85 AND igdb_rating_count >= 100

### Requirement: Date filters
The system SHALL provide 5 date-based filters that filter games by date fields (added_at, release_date, last_modified).

#### Scenario: Recently Added filter
- **WHEN** Recently Added filter is active
- **THEN** system SHALL show games where added_at >= DATE('now', '-30 days')

#### Scenario: Older Library filter
- **WHEN** Older Library filter is active
- **THEN** system SHALL show games where added_at < DATE('now', '-6 months')

#### Scenario: Recent Releases filter
- **WHEN** Recent Releases filter is active
- **THEN** system SHALL show games where release_date >= DATE('now', '-1 year')

#### Scenario: Recently Updated filter
- **WHEN** Recently Updated filter is active
- **THEN** system SHALL show games where last_modified >= DATE('now', '-30 days')

#### Scenario: Classics filter
- **WHEN** Classics filter is active
- **THEN** system SHALL show games where release_date <= DATE('now', '-10 years') AND total_rating >= 80

### Requirement: Content filters
The system SHALL provide 2 content-based filters that filter games by NSFW status.

#### Scenario: NSFW Content filter
- **WHEN** NSFW Content filter is active
- **THEN** system SHALL show games where nsfw = 1

#### Scenario: Safe Content filter
- **WHEN** Safe Content filter is active
- **THEN** system SHALL show games where nsfw = 0 OR nsfw IS NULL

### Requirement: Filter interaction with existing features
The system SHALL ensure predefined filters work correctly with all existing library page features including sorting, search, and pagination.

#### Scenario: Filters work with sorting
- **WHEN** predefined filters are active and user changes sort order
- **THEN** system SHALL apply both filters and sorting to the results

#### Scenario: Filters work with search
- **WHEN** predefined filters are active and user enters search text
- **THEN** system SHALL apply both filters and search to the results

#### Scenario: Filters work with game grouping
- **WHEN** predefined filters are active
- **THEN** system SHALL still apply IGDB-based game grouping (multi-store deduplication)

#### Scenario: Filters respect hidden games
- **WHEN** predefined filters are active
- **THEN** system SHALL still exclude hidden games from results (existing EXCLUDE_HIDDEN_FILTER)

### Requirement: Global filter scope
The system SHALL provide a global filter mode that applies filters across multiple pages (Library, Discover, Collections, Random). Users SHALL be able to toggle between library-only and global filter scope.

#### Scenario: Filter scope toggle is visible
- **WHEN** user views the library page
- **THEN** system SHALL display a checkbox labeled "Apply filters globally" in the filter bar

#### Scenario: Global filters are persisted
- **WHEN** user enables global filter mode
- **THEN** system SHALL save the current filter state (stores, genres, queries) to localStorage

#### Scenario: Global filters apply to Discover page
- **WHEN** user navigates to /discover with global filters enabled
- **THEN** system SHALL apply the saved filters to the discover page results

#### Scenario: Global filters apply to Collections page
- **WHEN** user views a collection detail page with global filters enabled
- **THEN** system SHALL apply the saved filters to the collection games

#### Scenario: Global filters apply to Random page
- **WHEN** user requests a random game with global filters enabled
- **THEN** system SHALL select a random game from the filtered set

#### Scenario: Filter scope is preserved
- **WHEN** user reloads the page or returns later
- **THEN** system SHALL restore the filter scope setting from localStorage

#### Scenario: Library-only mode hides filter bar
- **WHEN** user disables global filters and navigates to a non-library page
- **THEN** system SHALL hide the filter bar on non-library pages

### Requirement: Reusable filter components
The system SHALL provide reusable template, CSS, and JavaScript components for filter functionality that can be integrated into multiple pages.

#### Scenario: Filter bar template component exists
- **WHEN** a route needs to display filters
- **THEN** system SHALL provide a _filter_bar.html Jinja2 component that can be included

#### Scenario: Filter styles are centralized
- **WHEN** filter bar is rendered
- **THEN** system SHALL use filters.css for all filter styling across pages

#### Scenario: Filter JavaScript is centralized
- **WHEN** filter bar needs interactivity
- **THEN** system SHALL use filters.js for all filter management functions across pages

#### Scenario: Routes provide filter context
- **WHEN** a route renders a page with filters
- **THEN** the route SHALL provide all required context variables (store_counts, genre_counts, current filters, query data)

#### Scenario: Filter bar is configurable
- **WHEN** including _filter_bar.html
- **THEN** system SHALL support configuration flags (show_search, show_sort, show_actions) to customize visibility

### Requirement: Performance optimization
The system SHALL optimize database queries and API calls to ensure fast page load times, particularly on the Discover page.

#### Scenario: Combined SQL queries
- **WHEN** Discover page loads
- **THEN** system SHALL use a single UNION ALL query instead of multiple separate queries

#### Scenario: Popularity data caching
- **WHEN** system needs game popularity data from IGDB API
- **THEN** system SHALL check popularity_cache table first and only call API if data is stale (older than 24 hours)

#### Scenario: Cache table exists
- **WHEN** database is initialized
- **THEN** system SHALL create popularity_cache table with columns (igdb_id, popularity_type, popularity_value, cached_at)

#### Scenario: Cache expiration
- **WHEN** cached popularity data is older than 24 hours
- **THEN** system SHALL fetch fresh data from IGDB API and update the cache

### Requirement: Reset filters functionality
The system SHALL provide a "Reset all filters" button that clears all active filters, including global filters stored in localStorage.

#### Scenario: Reset button clears URL parameters
- **WHEN** user clicks "Reset all filters"
- **THEN** system SHALL remove all filter parameters from the URL (stores, genres, queries, search, sort)

#### Scenario: Reset button clears localStorage
- **WHEN** user clicks "Reset all filters" with global filters enabled
- **THEN** system SHALL clear saved filter state from localStorage

#### Scenario: Reset button reloads page
- **WHEN** user clicks "Reset all filters"
- **THEN** system SHALL reload the page with no filters active

