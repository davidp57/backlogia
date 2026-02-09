# Predefined Query Filters System

## Overview

The predefined query filters system provides a flexible, reusable filtering mechanism for games across the Backlogia application. It enables users to filter their library, collections, and discovery pages using 18 predefined filters organized into 4 categories.

**Key Feature:** Filters within the same category are combined with **OR** logic, while filters from different categories are combined with **AND** logic. This allows intuitive multi-selection within categories (e.g., "show played OR started games") while maintaining strict requirements across categories (e.g., "AND highly-rated").

## Architecture

### Components

#### 1. Filter Definitions (`web/utils/filters.py`)

The core filter configuration is defined in `PREDEFINED_QUERIES`:

```python
PREDEFINED_QUERIES = {
    "filter_id": {
        "label": "Display Name",
        "description": "User-facing description",
        "query": "SQL WHERE condition",
        "category": "category_name"
    }
}
```

**Categories:**
- `Gameplay`: Game completion and play status (8 filters: unplayed, played, started, well-played, heavily-played, completed, abandoned, incomplete)
- `Ratings`: Rating-based filters (7 filters: highly-rated, well-rated, critic-favorites, community-favorites, hidden-gems, below-average, unrated)
- `Dates`: Time-based filters (5 filters: recently-added, old-games, recently-updated, new-releases, classics)
- `Content`: Content classification (2 filters: nsfw, safe)

**Key Design Principles:**
- Each filter has a unique ID (kebab-case)
- SQL conditions are parameterized and injectable
- **Filters within the same category are combined with OR logic**
- **Filters from different categories are combined with AND logic**
- All filters respect store and genre selections

#### 2. Query Parameter Parsing (`web/utils/filters.py`)

**Function:** `parse_predefined_filters(query_string: str) -> list[str]`

Parses URL query parameter `predefined` into a list of filter IDs.

**Formats Supported:**
- Single: `?predefined=unplayed`
- Multiple (comma): `?predefined=unplayed,backlog`
- Multiple (repeated): `?predefined=unplayed&predefined=backlog`

**Validation:**
- Unknown filter IDs are silently ignored
- Duplicate filter IDs are removed
- Empty/invalid values are filtered out

#### 3. SQL Generation (`web/utils/filters.py`)

**Function:** `build_query_filter_sql(query_ids: list[str], table_prefix: str = "") -> str`

Converts filter IDs into SQL WHERE conditions with intelligent OR/AND logic.

**Logic:**
1. Groups filters by category
2. Within each category: combines filters with **OR**
3. Between categories: combines groups with **AND**
4. Applies optional table prefix for JOIN queries (e.g., `g.` for collections)
5. Returns empty string if no valid filters

**Examples:**

*Single filter:*
```python
build_query_filter_sql(["played"])
# Returns: "(playtime_hours > 0)"
```

*Multiple filters, same category (OR):*
```python
build_query_filter_sql(["played", "started"])
# Returns: "((playtime_hours > 0) OR (playtime_hours > 0 AND playtime_hours < 5))"
# Meaning: Show games that are played OR started
```

*Multiple filters, different categories (AND):*
```python
build_query_filter_sql(["played", "highly-rated"])
# Returns: "((playtime_hours > 0) AND (total_rating >= 90))"
# Meaning: Show games that are played AND highly-rated
```

*Complex combination (OR within, AND between):*
```python
build_query_filter_sql(["played", "started", "highly-rated", "well-rated"])
# Returns: "(((playtime_hours > 0) OR (playtime_hours > 0 AND playtime_hours < 5)) AND ((total_rating >= 90) OR (total_rating >= 75)))"
# Meaning: Show games that are (played OR started) AND (highly-rated OR well-rated)
```

*With table prefix for JOIN queries:*
```python
build_query_filter_sql(["played"], table_prefix="g.")
# Returns: "(g.playtime_hours > 0)"
# Used in collection queries where games table is aliased as 'g'
```

**Why OR/AND Logic?**

This approach enables intuitive filter combinations:
- **Same category OR**: Select multiple gameplay states (e.g., "played OR started") without excluding all results
- **Different categories AND**: Maintain strict requirements across different aspects (e.g., "must be played AND must be highly-rated")

Without this logic, selecting "played" + "started" would return zero results (impossible for a game to be both), making multi-selection within categories useless.

### Filter Combination Logic

#### How Filters Are Combined

The system uses a two-level combination strategy:

1. **Within Categories (OR Logic)**
   - Filters in the same category are alternatives
   - Results match ANY selected filter from that category
   - Example: `[played OR started]` = games matching either condition

2. **Between Categories (AND Logic)**
   - Each category's result set must be satisfied
   - Results match ALL category requirements
   - Example: `[Gameplay filters] AND [Rating filters]` = games matching both groups

#### Practical Examples

**Example 1: Multiple Gameplay Filters**
```
Selected: "played", "started" (both from Gameplay category)
SQL: ((playtime_hours > 0) OR (playtime_hours > 0 AND playtime_hours < 5))
Result: Games that are played OR started
```

**Example 2: Multiple Rating Filters**
```
Selected: "highly-rated", "well-rated" (both from Ratings category)
SQL: ((total_rating >= 90) OR (total_rating >= 75))
Result: Games that are highly-rated OR well-rated
```

**Example 3: Cross-Category Selection**
```
Selected: "played" (Gameplay), "highly-rated" (Ratings)
SQL: ((playtime_hours > 0) AND (total_rating >= 90))
Result: Games that are played AND highly-rated
```

**Example 4: Complex Multi-Category**
```
Selected: "played", "started" (Gameplay), "highly-rated", "well-rated" (Ratings), "recently-added" (Dates)
SQL: (
    ((playtime_hours > 0) OR (playtime_hours > 0 AND playtime_hours < 5))
    AND
    ((total_rating >= 90) OR (total_rating >= 75))
    AND
    (added_at >= DATE('now', '-30 days'))
)
Result: Games that are (played OR started) AND (highly OR well rated) AND recently added
```

#### Category Reference

| Category | Filters | Combination |
|----------|---------|-------------|
| **Gameplay** | unplayed, played, started, well-played, heavily-played, completed, abandoned, incomplete | OR |
| **Ratings** | highly-rated, well-rated, critic-favorites, community-favorites, hidden-gems, below-average, unrated | OR |
| **Dates** | recently-added, old-games, recently-updated, new-releases, classics | OR |
| **Content** | nsfw, safe | OR |
| **Between Categories** | Any mix of categories | AND |

#### Implementation Details

The `build_query_filter_sql()` function implements this logic by:

1. **Grouping**: Iterates through selected filters and groups them by category using `QUERY_CATEGORIES` mapping
2. **Within-Category**: For each category with multiple filters, wraps them in `(filter1 OR filter2 OR ...)`
3. **Between-Category**: Wraps each category group and joins with AND: `(category1_group) AND (category2_group) AND ...`
4. **Parenthesization**: All conditions are properly parenthesized to avoid operator precedence issues
5. **Table Prefixing**: Optionally prefixes column names (e.g., `g.playtime_hours`) for JOIN queries in collections

**Code Location:** `web/utils/filters.py::build_query_filter_sql()`

#### 4. Filter Counting (`web/utils/helpers.py`)

**Function:** `get_query_filter_counts(cursor, stores, genres, exclude_query) -> dict[str, int]`

Calculates result counts for all filters in a single optimized query.

**Performance:**
- Single SQL query using `COUNT(CASE WHEN ... THEN 1 END)`
- Respects current store and genre selections
- Excludes games matching exclude_query
- Returns dict mapping filter_id → count

**Usage:**
```python
counts = get_query_filter_counts(cursor, ["steam"], ["action"], "hidden = 1")
# Returns: {"unplayed": 42, "backlog": 15, ...}
```

#### 5. Route Integration

**Pattern:**
```python
# Parse filters from query params (comma-separated or repeated)
queries = request.query_params.getlist("queries")  # e.g., ["played", "highly-rated"]

# Build SQL WHERE clause with OR/AND logic
filter_sql = build_query_filter_sql(queries)

# Add to main query
if filter_sql:
    query += f" AND {filter_sql}"
```

**For Collection Routes (with table aliases):**
```python
# Use table prefix for JOIN queries
filter_sql = build_query_filter_sql(queries, table_prefix="g.")

# Add to main query
if filter_sql:
    query += f" AND {filter_sql}"
```

**Routes Using Filters:**
- `web/routes/library.py`: Main library page with filter counting (no prefix)
- `web/routes/library.py`: Random game endpoint (no prefix)
- `web/routes/collections.py`: Collection detail pages (with `g.` prefix)
- `web/routes/discover.py`: Game discovery page (no prefix)

#### 6. Frontend Components

**Filter Bar (`web/templates/_filter_bar.html`):**
- Reusable Jinja2 template included in multiple pages
- Organizes filters by category with collapsible sections
- Shows result count badges (when available)
- Maintains filter state via query parameters

**JavaScript (`web/static/js/filters.js`):**
- Manages dropdown interactions
- Handles keyboard navigation (Esc, Arrow keys, Enter/Space)
- Updates ARIA states for accessibility
- Syncs selections with URL query parameters

**CSS (`web/static/css/filters.css`):**
- Styles filter dropdowns and badges
- Provides visual feedback for active filters
- Responsive design for mobile and desktop

## Data Flow

### User Interaction Flow

```
User clicks filter checkbox
  ↓
JavaScript updates URL with ?predefined=filter-id
  ↓
Browser navigates to new URL
  ↓
Backend parses predefined query param
  ↓
Converts to SQL WHERE conditions
  ↓
Executes database query with filters
  ↓
Returns filtered game results
  ↓
Template renders games with active filter indicators
```

### Filter Count Flow

```
Library route handler
  ↓
Checks if games exist in result
  ↓
Calls get_query_filter_counts() with current context
  ↓
Single SQL query counts matches for all filters
  ↓
Returns counts dict to template
  ↓
Template displays badges next to filter labels
```

## State Management

### URL-Based State

Filters are stored in URL query parameters for:
- **Shareability**: Users can bookmark filtered views
- **Browser history**: Back/forward buttons work naturally
- **Server-side rendering**: No client-side state sync needed

**Query Parameter Format:**
```
?predefined=filter1,filter2&stores=steam,gog&genres=action
```

### Multi-Page Consistency

The filter bar component is reused across pages:
- Library (`index.html`)
- Collections (`collection_detail.html`)
- Discovery (`discover.html`)

Each page maintains its own filter context but shares the same UI and logic.

## Performance Optimizations

### 1. Database Indexes

Indexes are created on commonly filtered columns:
- `completed_date`
- `last_played_date`
- `release_date`
- `playtime_seconds`
- `tags`

**Setup:** `ensure_predefined_query_indexes()` in `web/main.py` creates indexes on startup.

### 2. Efficient Counting

- Single query with `COUNT(CASE)` instead of 18 separate queries
- Only calculated on library page (most used)
- Skipped on discover/collection pages to reduce overhead

### 3. SQL Optimization

- All filter conditions use indexed columns
- `LIKE` clauses use prefix matching where possible
- NULL checks use `IS NULL` instead of `= NULL`

## Accessibility

### ARIA Attributes

- `aria-label`: Descriptive labels for screen readers
- `aria-haspopup="true"`: Indicates dropdown menus
- `aria-expanded`: Dynamic state for open/closed dropdowns
- `role="group"`: Semantic grouping of related filters

### Keyboard Navigation

- **Esc**: Close all dropdowns
- **Arrow Up/Down**: Navigate between filters
- **Enter/Space**: Toggle filter selection
- **Tab**: Move between interactive elements

### Color Contrast

All filter UI elements meet WCAG 2.1 Level AA contrast requirements.

## Testing

### Unit Tests

#### Filter Logic Tests (`tests/test_query_filter_logic.py`)

**Coverage:**
- Single filter SQL generation
- Multiple filters in same category (OR logic)
- Multiple filters in different categories (AND logic)
- Complex multi-category combinations
- Table prefix application
- Empty and invalid filter handling

**9 unit tests** validate the OR/AND combination logic.

#### Filter Definitions Tests (`tests/test_predefined_filters.py`)

**Coverage:**
- Filter parsing with various input formats
- SQL generation with single/multiple filters
- Invalid filter handling
- Edge cases (empty input, unknown IDs)

**26 unit tests** validate core filter logic.

### Integration Tests (`tests/test_predefined_filters_integration.py`)

**Coverage:**
- HTTP requests with filter query parameters
- Combinations of filters, stores, and genres
- NULL value handling
- Result correctness for each filter

**26 integration tests** validate end-to-end functionality.

#### Collection Filter Tests (`tests/test_predefined_filters_integration.py`)

**Coverage:**
- SQL column prefixing in collection queries
- Community favorites filter (igdb_rating, igdb_rating_count)
- Critic favorites filter (aggregated_rating)
- Recently updated filter (last_modified)
- Multiple filter combinations in collections

**4 integration tests** validate collection-specific filtering.

#### Genre Filter Tests (`tests/test_predefined_filters_integration.py`)

**Coverage:**
- Genre LIKE pattern with proper quote escaping
- Multiple genre filters with OR logic
- Genre filter does not match substrings incorrectly

**5 integration tests** validate genre filtering SQL patterns.

**Total: 70+ tests** covering all aspects of the filter system.

## Extension Guide

### Adding a New Filter

1. **Define in `PREDEFINED_QUERIES` (`web/utils/filters.py`):**
```python
"new-filter": "SQL WHERE condition (e.g., playtime_hours >= 100)"
```

2. **Add to `QUERY_DISPLAY_NAMES`:**
```python
"new-filter": "Display Name"
```

3. **Add to `QUERY_DESCRIPTIONS`:**
```python
"new-filter": "Description of what this filter does"
```

4. **Add to appropriate category in `QUERY_CATEGORIES`:**
```python
QUERY_CATEGORIES = {
    "Gameplay": [..., "new-filter"],  # Choose appropriate category
    # ...
}
```

**Important:** The category you choose determines how this filter combines with others:
- Filters in the same category will use OR logic
- Filters in different categories will use AND logic

5. **Create database index (if needed):**
```python
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_new_column
    ON games(new_column)
""")
```

6. **Write tests:**
```python
def test_new_filter_logic():
    """Test new filter SQL generation"""
    result = build_query_filter_sql(["new-filter"])
    assert "expected SQL condition" in result

def test_new_filter_integration(client):
    """Test new filter in HTTP request"""
    response = client.get("/library?queries=new-filter")
    # Verify results match expected SQL condition
```

### Adding a New Category

1. **Add to `QUERY_CATEGORIES` (`web/utils/filters.py`):**
```python
QUERY_CATEGORIES = {
    "Gameplay": [...],
    "Ratings": [...],
    "Dates": [...],
    "Content": [...],
    "New Category": ["filter1", "filter2"],  # New category
}
```

2. **Update filter bar template (`web/templates/_filter_bar.html`):**

The template automatically renders categories from `QUERY_CATEGORIES`, so no changes needed unless you want custom styling.

3. **Consider logical grouping:**

Remember that filters within your new category will combine with OR, while combinations with other categories will use AND. Choose filters that make sense as alternatives (e.g., different playtime ranges, different rating thresholds).

**Example Use Case:**

If you create a "Multiplayer" category with filters like "has-multiplayer", "co-op-only", "pvp-only", selecting multiple would show games matching ANY of those (OR logic), while combining with other categories would require games to match both multiplayer criteria AND other requirements.

### Testing Filter Combinations

When adding new filters or categories, test the OR/AND logic:

```python
def test_new_filter_same_category_or():
    """Test new filters in same category use OR"""
    result = build_query_filter_sql(["filter1", "filter2"])  # Same category
    assert " OR " in result
    assert result.count("(") == result.count(")")  # Balanced parentheses

def test_new_filter_cross_category_and():
    """Test new filter with existing category uses AND"""
    result = build_query_filter_sql(["new-filter", "played"])  # Different categories
    assert " AND " in result
    assert " OR " not in result or result.count(" AND ") > 0
```

## Maintenance Notes

### Common Issues

**Issue:** Filter returns no results unexpectedly
- **Check:** NULL handling in SQL condition
- **Fix:** Use `IS NULL` or `COALESCE()` for nullable columns

**Issue:** Filter counts are incorrect
- **Check:** `get_query_filter_counts()` includes all context (stores, genres, exclude_query)
- **Fix:** Ensure count query matches main query conditions

**Issue:** Filter not appearing in UI
- **Check:** Filter is in `PREDEFINED_QUERIES` with valid category
- **Check:** Template includes filter bar component
- **Fix:** Verify filter_id matches between backend and template

### Code Locations

| Component | File Path |
|-----------|-----------|
| Filter definitions | `web/utils/filters.py` |
| SQL generation with OR/AND logic | `web/utils/filters.py::build_query_filter_sql()` |
| Filter counting | `web/utils/helpers.py` |
| Library route | `web/routes/library.py` |
| Collections route | `web/routes/collections.py` |
| Discovery route | `web/routes/discover.py` |
| Filter bar UI | `web/templates/_filter_bar.html` |
| JavaScript logic | `web/static/js/filters.js` |
| CSS styles | `web/static/css/filters.css` |
| Filter logic unit tests | `tests/test_query_filter_logic.py` |
| Filter definitions tests | `tests/test_predefined_filters.py` |
| Integration tests | `tests/test_predefined_filters_integration.py` |

## Related Documentation

- **API Reference**: See OpenAPI spec in `openspec/specs/predefined-query-filters/spec.md`
- **Design Decisions**: See `openspec/changes/add-predefined-queries/design.md`
- **Change Proposal**: See `openspec/changes/add-predefined-queries/proposal.md`
