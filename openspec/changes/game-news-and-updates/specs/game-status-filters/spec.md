## ADDED Requirements

### Requirement: Filter definitions for development status
The system SHALL provide predefined filters for querying games by development status.

#### Scenario: Early Access filter
- **WHEN** Early Access filter is active
- **THEN** system SHALL show games where development_status = 'early_access'

#### Scenario: Alpha/Beta filter
- **WHEN** Alpha/Beta filter is active
- **THEN** system SHALL show games where development_status IN ('alpha', 'beta')

#### Scenario: Released filter
- **WHEN** Released filter is active
- **THEN** system SHALL show games where development_status = 'released'

#### Scenario: In Development filter (combined)
- **WHEN** In Development filter is active
- **THEN** system SHALL show games where development_status IN ('alpha', 'beta', 'early_access')

### Requirement: Filter definitions for update recency
The system SHALL provide predefined filters for querying games by recent update activity.

#### Scenario: Recently Modified filter
- **WHEN** Recently Modified filter is active
- **THEN** system SHALL show games where last_modified IS NOT NULL AND last_modified >= date('now', '-30 days')

#### Scenario: Updated This Week filter
- **WHEN** Updated This Week filter is active
- **THEN** system SHALL show games where last_modified >= date('now', '-7 days')

#### Scenario: Updated This Month filter
- **WHEN** Updated This Month filter is active
- **THEN** system SHALL show games where last_modified >= date('now', '-30 days')

### Requirement: Filter integration with existing system
The system SHALL integrate status filters with existing predefined filter system in web/utils/filters.py.

#### Scenario: Filter category addition
- **WHEN** status filters are defined
- **THEN** system SHALL add new "Development Status" category to QUERY_CATEGORIES

#### Scenario: Filter SQL definitions
- **WHEN** status filters are implemented
- **THEN** system SHALL add SQL WHERE clauses to PREDEFINED_QUERIES dictionary

#### Scenario: Filter combination with existing filters
- **WHEN** status filters are active alongside gameplay/rating/date filters
- **THEN** system SHALL combine all active filters with AND logic

### Requirement: Filter UI display
The system SHALL display status filters in the filter bar UI component.

#### Scenario: Status filter category in filter bar
- **WHEN** user views library page
- **THEN** system SHALL display "Development Status" dropdown in filter bar

#### Scenario: Filter options display
- **WHEN** user opens Development Status dropdown
- **THEN** system SHALL show available status filters as clickable options

#### Scenario: Active filter highlighting
- **WHEN** status filter is active
- **THEN** system SHALL highlight filter tag and show active state

#### Scenario: Filter count badges
- **WHEN** displaying status filters
- **THEN** system SHALL show count of games matching each filter

### Requirement: Filter persistence
The system SHALL persist active status filters in URL query parameters for bookmarking and sharing.

#### Scenario: URL parameter encoding
- **WHEN** user activates status filter
- **THEN** system SHALL add filter ID to 'predefined' query parameter

#### Scenario: Multiple filters in URL
- **WHEN** multiple status filters are active
- **THEN** system SHALL encode all active filter IDs as comma-separated values

#### Scenario: URL-based filter restoration
- **WHEN** page loads with predefined query parameter containing status filter IDs
- **THEN** system SHALL activate those filters and display filtered results

### Requirement: Filter global scope
The system SHALL apply status filters across all pages that display game lists.

#### Scenario: Library page filtering
- **WHEN** status filter is active on library page
- **THEN** system SHALL filter displayed games by status

#### Scenario: Discover page filtering
- **WHEN** status filter is active on discover page
- **THEN** system SHALL filter displayed games by status

#### Scenario: Collection detail filtering
- **WHEN** status filter is active on collection detail page
- **THEN** system SHALL filter displayed games by status

#### Scenario: Random page filtering
- **WHEN** status filter is active on random page
- **THEN** system SHALL select random games from filtered set

### Requirement: Filter with store limitations
The system SHALL handle store-specific limitations for update tracking filters.

#### Scenario: Steam update filter accuracy
- **WHEN** Recently Modified filter is active
- **THEN** system SHALL include Steam games with reliable last_modified data

#### Scenario: Epic update filter accuracy
- **WHEN** Recently Modified filter is active
- **THEN** system SHALL include Epic games with last_modified from Legendary

#### Scenario: GOG update filter limitation
- **WHEN** Recently Modified filter is active
- **THEN** system SHALL include GOG games but acknowledge limited accuracy

#### Scenario: Filter help text
- **WHEN** user views Recently Modified filter
- **THEN** system SHALL display help text indicating "Most reliable for Steam/Epic games"

### Requirement: Filter interaction with search
The system SHALL combine status filters with text search queries.

#### Scenario: Filter with search text
- **WHEN** user has active status filter and enters search text
- **THEN** system SHALL apply both status filter AND text search to results

#### Scenario: Search preserves filters
- **WHEN** user searches while filters are active
- **THEN** system SHALL maintain active filters in results

### Requirement: Filter interaction with sorting
The system SHALL apply status filters before sorting results.

#### Scenario: Filter then sort
- **WHEN** user has active status filter and changes sort order
- **THEN** system SHALL apply filter first, then sort filtered results

#### Scenario: Sort preserves filters
- **WHEN** user changes sort while filters are active
- **THEN** system SHALL maintain active filters and update sort

### Requirement: Filter reset functionality
The system SHALL allow users to clear all active status filters.

#### Scenario: Reset status filters
- **WHEN** user clicks "Reset Filters" or individual filter toggle
- **THEN** system SHALL remove status filters from query parameters and show unfiltered results

#### Scenario: Reset preserves other filter types
- **WHEN** user resets status filters while store/genre filters are active
- **THEN** system SHALL clear status filters but preserve store/genre selections

### Requirement: Filter result counting
The system SHALL calculate and display counts for each status filter option.

#### Scenario: Filter count calculation
- **WHEN** library page loads
- **THEN** system SHALL calculate count of games matching each status filter

#### Scenario: Count respects other active filters
- **WHEN** other filters (store, genre) are active
- **THEN** status filter counts SHALL reflect games matching both criteria

#### Scenario: Count display in UI
- **WHEN** filter counts are available
- **THEN** system SHALL display count next to each filter option (e.g., "Early Access (23)")

### Requirement: Filter performance optimization
The system SHALL optimize filter queries for performance with database indexes.

#### Scenario: Index on development_status
- **WHEN** system initializes
- **THEN** system SHALL create index on development_status column

#### Scenario: Index on last_modified
- **WHEN** system initializes
- **THEN** system SHALL create index on last_modified column if not exists

#### Scenario: Efficient COUNT queries
- **WHEN** calculating filter counts
- **THEN** system SHALL use single optimized query with CASE WHEN aggregation

### Requirement: Filter documentation
The system SHALL document filter behavior and limitations for users and developers.

#### Scenario: User help text
- **WHEN** user views status filters
- **THEN** system SHALL provide tooltips or help text explaining each filter

#### Scenario: Developer documentation
- **WHEN** developers reference filter system docs
- **THEN** system SHALL document SQL queries, limitations, and store compatibility

#### Scenario: Store compatibility indicators
- **WHEN** displaying update-based filters
- **THEN** system SHALL indicate which stores have full/partial/no support
