# Predefined Query Filters System

## Overview

The predefined query filters system provides a flexible, reusable filtering mechanism for games across the Backlogia application. It enables users to filter their library, collections, and discovery pages using 18 predefined filters organized into 4 categories.

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
- `status`: Game completion and play status (8 filters)
- `metadata`: Games with/without external metadata (4 filters)
- `playtime`: Playtime-based filters (4 filters)
- `release`: Release date filters (2 filters)

**Key Design Principles:**
- Each filter has a unique ID (kebab-case)
- SQL conditions are parameterized and injectable
- Filters can be combined with AND logic
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

**Function:** `build_predefined_filter_sql(filter_ids: list[str]) -> str`

Converts filter IDs into SQL WHERE conditions.

**Logic:**
- Retrieves SQL query for each valid filter ID
- Combines multiple filters with `AND`
- Returns empty string if no valid filters
- Each condition is wrapped in parentheses for safety

**Example:**
```python
build_predefined_filter_sql(["unplayed", "backlog"])
# Returns: "(playtime_seconds = 0) AND (tags LIKE '%backlog%')"
```

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
# Parse filters from query params
selected_filters = parse_predefined_filters(request.query_params.get("predefined", ""))

# Build SQL WHERE clause
filter_sql = build_predefined_filter_sql(selected_filters)

# Add to main query
if filter_sql:
    conditions.append(filter_sql)
```

**Routes Using Filters:**
- `web/routes/library.py`: Main library page with filter counting
- `web/routes/collections.py`: Collection detail pages
- `web/routes/discover.py`: Game discovery page

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

### Unit Tests (`tests/test_predefined_filters.py`)

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

## Extension Guide

### Adding a New Filter

1. **Define in `PREDEFINED_QUERIES`:**
```python
"new-filter": {
    "label": "Display Name",
    "description": "What this filter does",
    "query": "SQL WHERE condition",
    "category": "existing_category"
}
```

2. **Create database index (if needed):**
```python
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_new_column
    ON games(new_column)
""")
```

3. **Add to filter bar template:**

Template will automatically pick up new filter from `PREDEFINED_QUERIES`.

4. **Write tests:**
```python
def test_new_filter_integration(client):
    response = client.get("/library?predefined=new-filter")
    # Verify results match expected SQL condition
```

### Adding a New Category

1. **Update `PREDEFINED_QUERIES`:**

Add filters with `"category": "new_category"`

2. **Update filter bar template:**

Add new section in `_filter_bar.html`:
```html
<div class="filter-section">
    <button class="filter-dropdown-toggle" aria-label="Category Name">
        Category Name
    </button>
    <div class="filter-options" role="group">
        {% for filter_id, filter_data in predefined_queries.items() %}
            {% if filter_data.category == 'new_category' %}
                <!-- Filter checkbox -->
            {% endif %}
        {% endfor %}
    </div>
</div>
```

3. **Update JavaScript (if interactive):**

Add dropdown toggle handler in `filters.js`.

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
| SQL generation | `web/utils/filters.py` |
| Filter counting | `web/utils/helpers.py` |
| Library route | `web/routes/library.py` |
| Collections route | `web/routes/collections.py` |
| Discovery route | `web/routes/discover.py` |
| Filter bar UI | `web/templates/_filter_bar.html` |
| JavaScript logic | `web/static/js/filters.js` |
| CSS styles | `web/static/css/filters.css` |
| Unit tests | `tests/test_predefined_filters.py` |
| Integration tests | `tests/test_predefined_filters_integration.py` |

## Related Documentation

- **API Reference**: See OpenAPI spec in `openspec/specs/predefined-query-filters/spec.md`
- **Design Decisions**: See `openspec/changes/add-predefined-queries/design.md`
- **Change Proposal**: See `openspec/changes/add-predefined-queries/proposal.md`
