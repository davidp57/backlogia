# Labels, Tags & Auto-Tagging

## Overview

Backlogia uses a unified **label system** to organize games. Labels serve two purposes:

- **User labels** (`type = 'collection'`, `system = 0`): Custom collections created by users (e.g., "Weekend Playlist", "Couch Co-op")
- **System labels** (`type = 'system_tag'`, `system = 1`): Gameplay tags automatically assigned based on playtime

This document covers the complete labels system: gameplay tags, auto-tagging, manual tagging, priority, personal ratings, and all related UI interactions.

---

## Quick Start

### Getting Started with Labels

**Step 1: Run Steam Sync**

Auto-tagging happens automatically during Steam sync. Go to Settings > Sync and click "Sync Steam Games".

```
[Sync] -> [Steam] -> Auto-tagging runs -> Games tagged by playtime
```

**Step 2: Verify Auto-Tags**

After sync completes, return to your library. You'll see gameplay tag badges on game cards:

- 🎮 **Never Launched** (slate gray) - 0 hours
- 👀 **Just Tried** (amber) - >0h, <2h  
- 🎯 **Played** (blue) - 2-10h
- ⭐ **Well Played** (violet) - 10-50h
- 🏆 **Heavily Played** (emerald) - ≥50h

**Step 3: Set Priorities**

Open a game's detail page and click the **Priority** pill below the title:

```
[Game Detail] -> Click "Priority: -" -> Select "High/Medium/Low"
```

The game card will now show a colored priority badge (red/amber/green) in the top-left corner.

**Step 4: Rate Games**

Click the **Rating** pill on the game detail page:

```
[Game Detail] -> Click "Rating: -" -> Select 1-10 stars
```

The game card will display a gold star badge with your rating.

**Step 5: Use Bulk Actions**

For multi-game operations, enable multi-select mode:

1. Click the floating **☑** button (bottom-right of library page)
2. Click checkboxes on game cards (or Shift-click for range selection)
3. Use the floating action bar to:
   - Add to collection
   - Set priority
   - Set personal rating
   - Assign playtime tag
   - Hide/NSFW/Delete games

**Step 6: Manual Tags for Non-Steam Games**

For games from Epic, GOG, etc. that don't have playtime tracking:

```
[Game Detail] -> Click "Playtime: -" -> Select tag manually
```

Manual tags persist and won't be overwritten by auto-tagging.

### Common Workflows

**Prioritize Your Backlog**
1. Filter library: "Gameplay > Never Launched" or "Just Tried"
2. Enable multi-select mode
3. Select games you want to play next
4. Bulk action: "Set Priority > High"
5. Sort by priority in library view

**Rate Completed Games**
1. Filter library: "Gameplay > Well Played" or "Heavily Played"
2. Open each game, rate 1-10 based on experience
3. Filter by "My Rating > Personally Rated" to see all rated games

**Organize Collections**
1. Create collections: Collections page > "New Collection"
2. In library, enable multi-select mode
3. Select related games (e.g., all roguelikes)
4. Bulk action: "Add to Collection" > Select collection

---

## Table of Contents

1. [Gameplay Tags (System Labels)](#gameplay-tags-system-labels)
2. [Auto-Tagging Mechanism](#auto-tagging-mechanism)
3. [Manual Tagging](#manual-tagging)
4. [Priority System](#priority-system)
5. [Personal Ratings](#personal-ratings)
6. [Bulk Actions (Library Page)](#bulk-actions-library-page)
7. [Quick Actions (Game Detail Page)](#quick-actions-game-detail-page)
8. [Collections Management](#collections-management)
9. [Toast Notifications](#toast-notifications)
10. [Database Schema](#database-schema)
11. [API Reference](#api-reference)
12. [Integration with Predefined Filters](#integration-with-predefined-filters)
13. [Frequently Asked Questions](#frequently-asked-questions)
14. [Source Files](#source-files)
15. [Testing](#testing)

---

## Gameplay Tags (System Labels)

### Label Definitions

Five system labels classify games by playtime. Each game receives **exactly one** gameplay tag at a time:

| Label | Icon | Color | Playtime Range | Condition |
|-------|------|-------|----------------|-----------|
| **Never Launched** | :video_game: | `#64748b` (slate) | 0 hours | `playtime_hours is None or playtime_hours == 0` |
| **Just Tried** | :eyes: | `#f59e0b` (amber) | > 0h and < 2h | `0 < playtime_hours < 2` |
| **Played** | :dart: | `#3b82f6` (blue) | 2h to < 10h | `2 <= playtime_hours < 10` |
| **Well Played** | :star: | `#8b5cf6` (violet) | 10h to < 50h | `10 <= playtime_hours < 50` |
| **Heavily Played** | :trophy: | `#10b981` (emerald) | >= 50h | `playtime_hours >= 50` |

Source: `SYSTEM_LABELS` dict in `web/services/system_labels.py`

### Boundary Values

The boundaries are **exclusive on the upper end** (half-open intervals `[lower, upper)`):

```
0h          -> Never Launched
0.1h        -> Just Tried
1.99h       -> Just Tried
2.0h        -> Played        (boundary: >= 2)
9.99h       -> Played
10.0h       -> Well Played   (boundary: >= 10)
49.99h      -> Well Played
50.0h       -> Heavily Played (boundary: >= 50)
1000h       -> Heavily Played
```

### Visual Display

**On game cards** (library page): Gameplay tag badge displayed in the top-left corner with icon and colored background.

**On game detail page**: Interactive tag pill below the game title. Shows icon + label text (e.g., ":trophy: Heavily Played") on a blue background. Click to open dropdown and change.

---

## Auto-Tagging Mechanism

### When Does Auto-Tagging Run?

Auto-tagging is triggered **automatically during Steam sync**, in three code paths:

1. **Synchronous sync** (`POST /api/sync/store/steam`):
   ```python
   # web/routes/sync.py
   results["steam"] = import_steam_games(conn)
   from ..services.system_labels import update_all_auto_labels
   update_all_auto_labels(conn)
   ```

2. **Asynchronous sync** (`POST /api/sync/store/steam/async`):
   ```python
   # web/routes/sync.py, inside run_sync() loop
   if store_name == "steam":
       from ..services.system_labels import update_all_auto_labels
       update_all_auto_labels(conn)
   ```

3. **Manual trigger** (`POST /api/labels/update-system-tags`):
   ```python
   # web/routes/api_metadata.py
   update_all_auto_labels(conn)
   ```

Both `/api/sync/store/steam` and `/api/sync/store/all` trigger auto-tagging.

### Steam-Only Restriction

Auto-tagging **only applies to Steam games** because Steam is the only store providing reliable playtime data via its API. The guard is at `web/services/system_labels.py:93`:

```python
if game["store"] != "steam" or game["playtime_hours"] is None:
    return
```

Games from other stores can receive gameplay tags **manually** (see [Manual Tagging](#manual-tagging)).

### Processing Flow

When `update_all_auto_labels(conn)` runs:

```
1. Query all Steam games with playtime data
   (WHERE store = 'steam' AND playtime_hours IS NOT NULL)
2. For each game, call update_auto_labels_for_game():
   a. Fetch the game's playtime_hours and store
   b. Skip if not Steam or playtime is NULL
   c. DELETE all existing auto system labels (WHERE auto = 1)
   d. Evaluate each SYSTEM_LABELS condition against the game's playtime
   e. INSERT the matching label into game_labels (with auto = 1)
3. Commit the transaction
```

### Auto vs Manual Labels

The `game_labels.auto` column distinguishes between automatic and manual assignments:

| `auto` value | Meaning | Behavior on sync |
|-------------|---------|------------------|
| `1` | Auto-assigned by system | Deleted and re-evaluated |
| `0` | Manually assigned by user | Never touched |

A user can manually override a system label. If a user assigns "Heavily Played" to a game with 1 hour of playtime, the manual assignment (`auto = 0`) persists even after auto-tagging runs.

### Initialization

System labels are created at application startup in `web/main.py`:

```python
def init_database():
    ensure_system_labels(conn)  # Creates/updates system labels in the labels table
```

`ensure_system_labels()` is idempotent: it migrates old French names to English and creates any missing labels.

---

## Manual Tagging

Users can manually assign gameplay tags to **any game** (including non-Steam games) via two interfaces:

### From the Game Detail Page

Click the Playtime tag pill below the game title to open a dropdown with all 5 gameplay tags + "Remove Tag". The selected tag is highlighted with a checkmark.

**Endpoint**: `POST /api/game/{game_id}/manual-playtime-tag`
**Body**: `{"label_name": "Well Played"}` or `{"label_name": null}` to remove

### From the Library (Bulk)

1. Enable multi-select mode (checkmark button, bottom-right)
2. Select one or more games (click checkboxes, or Shift-click for range selection)
3. Click "Playtime Tag" in the floating action bar
4. Choose a tag from the dropdown

**Endpoint**: `POST /api/game/{game_id}/manual-playtime-tag` (called for each selected game)

### Manual vs Auto Tag Behavior

- Setting a manual tag removes any existing auto tag and creates a `game_labels` entry with `auto = 0`
- Removing a manual tag on a Steam game allows the auto tag to reappear on next sync
- Non-Steam games only have manual tags (never auto-tagged)

---

## Priority System

Users can assign a priority level to any game to help organize their backlog.

### Priority Levels

| Priority | Icon | Color |
|----------|------|-------|
| High | :red_circle: | Red |
| Medium | :yellow_circle: | Amber |
| Low | :green_circle: | Green |
| (None) | :white_circle: | Gray |

### Database

Column `priority` (TEXT) on the `games` table. Values: `'high'`, `'medium'`, `'low'`, or `NULL`.

### Setting Priority

**From game detail page**: Click the Priority tag pill -> dropdown with 4 options. Current selection shown with blue highlight and checkmark.

**From library (bulk)**: Multi-select mode -> "Set Priority" button in action bar -> dropdown.

### Visual Display

- **Game cards**: Priority badge in top-left corner (colored emoji)
- **Game detail**: Interactive tag pill showing current priority with colored background

### Sorting

Games can be sorted by priority in the library (High -> Medium -> Low -> Unset).

---

## Personal Ratings

Users can rate any game on a 1-10 scale.

### Database

Column `personal_rating` (REAL) on the `games` table. Values: `1` to `10`, or `NULL`/`0` for unrated.

### Setting Ratings

**From game detail page**: Click the Rating tag pill -> dropdown with ratings 10 down to 1 + "Remove Rating". Each option shows star visualization.

**From library (bulk)**: Multi-select mode -> "Personal Rating" button in action bar -> dropdown.

### Star Visualization

Ratings are displayed as stars (rating / 2, rounded):
- Rating 10: :star::star::star::star::star: 10
- Rating 8: :star::star::star::star: 8
- Rating 6: :star::star::star: 6
- Rating 2: :star: 2

### Visual Display

- **Game cards**: Gold gradient badge in top-left corner with stars and number
- **Game detail**: Interactive tag pill with amber gradient background

---

## Bulk Actions (Library Page)

### Enabling Multi-Select

A floating circular button (bottom-right corner, purple gradient with checkmark) toggles multi-select mode. When enabled:

- Each game card shows a checkbox (top-left corner)
- Click checkboxes to select individual games
- **Shift-click**: Select a range of games between last click and current click
- A "Select All" link appears to select all visible games
- Selection counter shows "X selected"

### Floating Action Bar

When 1+ games are selected, a floating action bar appears at the bottom center with these actions:

| Action | Icon | Endpoint | Description |
|--------|------|----------|-------------|
| **Add to Collection** | - | `POST /api/games/bulk/add-to-collection` | Opens collection modal |
| **Set Priority** | Dropdown | `POST /api/games/bulk/set-priority` | High/Medium/Low/Remove |
| **Personal Rating** | Dropdown | `POST /api/games/bulk/set-personal-rating` | 1-10 scale + Remove |
| **Playtime Tag** | Dropdown | `POST /api/game/{id}/manual-playtime-tag` | 5 tags + Remove |
| **Hide Selected** | :eye: | `POST /api/games/bulk/hide` | Hides from library |
| **Mark NSFW** | :underage: | `POST /api/games/bulk/nsfw` | Marks as NSFW |
| **Delete Selected** | :wastebasket: | `POST /api/games/bulk/delete` | With confirmation dialog |
| **Cancel** | :x: | - | Clears selection |

### Visual Feedback

- Selected cards have a 3px purple outline
- Games fade out and scale down when hidden/deleted
- Toast notifications confirm each action with count

---

## Quick Actions (Game Detail Page)

### Tag Pills Zone

Below the game title, interactive tag pills provide one-click access to game metadata:

1. **Priority pill**: Shows current priority or ":star: Priority" placeholder. Click to open dropdown.
2. **Rating pill**: Shows stars + score or ":100: Rating" placeholder. Click to open dropdown.
3. **Playtime pill**: Shows current tag or ":video_game: Playtime" placeholder. Click to open dropdown.
4. **Collection pills**: Purple gradient pills showing each collection the game belongs to. Click to navigate to that collection.
5. **Status pills** (read-only): "Hidden" (red) and "NSFW" (orange) indicators.

### Edit Button

An "Edit..." button opens a secondary panel with additional actions:

| Action | Icon | Description |
|--------|------|-------------|
| **Collection** | :label: | Opens collection modal (toggle multiple collections) |
| **Hide/Unhide** | :eye: | Toggle hidden status |
| **Mark NSFW/SFW** | :underage: | Toggle NSFW flag |
| **Delete** | :wastebasket: | Delete game from library |

### Collection Modal (Single Game)

When opened from the game detail page, the collection modal shows:
- Checkbox list of all collections (can toggle multiple)
- Game count per collection
- "Create new collection" input + "Create & Add" button
- Real-time updates (adds/removes without page reload)

---

## Collections Management

Collections are stored as labels with `type = 'collection'` and `system = 0`.

### From Library (Bulk Add)
- Select games -> "Add to Collection" -> radio selection (one collection) -> Add
- Can create a new collection inline

### From Game Detail
- "Edit..." -> ":label: Collection" -> checkbox list (toggle multiple) -> real-time updates
- Can create a new collection and immediately add the game

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/collections` | GET | List all collections |
| `/api/collections` | POST | Create collection `{"name": "...", "description": "..."}` |
| `/api/collections/{id}` | PUT | Update collection |
| `/api/collections/{id}` | DELETE | Delete collection |
| `/api/collections/{id}/games` | POST | Add game `{"game_id": 123}` |
| `/api/collections/{id}/games/{game_id}` | DELETE | Remove game from collection |
| `/api/game/{id}/collections` | GET | Get game's collections |
| `/api/games/bulk/add-to-collection` | POST | Bulk add `{"game_ids": [...], "collection_id": 5}` |

---

## Toast Notifications

All user action feedback uses toast notifications (replacing `alert()` dialogs).

### Visual Design

- **Position**: Top-right corner, stacked vertically
- **Appearance**: Dark semi-transparent with blur, slide-in from right
- **Color-coded left border**: Green (success), Red (error), Blue (info)
- **Auto-dismiss**: After 3-5 seconds
- **Click to dismiss**: Click anywhere on the toast

### JavaScript API

```javascript
showToast(message, type, duration)
// type: 'success' | 'error' | 'info'
// duration: milliseconds (default varies by type)
```

### Examples

- "Priority high set for 5 games" (success)
- "Personal rating 8/10 set for 3 games" (success)
- "Playtime tag 'Well Played' set for 2 games" (success)
- "5 games hidden" (success)
- "Failed to set priority" (error)

---

## Database Schema

### `labels` Table

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | INTEGER PK | Auto-increment | |
| `name` | TEXT NOT NULL | | Display name |
| `description` | TEXT | | Optional description |
| `type` | TEXT | `'collection'` | `'collection'` or `'system_tag'` |
| `color` | TEXT | | Hex color code |
| `icon` | TEXT | | Emoji icon |
| `system` | INTEGER | `0` | `1` for system labels, `0` for user labels |
| `created_at` | TIMESTAMP | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | `CURRENT_TIMESTAMP` | |

### `game_labels` Junction Table

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `label_id` | INTEGER FK | | References `labels.id` (CASCADE) |
| `game_id` | INTEGER FK | | References `games.id` (CASCADE) |
| `added_at` | TIMESTAMP | `CURRENT_TIMESTAMP` | |
| `auto` | INTEGER | `0` | `1` = auto-assigned, `0` = manual |

**Primary Key**: `(label_id, game_id)`

### `games` Table (added columns)

| Column | Type | Description |
|--------|------|-------------|
| `priority` | TEXT | `'high'`, `'medium'`, `'low'`, or `NULL` |
| `personal_rating` | REAL | `1`-`10`, or `NULL`/`0` for unrated |

### Indexes

- `idx_game_labels_game_id` on `game_labels.game_id`
- `idx_game_labels_label_id` on `game_labels.label_id`
- `idx_labels_type` on `labels.type`
- `idx_labels_system` on `labels.system`

---

## API Reference

> 📖 **For complete API documentation with request/response examples, error codes, and curl commands, see [API Metadata Endpoints](api-metadata-endpoints.md)**

### Gameplay Tags

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/game/{id}/manual-playtime-tag` | POST | `{"label_name": "Well Played"}` | Set tag (or `null` to remove) |
| `/api/labels/update-system-tags` | POST | - | Re-evaluate all auto tags |

### Priority & Ratings

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/game/{id}/priority` | POST | `{"priority": "high"}` | Set priority (or `null`) |
| `/api/game/{id}/personal-rating` | POST | `{"rating": 8}` | Set rating (or `0` to remove) |
| `/api/games/bulk/set-priority` | POST | `{"game_ids": [...], "priority": "high"}` | Bulk set priority |
| `/api/games/bulk/set-personal-rating` | POST | `{"game_ids": [...], "rating": 8}` | Bulk set rating |

### Game Management

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/game/{id}/hidden` | POST | - | Toggle hidden status |
| `/api/game/{id}/nsfw` | POST | - | Toggle NSFW flag |
| `/api/game/{id}` | DELETE | - | Delete game |
| `/api/games/bulk/hide` | POST | `{"game_ids": [...]}` | Bulk hide |
| `/api/games/bulk/nsfw` | POST | `{"game_ids": [...]}` | Bulk mark NSFW |
| `/api/games/bulk/delete` | POST | `{"game_ids": [...]}` | Bulk delete |

### Sync (with auto-tagging)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/store/steam` | POST | Sync + auto-tag |
| `/api/sync/store/steam/async` | POST | Async sync + auto-tag |
| `/api/sync/store/all` | POST | Sync all stores + auto-tag Steam |
| `/api/sync/store/all/async` | POST | Async sync all + auto-tag Steam |

---

## Integration with Predefined Filters

The Gameplay filters use SQL subqueries against the labels tables:

```python
# Check if a game has a specific system tag
_TAG_EXISTS = """EXISTS (
    SELECT 1 FROM game_labels _gl JOIN labels _l ON _l.id = _gl.label_id
    WHERE _gl.game_id = games.id AND _l.system = 1 AND _l.type = 'system_tag'
    AND _l.name = '{tag_name}'
)"""
```

| Filter ID | SQL Condition | Description |
|-----------|--------------|-------------|
| `unplayed` | Steam: no tag except "Never Launched"; Other: no tag at all | Unplayed games |
| `just-tried` | `_TAG_EXISTS` for "Just Tried" | < 2h played |
| `played` | `_TAG_EXISTS` for "Played" | 2-10h played |
| `well-played` | `_TAG_EXISTS` for "Well Played" | 10-50h played |
| `heavily-played` | `_TAG_EXISTS` for "Heavily Played" | 50+ hours |

The `unplayed` filter handles Steam vs non-Steam differently:
- **Steam**: No tag other than "Never Launched" (excludes games that have been played)
- **Non-Steam**: No system tags at all (since they don't get auto-tagged)

See [Filter System documentation](filter-system.md) for the full filter architecture.

---

## Source Files

| File | Role |
|------|------|
| `web/services/system_labels.py` | Label definitions, auto-tagging logic, CRUD operations |
| `web/routes/sync.py` | Calls `update_all_auto_labels()` after Steam import |
| `web/routes/api_metadata.py` | All label/priority/rating endpoints |
| `web/routes/collections.py` | Collection CRUD and game-collection management |
| `web/utils/filters.py` | SQL templates and Gameplay filter definitions |
| `web/database.py` | Table creation for `labels` and `game_labels` |
| `web/main.py` | Calls `ensure_system_labels()` at startup |
| `web/templates/index.html` | Library page: bulk actions, multi-select, action bar |
| `web/templates/game_detail.html` | Game detail page: tag pills, quick actions, edit panel |

---

## Frequently Asked Questions

### Q: Why aren't my Epic/GOG/Xbox games auto-tagged?

**A:** Auto-tagging is **Steam-only** because only Steam provides accurate playtime tracking through the platform API. Other stores don't expose playtime data consistently.

**Solution:** Use manual playtime tags for non-Steam games:
1. Open game detail page
2. Click the "Playtime: -" pill
3. Select appropriate tag (Never Launched, Just Tried, etc.)

Manual tags persist and won't be overwritten by auto-tagging.

---

### Q: Can I change the playtime boundaries (e.g., make "Played" 5-15h instead of 2-10h)?

**A:** No, boundaries are hard-coded in `web/services/system_labels.py` in the `SYSTEM_LABELS` dictionary. Changing them requires:

1. Editing the source code
2. Restarting the application
3. Running manual system tag update: `POST /api/labels/update-system-tags`

However, you can **override** auto-tags with manual tags on a per-game basis:
- Open game detail page
- Click playtime tag pill
- Select different tag manually

This gives you flexibility without modifying code.

---

### Q: What happens if I delete a system label (e.g., "Well Played")?

**A:** **Don't do this!** Deleting system labels will break auto-tagging and cause errors.

**What breaks:**
- Auto-tagging will fail to assign labels for games in that playtime range
- Existing games with that label will lose the association (if CASCADE delete is configured)
- Filters relying on that label will return incorrect results

**Recovery:**
1. Restart the application (runs `ensure_system_labels()` which recreates missing labels)
2. Run manual system tag update: `POST /api/labels/update-system-tags`

**Protection:** System labels have `system = 1` flag. The UI should prevent deletion of system labels (user can only delete `system = 0` collections).

---

### Q: Do manual tags get overwritten when I sync Steam?

**A:** No! Manual tags (`auto = 0`) are **never** overwritten by auto-tagging.

**How it works:**
- Auto-tagging only deletes and re-inserts labels where `auto = 1`
- Manual tags have `auto = 0` and are skipped during auto-tagging
- If you manually override a game's playtime tag, it won't change on next sync

**Example:**
1. Steam game has 100h (auto-tags as "Heavily Played")
2. You manually change to "Just Tried" (sets `auto = 0`)
3. Next Steam sync runs → Your "Just Tried" tag persists

To allow auto-tagging again, remove the manual tag:
- Click playtime pill → Select "Remove Tag"

---

### Q: How do I bulk-unrate games (remove all ratings)?

**A:** Use the bulk rating endpoint with `rating = 0`:

1. **UI Method:**
   - Enable multi-select mode (☑ button)
   - Select games with ratings
   - Bulk action: "Personal Rating" → "Remove Rating" (0 stars)

2. **API Method:**
   ```bash
   curl -X POST http://localhost:5050/api/games/bulk/set-personal-rating \
     -H "Content-Type: application/json" \
     -d '{"game_ids": [123, 456, 789], "rating": 0}'
   ```

Rating `0` sets `personal_rating` to `NULL` in the database.

---

### Q: Can a game have multiple playtime tags?

**A:** No, each game has **exactly one** playtime tag at a time (or none).

**Why:** Playtime is a single numeric value, so only one tag applies. The system:
1. Deletes existing playtime tags (system labels with `system = 1`)
2. Inserts the single appropriate tag based on current playtime

**Multiple labels:** Games can have multiple **collection** labels (user-created, `type = 'collection'`) but only one **system tag** (`type = 'system_tag'`).

---

### Q: How do I see all games with a specific priority?

**A:** Use the filter system:

1. **UI Method:**
   - Library page → Filter sidebar
   - "My Rating" category → "Has Priority"
   - (Note: Currently filters by existence, not specific priority level)

2. **API Method:**
   Query games with priority:
   ```sql
   SELECT * FROM games WHERE priority = 'high';
   ```

3. **Advanced:** Create a custom filter in `web/utils/filters.py` for specific priorities.

---

### Q: What happens to collections when migrating from old system?

**A:** The `migrate_collections_to_labels()` function automatically:

1. Copies all `collections` → `labels` with `type = 'collection'`
2. Copies all `collection_games` → `game_labels` with `auto = 0`
3. Drops old `collections` and `collection_games` tables
4. Preserves all timestamps and associations

**Migration is automatic** on first startup after upgrading. No manual action needed.

**Data preserved:**
- Collection names and descriptions
- Game-collection associations
- Created/updated timestamps

**New fields:**
- `type` = 'collection' (distinguishes from system tags)
- `icon`, `color` (NULL for migrated collections, can be set later)
- `system` = 0 (user-created)

---

### Q: How fast is auto-tagging for large libraries?

**A:** Performance depends on library size:

- **Small (<100 games):** Instant (<0.1s)
- **Medium (100-1000 games):** 0.5-2 seconds
- **Large (1000-5000 games):** 2-10 seconds
- **Very Large (>5000 games):** 10-30 seconds

**Optimization:**
- Batch processing (`update_all_auto_labels()`) is ~10x faster than individual
- Uses single transaction for atomic updates
- Indexes on `game_labels.game_id` and `label_id` accelerate queries

**Measuring performance:**
Run the test suite:
```bash
pytest tests/test_edge_cases_labels.py::test_large_library_performance -v
```

---

### Q: Can I use labels/tags in custom filters?

**A:** Yes! The filter system supports SQL subqueries against labels.

**Example filter** (in `web/utils/filters.py`):
```python
{
    "name": "Has Priority",
    "sql": "g.priority IS NOT NULL",
    "category": "My Rating"
}
```

**Advanced example** (games with specific tag):
```python
{
    "name": "Well Played Games",
    "sql": """EXISTS (
        SELECT 1 FROM game_labels gl
        JOIN labels l ON l.id = gl.label_id
        WHERE gl.game_id = g.id
          AND l.name = 'Well Played'
          AND l.system = 1
    )""",
    "category": "Gameplay"
}
```

See [Filter System](filter-system.md) for more examples.

---

### Q: What keyboard shortcuts are available in multi-select mode?

**A:** The following shortcuts work in the library page when multi-select mode is enabled:

| Shortcut | Action |
|----------|--------|
| Click checkbox | Toggle single game selection |
| Shift + Click | Select range from last clicked to current |
| Click action button | Apply action to all selected games |
| Esc | Cancel multi-select mode (UI convention, may not be implemented) |

**Range selection example:**
1. Check game #5
2. Hold Shift, check game #12
3. → Games 5-12 are now all selected

**Future enhancements** (not yet implemented):
- Ctrl+A: Select all visible games
- Ctrl+Click: Add to selection without range
- Up/Down arrows: Navigate selection

---

## Testing

### Test File: `tests/test_system_labels_auto_tagging.py`

11 tests covering the auto-tagging system:

| Test | Description |
|------|-------------|
| `test_ensure_system_labels_creates_all_labels` | All 5 system labels are created |
| `test_update_auto_labels_never_launched` | 0h -> Never Launched |
| `test_update_auto_labels_just_tried` | 1.5h -> Just Tried |
| `test_update_auto_labels_played` | 5h -> Played |
| `test_update_auto_labels_well_played` | 25h -> Well Played |
| `test_update_auto_labels_heavily_played` | 100h -> Heavily Played |
| `test_update_auto_labels_only_steam_games` | Non-Steam games are skipped |
| `test_update_auto_labels_ignores_null_playtime` | NULL playtime is skipped |
| `test_update_all_auto_labels` | Batch update processes all Steam games |
| `test_update_auto_labels_replaces_old_labels` | Playtime change updates label |
| `test_boundary_values` | All boundary points (0, 0.1, 1.9, 2.0, 9.9, 10.0, 49.9, 50.0) |

Run with:
```bash
pytest tests/test_system_labels_auto_tagging.py -v
```

---

## Migration Notes

System labels were originally named in French and migrated to English via `ensure_system_labels()`:

| Old (French) | New (English) |
|-------------|---------------|
| Jamais lance | Never Launched |
| Juste essaye | Just Tried |
| Joue | Played |
| Bien joue | Well Played |
| Beaucoup joue | Heavily Played |
