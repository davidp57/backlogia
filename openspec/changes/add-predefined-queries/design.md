## Context

The library page currently supports filtering by stores, genres, and text search, plus sorting by various fields. These filters are applied as query parameters and produce SQL WHERE clauses dynamically. The UI displays filter tags that can be toggled on/off, with active filters persisting in the URL.

This design extends the existing filter architecture to support predefined query filters - reusable SQL conditions mapped to user-friendly labels like "Unplayed" or "Highly Rated". The implementation should integrate seamlessly with existing filters without disrupting current behavior.

**Current Architecture:**
- `web/routes/library.py`: Handles `/library` route with `stores`, `genres`, `search`, `sort`, `order` parameters
- `web/templates/index.html`: Displays filter UI with store/genre tag pills
- JavaScript: Handles filter toggle and URL synchronization
- Database: SQLite with games table containing all necessary fields

**Constraints:**
- Must work with existing SQLite queries (no ORM, raw SQL)
- No database schema changes
- Must integrate with existing filter UI patterns
- Backend is FastAPI with Jinja2 templates

## Goals / Non-Goals

**Goals:**
- Add 18 predefined query filters across 4 categories (gameplay, ratings, dates, content)
- Support multi-select filter combinations
- Maintain URL persistence for bookmarking/sharing
- Show result counts for active filters
- Integrate seamlessly with existing store/genre filters
- Optimize query performance with appropriate indexes

**Non-Goals:**
- User-defined custom queries (future enhancement)
- Saved filter presets/favorites
- Filter recommendations/suggestions
- Applying filters to other pages (Discover, Collections)
- Advanced filter logic (AND/OR/NOT combinations beyond multi-select)
- Filter analytics or usage tracking

## Decisions

### 1. Filter Definition Structure

**Decision:** Define filters as a constant dictionary mapping filter IDs to SQL WHERE clause fragments.

**Rationale:**
- Keeps filter logic centralized and easy to modify
- SQL fragments can be directly injected into existing query builder
- Filter IDs serve as both URL parameters and internal references
- Dictionary structure allows easy lookup and validation

**Alternative Considered:**
- Database-stored filter definitions: Rejected due to unnecessary complexity for static filters
- Class-based filter objects: Rejected as overkill for simple WHERE clauses

**Implementation:**
```python
# In web/routes/library.py or web/utils/filters.py
PREDEFINED_QUERIES = {
    # Gameplay
    "unplayed": "(playtime_hours IS NULL OR playtime_hours = 0)",
    "played": "playtime_hours > 0",
    "started": "(playtime_hours > 0 AND playtime_hours < 5)",
    "well-played": "playtime_hours >= 5",
    "heavily-played": "playtime_hours >= 20",
    
    # Ratings
    "highly-rated": "total_rating >= 90",
    "well-rated": "total_rating >= 75",
    "below-average": "(total_rating < 75 AND total_rating IS NOT NULL)",
    "unrated": "total_rating IS NULL",
    "hidden-gems": "(total_rating >= 75 AND total_rating < 90 AND aggregated_rating IS NULL)",
    "critic-favorites": "aggregated_rating >= 80",
    "community-favorites": "(igdb_rating >= 85 AND igdb_rating_count >= 100)",
    
    # Dates
    "recently-added": "added_at >= DATE('now', '-30 days')",
    "older-library": "added_at < DATE('now', '-6 months')",
    "recent-releases": "release_date >= DATE('now', '-1 year')",
    "recently-updated": "last_modified >= DATE('now', '-30 days')",
    "classics": "(release_date <= DATE('now', '-10 years') AND total_rating >= 80)",
    
    # Content
    "nsfw": "nsfw = 1",
    "safe": "(nsfw = 0 OR nsfw IS NULL)"
}

# Display names for UI
QUERY_DISPLAY_NAMES = {
    "unplayed": "Unplayed",
    "played": "Played",
    "started": "Started",
    "well-played": "Well Played",
    "heavily-played": "Heavily Played",
    "highly-rated": "Highly Rated",
    "well-rated": "Well Rated",
    "below-average": "Below Average",
    "unrated": "Unrated",
    "hidden-gems": "Hidden Gems",
    "critic-favorites": "Critic Favorites",
    "community-favorites": "Community Favorites",
    "recently-added": "Recently Added",
    "older-library": "Older Library",
    "recent-releases": "Recent Releases",
    "recently-updated": "Recently Updated",
    "classics": "Classics",
    "nsfw": "NSFW",
    "safe": "Safe Content"
}

# Category grouping for UI organization
QUERY_CATEGORIES = {
    "Gameplay": ["unplayed", "played", "started", "well-played", "heavily-played"],
    "Ratings": ["highly-rated", "well-rated", "below-average", "unrated", "hidden-gems", 
                "critic-favorites", "community-favorites"],
    "Dates": ["recently-added", "older-library", "recent-releases", "recently-updated", "classics"],
    "Content": ["nsfw", "safe"]
}
```

### 2. Backend Query Building

**Decision:** Extend existing library route to accept `queries` parameter (list of filter IDs) and build combined WHERE clause.

**Rationale:**
- Minimal changes to existing code
- FastAPI's `Query(default=[])` handles multi-value parameters naturally
- SQL injection safe (filter clauses are hardcoded, not user input)
- Easy to combine with existing filters using AND logic

**Implementation:**
```python
@router.get("/library", response_class=HTMLResponse)
def library(
    request: Request,
    stores: list[str] = Query(default=[]),
    genres: list[str] = Query(default=[]),
    queries: list[str] = Query(default=[]),  # NEW
    search: str = "",
    sort: str = "name",
    order: str = "asc",
    conn: sqlite3.Connection = Depends(get_db)
):
    # ... existing setup ...
    
    query = "SELECT * FROM games WHERE 1=1" + EXCLUDE_HIDDEN_FILTER
    params = []
    
    # ... existing store/genre/search filters ...
    
    # NEW: Add predefined query filters
    if queries:
        valid_queries = [q for q in queries if q in PREDEFINED_QUERIES]
        if valid_queries:
            for query_id in valid_queries:
                query += f" AND {PREDEFINED_QUERIES[query_id]}"
    
    # ... rest of existing logic ...
```

**Alternative Considered:**
- Separate `/library/filtered` endpoint: Rejected to avoid code duplication
- Query builder class: Over-engineering for this use case

### 3. Frontend UI Integration

**Decision:** Add a new filter section below existing store/genre filters, using same tag pill styling.

**Rationale:**
- Consistent with existing UI patterns
- Users already familiar with multi-select tag behavior
- Natural visual grouping by category
- Minimal CSS changes needed

**Implementation:**
- Add filter section in `index.html` template
- Use same `.filter-tag` CSS class as store/genre filters
- Group filters by category with headers
- Active filters highlighted with `.active` class
- JavaScript toggles query parameters in URL

**Layout:**
```
[Store Filters: Steam | Epic | GOG ...]
[Genre Filters: Action | RPG | Adventure ...]
[Quick Filters:
  Gameplay: [Unplayed] [Played] [Started] ...
  Ratings: [Highly Rated] [Well Rated] ...
  Dates: [Recently Added] [Recent Releases] ...
  Content: [Safe Content] [NSFW]
]
[Game Grid...]
```

### 4. URL Parameter Strategy

**Decision:** Use repeated `queries=` parameters for multi-select (e.g., `?queries=unplayed&queries=highly-rated`).

**Rationale:**
- FastAPI handles this naturally with `list[str]`
- Standard REST pattern for multi-value parameters
- Works with existing URL state management
- Easy to parse and manipulate in JavaScript

**Alternative Considered:**
- Comma-separated single parameter: Harder to manipulate in JS, encoding issues
- JSON parameter: Overkill, poor URL readability

### 5. Performance Optimization

**Decision:** Add database indexes on frequently filtered columns if query performance degrades.

**Rationale:**
- SQLite benefits from indexes on WHERE clause columns
- Indexes have minimal storage overhead
- Can add incrementally based on actual performance data

**Indexes to consider:**
```sql
CREATE INDEX IF NOT EXISTS idx_games_playtime ON games(playtime_hours);
CREATE INDEX IF NOT EXISTS idx_games_total_rating ON games(total_rating);
CREATE INDEX IF NOT EXISTS idx_games_added_at ON games(added_at);
CREATE INDEX IF NOT EXISTS idx_games_release_date ON games(release_date);
CREATE INDEX IF NOT EXISTS idx_games_nsfw ON games(nsfw);
```

**When to add:** Only if page load times exceed 500ms with typical filter combinations (measure first, optimize second).

### 6. Filter Result Counts

**Decision:** Show result counts only for currently active filters, not all possible filters.

**Rationale:**
- Showing counts for all 18 filters requires 18 additional COUNT queries
- Performance impact too high for marginal UX benefit
- Active filter counts provide sufficient feedback
- Can add "preview counts" in future if needed with caching

**Implementation:**
- Display count in existing stats area: "Showing X games (Y total)"
- Active filter pills show count in badge: "[Unplayed (42)]"

## Risks / Trade-offs

### 1. Query Performance with Multiple Filters
**Risk:** Combining many filters could create slow queries, especially without proper indexes.

**Mitigation:**
- Add indexes on filtered columns
- Monitor query execution time in development
- Consider query plan analysis for complex combinations
- Document recommended filter combinations

### 2. Filter Conflict Logic
**Risk:** Users might select conflicting filters (e.g., "Unplayed" + "Heavily Played").

**Mitigation:**
- Allow conflicting filters (results in empty set, which is valid)
- Future: Add UI hints about inverse filters
- Document behavior: filters use AND logic (all must match)

### 3. Store-Specific Filters
**Risk:** "Recently Updated" only works for Epic Games, may confuse users.

**Mitigation:**
- Document in UI tooltip or help text
- Consider adding "(Epic only)" suffix to filter label
- Future: Dynamically show/hide store-specific filters based on selected stores

### 4. Mobile Responsiveness
**Risk:** 18 filter tags may clutter mobile UI.

**Mitigation:**
- Use collapsible category sections on mobile
- Show category count badges when collapsed
- Test thoroughly on mobile devices

### 5. Date Filter Accuracy
**Risk:** Date-based filters like "Recent Releases" depend on accurate release_date data, which may be missing or incorrect.

**Mitigation:**
- Filters handle NULL dates gracefully (excluded from results)
- Document that results depend on metadata quality
- Consider adding "Unknown Release Date" filter option

## Migration Plan

### Deployment Steps

1. **Backend changes** (non-breaking):
   - Add filter constants to `web/utils/filters.py` or `web/routes/library.py`
   - Update `library()` route to handle `queries` parameter
   - Add optional indexes in database migration

2. **Frontend changes** (non-breaking):
   - Add filter UI section to `index.html` template
   - Add JavaScript for filter toggle behavior
   - Add minimal CSS for filter category grouping

3. **Testing**:
   - Test all filter combinations
   - Verify URL persistence and bookmarking
   - Test with various database states (missing data, NULL values)
   - Check mobile responsiveness

4. **Rollout**:
   - Deploy to production (no downtime required)
   - Monitor query performance
   - Add indexes if needed based on metrics

### Rollback Strategy

Changes are additive and non-breaking:
- Remove `queries` parameter handling from backend (old URLs still work)
- Remove filter UI section from frontend
- Keep database indexes (harmless if unused)

No data migration or schema changes required, so rollback is straightforward.

## Open Questions

1. **Should we limit the number of active filters?**
   - Current thinking: No limit, let users experiment
   - Monitor for performance issues with many filters

2. **Should filters be mutually exclusive within categories?**
   - Current thinking: No, allow any combination
   - Exception: Conflicting filters (e.g., "Unplayed" + "Played") produce empty results

3. **Should we add "Clear All Filters" button?**
   - Current thinking: Yes, add to filter section
   - Should clear query filters only, or all filters including stores/genres?

4. **Should filter state persist in browser localStorage?**
   - Current thinking: URL persistence is sufficient for now
   - localStorage could be added later for "remember my filters" feature

5. **Should we show filter tooltips explaining criteria?**
   - Current thinking: Yes, helpful for transparency
   - Show SQL condition in tooltip for power users
