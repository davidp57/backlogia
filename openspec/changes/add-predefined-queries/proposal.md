## Why

Users currently have basic filtering capabilities (stores, genres, search) in the library view, but lack quick access to common queries like "unplayed games," "highly rated titles," or "recent releases." These queries require manual combination of sort/filter parameters and aren't easily reusable. Adding predefined query filters as toggleable tags would improve discoverability and reduce friction when browsing the library with specific intent.

## What Changes

Add a new filter section to the library page with predefined query tags that apply SQL-based filters to the games list. These filters will:

- Appear alongside existing store and genre filters as clickable tags
- Support multi-select (combine multiple predefined queries)
- Apply database-level filtering using existing fields (playtime, ratings, dates)
- Show result counts for each filter when applied
- Persist in URL query parameters for bookmarking

**New filter categories:**

### Gameplay-based filters
- **Unplayed**: `playtime_hours IS NULL OR playtime_hours = 0`
- **Played**: `playtime_hours > 0` (inverse of Unplayed)
- **Started**: `playtime_hours > 0 AND playtime_hours < 5`
- **Well Played**: `playtime_hours >= 5`
- **Heavily Played**: `playtime_hours >= 20`

### Rating-based filters
- **Highly Rated**: `total_rating >= 90`
- **Well Rated**: `total_rating >= 75`
- **Below Average**: `total_rating < 75 AND total_rating IS NOT NULL` (inverse of Well Rated)
- **Unrated**: `total_rating IS NULL` (games without ratings)
- **Hidden Gems**: `total_rating >= 75 AND total_rating < 90 AND aggregated_rating IS NULL`
- **Critic Favorites**: `aggregated_rating >= 80`
- **Community Favorites**: `igdb_rating >= 85 AND igdb_rating_count >= 100`

### Date-based filters
- **Recently Added**: `added_at >= DATE('now', '-30 days')`
- **Older Library**: `added_at < DATE('now', '-6 months')` (inverse of Recently Added)
- **Recent Releases**: `release_date >= DATE('now', '-1 year')`
- **Recently Updated**: `last_modified >= DATE('now', '-30 days')` (Epic only)
- **Classics**: `release_date <= DATE('now', '-10 years') AND total_rating >= 80`

### Content filters
- **NSFW Content**: `nsfw = 1`
- **Safe Content**: `nsfw = 0 OR nsfw IS NULL` (inverse of NSFW)

## Capabilities

### New Capabilities

- `predefined-query-filters`: Backend logic and UI components for applying predefined SQL filters to the library view, including multi-select support, result counting, and URL persistence

### Modified Capabilities

None - this extends existing library filtering without changing current filter behavior.

## Impact

### Affected Code
- **web/routes/library.py**: Add query parameter parsing and SQL filter building for predefined queries
- **web/templates/index.html**: Add new filter section UI with predefined query tags
- **web/static/js/**: Add JavaScript for toggle behavior and URL state management

### Database
- No schema changes required - uses existing fields
- Query performance may need optimization for complex filter combinations (consider indexes on `playtime_hours`, `total_rating`, `added_at`, `release_date`)

### UI/UX
- New filter section added above game grid
- Filter tags use same visual style as genre/store filters
- Active filters show result counts
- Clear visual feedback when filters are applied

### Store Integrations
- No changes to store sync logic
- "Recently Updated" filter only applies to Epic Games (other stores will show no results for this filter)
- Filter availability could be store-aware in future iterations

### Non-goals
- **Not** adding custom user-defined queries (future enhancement)
- **Not** modifying existing filter/sort behavior
- **Not** adding new database fields or columns
- **Not** creating saved filter presets (future enhancement)
- **Not** applying predefined queries to other pages (Discover, Collections)

## Implementation Approach

1. **Backend**: Extend library route to accept `queries` parameter (list of filter IDs), map to SQL WHERE clauses
2. **Frontend**: Add filter tag section, implement multi-select toggle behavior with URL state sync
3. **UI Design**: Follow existing filter styling (store/genre tags) for consistency
4. **Performance**: Add database indexes if query performance degrades with complex filters
5. **Testing**: Verify filter combinations work correctly, test URL persistence and bookmarking
