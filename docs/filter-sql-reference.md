# Predefined Filter SQL Reference

This document provides complete transparency on the SQL conditions used by each predefined filter in the Backlogia filter system.

## Overview

All filters are applied as `WHERE` conditions in SQL queries against the `games` table. Multiple filters are combined using `AND` logic. All conditions respect the current store and genre selections.

## Status Filters

Filters related to game completion and play status.

### Unplayed

**Filter ID:** `unplayed`

**Label:** Games I haven't played yet

**SQL Condition:**
```sql
playtime_seconds = 0
```

**Logic:** Matches games where recorded playtime is exactly 0 seconds.

**NULL Handling:** Games with `NULL` playtime are excluded (treated as unknown, not unplayed).

---

### Backlog

**Filter ID:** `backlog`

**Label:** Games in my backlog

**SQL Condition:**
```sql
tags LIKE '%backlog%'
```

**Logic:** Matches games where the `tags` field contains the word "backlog" anywhere.

**Case Sensitivity:** Case-insensitive (SQLite `LIKE` default).

**NULL Handling:** Games with `NULL` tags are excluded.

---

### Recently Played

**Filter ID:** `recently-played`

**Label:** Games I've played in the last 2 weeks

**SQL Condition:**
```sql
last_played_date >= date('now', '-14 days')
```

**Logic:** Matches games played within the last 14 days from today.

**Date Calculation:** Uses SQLite's `date()` function with relative offset.

**NULL Handling:** Games with `NULL` last_played_date are excluded.

---

### Completed

**Filter ID:** `completed`

**Label:** Games I've completed

**SQL Condition:**
```sql
completed_date IS NOT NULL
```

**Logic:** Matches games with any completion date set.

**Note:** Does not validate if the date is in the past.

---

### Never Finished

**Filter ID:** `never-finished`

**Label:** Games I played but never finished

**SQL Condition:**
```sql
playtime_seconds > 0 AND completed_date IS NULL
```

**Logic:** Matches games with playtime but no completion date.

**Interpretation:** User started playing but never marked as completed.

---

### Currently Playing

**Filter ID:** `currently-playing`

**Label:** Games I'm currently playing

**SQL Condition:**
```sql
tags LIKE '%currently-playing%'
```

**Logic:** Matches games tagged with "currently-playing".

**Case Sensitivity:** Case-insensitive.

**NULL Handling:** Games with `NULL` tags are excluded.

---

### On Hold

**Filter ID:** `on-hold`

**Label:** Games I've put on hold

**SQL Condition:**
```sql
tags LIKE '%on-hold%'
```

**Logic:** Matches games tagged with "on-hold".

**Case Sensitivity:** Case-insensitive.

**NULL Handling:** Games with `NULL` tags are excluded.

---

### Wishlist

**Filter ID:** `wishlist`

**Label:** Games on my wishlist

**SQL Condition:**
```sql
tags LIKE '%wishlist%'
```

**Logic:** Matches games tagged with "wishlist".

**Case Sensitivity:** Case-insensitive.

**NULL Handling:** Games with `NULL` tags are excluded.

---

## Metadata Filters

Filters for games with or without external metadata from services like IGDB, Metacritic, and ProtonDB.

### IGDB Data

**Filter ID:** `has-igdb`

**Label:** Games with IGDB metadata

**SQL Condition:**
```sql
igdb_id IS NOT NULL
```

**Logic:** Matches games with an IGDB ID assigned.

**Note:** Presence of ID does not guarantee all metadata fields are populated.

---

### No IGDB Data

**Filter ID:** `no-igdb`

**Label:** Games without IGDB metadata

**SQL Condition:**
```sql
igdb_id IS NULL
```

**Logic:** Matches games without an IGDB ID.

**Use Case:** Identify games needing metadata enrichment.

---

### Metacritic Scores

**Filter ID:** `has-metacritic`

**Label:** Games with Metacritic scores

**SQL Condition:**
```sql
metacritic_score IS NOT NULL
```

**Logic:** Matches games with a Metacritic score.

**Score Range:** Typically 0-100, but not validated by this filter.

---

### ProtonDB Data

**Filter ID:** `has-protondb`

**Label:** Games with ProtonDB compatibility ratings

**SQL Condition:**
```sql
protondb_tier IS NOT NULL
```

**Logic:** Matches games with a ProtonDB compatibility tier.

**Tiers:** Usually "platinum", "gold", "silver", "bronze", "borked" (not validated).

**Use Case:** Find Linux/Proton-compatible games.

---

## Playtime Filters

Filters based on recorded playtime duration.

### Short Games

**Filter ID:** `short-games`

**Label:** Games playable in under 10 hours

**SQL Condition:**
```sql
playtime_seconds > 0 AND playtime_seconds <= 36000
```

**Logic:** Matches games with 1 second to 10 hours of playtime.

**Time Calculation:** 10 hours = 36,000 seconds.

**Interpretation:** Assumes playtime reflects game length (may not be accurate for unfinished games).

---

### Medium Games

**Filter ID:** `medium-games`

**Label:** Games requiring 10-30 hours

**SQL Condition:**
```sql
playtime_seconds > 36000 AND playtime_seconds <= 108000
```

**Logic:** Matches games with more than 10 hours up to 30 hours of playtime.

**Time Calculation:** 
- Lower bound: 10 hours = 36,000 seconds
- Upper bound: 30 hours = 108,000 seconds

---

### Long Games

**Filter ID:** `long-games`

**Label:** Games requiring 30-100 hours

**SQL Condition:**
```sql
playtime_seconds > 108000 AND playtime_seconds <= 360000
```

**Logic:** Matches games with more than 30 hours up to 100 hours of playtime.

**Time Calculation:**
- Lower bound: 30 hours = 108,000 seconds
- Upper bound: 100 hours = 360,000 seconds

---

### Epic Games

**Filter ID:** `epic-games`

**Label:** Games requiring 100+ hours

**SQL Condition:**
```sql
playtime_seconds > 360000
```

**Logic:** Matches games with more than 100 hours of playtime.

**Time Calculation:** 100 hours = 360,000 seconds.

**Note:** No upper limit.

---

## Release Filters

Filters based on game release dates.

### New Releases

**Filter ID:** `new-releases`

**Label:** Games released in the last 6 months

**SQL Condition:**
```sql
release_date >= date('now', '-6 months')
```

**Logic:** Matches games released within the last 180 days (approximately).

**Date Calculation:** Uses SQLite's `date()` function with `-6 months` offset.

**NULL Handling:** Games with `NULL` release_date are excluded.

---

### Classic Games

**Filter ID:** `classic-games`

**Label:** Games released 10+ years ago

**SQL Condition:**
```sql
release_date <= date('now', '-10 years')
```

**Logic:** Matches games released 10 or more years ago.

**Date Calculation:** Uses SQLite's `date()` function with `-10 years` offset.

**NULL Handling:** Games with `NULL` release_date are excluded.

---

## Combining Filters

When multiple filters are selected, they are combined with `AND` logic:

```sql
WHERE (condition1) AND (condition2) AND (condition3) ...
```

### Example 1: Unplayed + Backlog

**Selected Filters:** `unplayed`, `backlog`

**Combined SQL:**
```sql
WHERE (playtime_seconds = 0) AND (tags LIKE '%backlog%')
```

**Result:** Games that are both unplayed and tagged as backlog.

---

### Example 2: Recently Played + IGDB Data + Short Games

**Selected Filters:** `recently-played`, `has-igdb`, `short-games`

**Combined SQL:**
```sql
WHERE (last_played_date >= date('now', '-14 days'))
  AND (igdb_id IS NOT NULL)
  AND (playtime_seconds > 0 AND playtime_seconds <= 36000)
```

**Result:** Short games with IGDB metadata that were played in the last 2 weeks.

---

### Example 3: Completed + Long Games + Classic Games

**Selected Filters:** `completed`, `long-games`, `classic-games`

**Combined SQL:**
```sql
WHERE (completed_date IS NOT NULL)
  AND (playtime_seconds > 108000 AND playtime_seconds <= 360000)
  AND (release_date <= date('now', '-10 years'))
```

**Result:** Completed long games released over 10 years ago.

---

## Additional Context

All filters are applied **in addition to**:

1. **Store Filters:** If stores are selected (e.g., Steam, GOG), only games from those stores are included.
2. **Genre Filters:** If genres are selected, only games with those genres are included.
3. **Exclusion Queries:** Hidden games or other excluded items are filtered out.

### Full Query Structure

```sql
SELECT * FROM games
WHERE 1=1
  -- Store filter (if selected)
  AND store_key IN ('steam', 'gog')
  
  -- Genre filter (if selected)
  AND genres LIKE '%action%'
  
  -- Exclusion filter (e.g., hidden games)
  AND hidden = 0
  
  -- Predefined filters (if selected)
  AND (playtime_seconds = 0)
  AND (tags LIKE '%backlog%')
```

---

## NULL Value Handling Summary

| Column | NULL Interpretation | Filter Behavior |
|--------|---------------------|-----------------|
| `playtime_seconds` | Unknown playtime | Excluded from `unplayed`, included in `NULL = NULL` would be false |
| `completed_date` | Not completed | Included in `never-finished` |
| `last_played_date` | Never played | Excluded from `recently-played` |
| `release_date` | Unknown release | Excluded from date-based filters |
| `tags` | No tags set | Excluded from tag-based filters |
| `igdb_id` | No IGDB data | Included in `no-igdb` |
| `metacritic_score` | No score | Excluded from `has-metacritic` |
| `protondb_tier` | No rating | Excluded from `has-protondb` |

---

## Performance Considerations

### Indexed Columns

The following columns have indexes to optimize filter queries:

- `playtime_seconds`
- `completed_date`
- `last_played_date`
- `release_date`
- `tags` (partial index on filters using LIKE)

**Index Creation:** `ensure_predefined_query_indexes()` in `web/main.py`

### Query Optimization Tips

1. **Date Filters:** Use `date('now', 'offset')` for dynamic date calculations instead of hardcoded dates.
2. **Tag Filters:** Consider full-text search (FTS) if tag queries become slow with large datasets.
3. **Playtime Filters:** Use indexed column ranges for fast range scans.
4. **NULL Checks:** `IS NULL` is more efficient than `= NULL` (which always returns false).

---

## Testing SQL Conditions

Each filter condition is tested in:

- **Unit Tests:** `tests/test_predefined_filters.py`
- **Integration Tests:** `tests/test_predefined_filters_integration.py`

### Manual Testing

To test a filter condition directly in SQLite:

```sql
-- Example: Test unplayed filter
SELECT name, playtime_seconds FROM games WHERE playtime_seconds = 0;

-- Example: Test backlog filter
SELECT name, tags FROM games WHERE tags LIKE '%backlog%';

-- Example: Test recently-played filter
SELECT name, last_played_date FROM games WHERE last_played_date >= date('now', '-14 days');
```

---

## Modifying Filter Conditions

To change a filter's SQL condition:

1. **Update `PREDEFINED_QUERIES` in `web/utils/filters.py`:**
```python
"filter-id": {
    "label": "Display Name",
    "description": "Updated description",
    "query": "new SQL condition",  # ← Change this
    "category": "category_name"
}
```

2. **Update tests in `tests/test_predefined_filters_integration.py`:**
```python
def test_filter_id_integration(client):
    response = client.get("/library?predefined=filter-id")
    # Update assertions to match new condition
```

3. **Run tests to verify:**
```bash
pytest tests/test_predefined_filters_integration.py -v
```

4. **Update this documentation** to reflect the new condition.

---

## Security Notes

### SQL Injection Prevention

- All filter conditions are **hardcoded** in `PREDEFINED_QUERIES`
- No user input is directly interpolated into SQL
- Filter IDs from URL parameters are validated against known filters
- Unknown filter IDs are silently ignored

**Safe:**
```python
filter_ids = parse_predefined_filters(request.query_params.get("predefined"))
# Only known filter IDs are converted to SQL
filter_sql = build_predefined_filter_sql(filter_ids)
```

**Unsafe (NOT USED):**
```python
# ❌ NEVER DO THIS
user_sql = request.query_params.get("custom_sql")
cursor.execute(f"SELECT * FROM games WHERE {user_sql}")
```

### Data Privacy

- Filters operate on user's local game library
- No filter queries are sent to external services
- Metadata filters only check for presence of IDs, not content

---

## Related Documentation

- **Filter System Architecture**: `.copilot-docs/filter-system.md`
- **API Specification**: `openspec/specs/predefined-query-filters/spec.md`
- **Filter Definitions**: `web/utils/filters.py`
- **Database Schema**: `web/database.py`
