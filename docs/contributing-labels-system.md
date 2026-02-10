# Contributing to the Labels System

This guide explains the architecture and extension points of the Backlogia labels system for developers who want to contribute new features or modify existing behavior.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Understanding the `auto` Column](#understanding-the-auto-column)
3. [Adding a New System Label](#adding-a-new-system-label)
4. [Adding a New Metadata Field](#adding-a-new-metadata-field)
5. [Performance Considerations](#performance-considerations)
6. [Migration Best Practices](#migration-best-practices)
7. [Testing Guidelines](#testing-guidelines)

---

## System Architecture

### Database Schema Overview

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│     games        │         │   game_labels    │         │     labels       │
├──────────────────┤         ├──────────────────┤         ├──────────────────┤
│ id (PK)          │◄────────┤ game_id (FK)     │         │ id (PK)          │
│ name             │         │ label_id (FK)    ├────────►│ name             │
│ store            │         │ added_at         │         │ type             │
│ playtime_hours   │         │ auto             │         │ icon             │
│ priority         │         │                  │         │ color            │
│ personal_rating  │         │ PK: (game_id,    │         │ system           │
│ ...              │         │      label_id)   │         │ ...              │
└──────────────────┘         └──────────────────┘         └──────────────────┘

                                     │
                                     │ auto = 0 (manual)
                                     │ auto = 1 (automatic)
                                     ▼

               ┌──────────────────────────────────────┐
               │  auto = 0: User-created, persists    │
               │  auto = 1: System-managed, replaced  │
               └──────────────────────────────────────┘
```

### Label Types

| `type` | `system` | Description | Example |
|--------|----------|-------------|---------|
| `collection` | `0` | User-created collection | "Favorites", "Backlog" |
| `collection` | `1` | (Reserved for future system collections) | - |
| `system_tag` | `1` | Auto-assigned gameplay tag | "Well Played" |

### Key Components

```
web/
├── services/
│   └── system_labels.py          # Core auto-tagging logic
├── routes/
│   ├── sync.py                   # Triggers auto-tagging after Steam sync
│   ├── api_metadata.py           # Priority, ratings, manual tags endpoints
│   └── collections.py            # Collection CRUD operations
├── utils/
│   └── filters.py                # Filter definitions using label queries
├── database.py                   # Migrations and schema management
└── main.py                       # App startup (ensure_system_labels)
```

---

## Understanding the `auto` Column

The `auto` column in `game_labels` is the cornerstone of the system's flexibility.

### Lifecycle of an Auto Tag

```
1. Steam Sync
   │
   ▼
2. Game has playtime_hours = 25.0
   │
   ▼
3. update_auto_labels_for_game(conn, game_id)
   │
   ├─► DELETE FROM game_labels WHERE game_id = ? AND auto = 1
   │   (Removes old auto tags, preserves manual tags with auto = 0)
   │
   ├─► Evaluate playtime against SYSTEM_LABELS conditions
   │   → 25h matches "Well Played" (10 ≤ playtime < 50)
   │
   └─► INSERT INTO game_labels (label_id, game_id, auto)
       VALUES (label_id_of_well_played, game_id, 1)
   
   Result: Game now has "Well Played" tag with auto = 1
```

### Manual Tag Override

```
User Action: Manually set "Just Tried" tag on game with 25h
   │
   ▼
1. DELETE FROM game_labels WHERE game_id = ? AND label_id IN (system_labels)
   (Removes ALL playtime tags, both auto and manual)
   │
   ▼
2. INSERT INTO game_labels (label_id, game_id, auto)
   VALUES (label_id_of_just_tried, game_id, 0)
   │
   ▼
Result: Game has "Just Tried" tag with auto = 0

Next Steam Sync:
   │
   ▼
update_auto_labels_for_game(conn, game_id)
   │
   ├─► DELETE FROM game_labels WHERE game_id = ? AND auto = 1
   │   (Query finds no rows to delete, manual tag has auto = 0)
   │
   └─► Skip INSERT because game is not steam or has existing manual tag
       (Logic checks for existing system tags before inserting)

Result: Manual "Just Tried" tag persists!
```

### Key Insight

**Manual tags survive because:**
1. DELETE query filters by `auto = 1` (only removes auto tags)
2. INSERT logic checks if a system tag already exists before adding
3. Manual tags block auto-tagging for that game

---

## Adding a New System Label

Let's add a hypothetical "Marathon" label for games with 200+ hours.

### Step 1: Update `SYSTEM_LABELS` Dictionary

**File:** `web/services/system_labels.py`

```python
SYSTEM_LABELS = {
    # ... existing labels ...
    "heavily-played": {
        "name": "Heavily Played",
        "icon": "🏆",
        "color": "#10b981",
        "condition": lambda game: game["playtime_hours"] is not None and 50 <= game["playtime_hours"] < 200  # Changed upper bound
    },
    "marathon": {  # NEW LABEL
        "name": "Marathon",
        "icon": "🔥",
        "color": "#dc2626",  # Red color for extreme playtime
        "condition": lambda game: game["playtime_hours"] is not None and game["playtime_hours"] >= 200
    }
}
```

**Important:** Adjust boundaries of existing labels to avoid overlaps (e.g., "Heavily Played" now stops at 200h).

### Step 2: Run Ensure System Labels

On next app startup, `ensure_system_labels(conn)` will automatically:
1. Detect new label in `SYSTEM_LABELS`
2. Insert into database with `system = 1`

No manual database migration needed!

### Step 3: Update Filter Definitions

**File:** `web/utils/filters.py`

Add a new filter to the "Gameplay" category:

```python
PREDEFINED_FILTERS = {
    # ... existing filters ...
    "marathon": {
        "name": "Marathon",
        "category": "Gameplay",
        "sql": _TAG_EXISTS.format(tag_name='Marathon'),
        "description": "Games played for 200+ hours"
    }
}
```

### Step 4: Update Frontend (Optional)

**File:** `web/templates/game_detail.html`

Add "Marathon" to the playtime tag dropdown:

```html
<select id="playtimeTagSelect-{{ game.id }}">
    <option value="">Remove Tag</option>
    <option value="Never Launched">🎮 Never Launched</option>
    <option value="Just Tried">👀 Just Tried</option>
    <option value="Played">🎯 Played</option>
    <option value="Well Played">⭐ Well Played</option>
    <option value="Heavily Played">🏆 Heavily Played</option>
    <option value="Marathon">🔥 Marathon</option>  <!-- NEW -->
</select>
```

### Step 5: Add Tests

**File:** `tests/test_system_labels_auto_tagging.py`

```python
def test_update_auto_labels_marathon(test_db_with_labels):
    """Test 200+ hours gets Marathon label"""
    cursor = test_db_with_labels.cursor()
    
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Marathon Game", "steam", 250.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))
    
    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Marathon']


def test_boundary_heavily_played_marathon(test_db_with_labels):
    """Test boundary between Heavily Played and Marathon"""
    cursor = test_db_with_labels.cursor()
    
    # Just under Marathon threshold
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Just Below", "steam", 199.9))
    game_id_below = cursor.lastrowid
    
    # Exactly at Marathon threshold
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Exactly 200", "steam", 200.0))
    game_id_exact = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id_below)
    update_auto_labels_for_game(test_db_with_labels, game_id_exact)

    # Verify 199.9h gets Heavily Played
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id_below,))
    assert cursor.fetchone()[0] == 'Heavily Played'

    # Verify 200h gets Marathon
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id_exact,))
    assert cursor.fetchone()[0] == 'Marathon'
```

### Step 6: Update Documentation

Add "Marathon" to the table in [docs/system-labels-auto-tagging.md](system-labels-auto-tagging.md#gameplay-tags-system-labels):

```markdown
| **Marathon** | :fire: | `#dc2626` (red) | >= 200h | `playtime_hours >= 200` |
```

### Step 7: Trigger Re-tagging

After deploying, run:

```bash
curl -X POST http://localhost:5050/api/labels/update-system-tags
```

This re-evaluates all games against the new boundaries.

---

## Adding a New Metadata Field

Let's add a hypothetical "completion_status" field (e.g., "not_started", "in_progress", "completed", "abandoned").

### Step 1: Add Database Column

**File:** `web/database.py`

Create a new migration function:

```python
def ensure_completion_status_column():
    """Add completion_status column to games table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check if games table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if not cursor.fetchone():
        conn.close()
        return

    # Check if column exists
    cursor.execute("PRAGMA table_info(games)")
    columns = {row[1] for row in cursor.fetchall()}

    if "completion_status" not in columns:
        cursor.execute("""
            ALTER TABLE games ADD COLUMN completion_status TEXT
            CHECK(completion_status IN ('not_started', 'in_progress', 'completed', 'abandoned', NULL))
        """)
        print("[OK] Added completion_status column to games table")

    conn.commit()
    conn.close()
```

**Important:** Use a CHECK constraint to enforce valid values at the database level.

### Step 2: Call Migration at Startup

**File:** `web/main.py`

```python
def init_database():
    """Initialize the database and ensure all tables/columns exist."""
    create_database()
    ensure_extra_columns()
    migrate_collections_to_labels()
    ensure_labels_tables()
    ensure_game_metadata_columns()
    ensure_completion_status_column()  # NEW
    # ...
```

### Step 3: Add API Endpoint

**File:** `web/routes/api_metadata.py`

```python
class UpdateCompletionStatusRequest(BaseModel):
    status: Optional[str] = None  # 'not_started', 'in_progress', 'completed', 'abandoned', or None


@router.post("/api/game/{game_id}/completion-status")
def set_game_completion_status(game_id: int, body: UpdateCompletionStatusRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Set completion status for a game."""
    status = body.status

    # Validate status value
    valid_statuses = ('not_started', 'in_progress', 'completed', 'abandoned')
    if status is not None and status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses} or null")

    cursor = conn.cursor()

    # Check if game exists
    cursor.execute("SELECT name FROM games WHERE id = ?", (game_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Game not found")

    # Update status
    cursor.execute("UPDATE games SET completion_status = ? WHERE id = ?", (status, game_id))
    conn.commit()

    return {"success": True, "completion_status": status}
```

### Step 4: Add Filters

**File:** `web/utils/filters.py`

```python
PREDEFINED_FILTERS = {
    # ...
    "completed-games": {
        "name": "Completed Games",
        "category": "My Progress",
        "sql": "g.completion_status = 'completed'",
        "description": "Games marked as completed"
    },
    "in-progress": {
        "name": "In Progress",
        "category": "My Progress",
        "sql": "g.completion_status = 'in_progress'",
        "description": "Games currently being played"
    },
    "abandoned": {
        "name": "Abandoned",
        "category": "My Progress",
        "sql": "g.completion_status = 'abandoned'",
        "description": "Games stopped playing"
    }
}
```

### Step 5: Add Tests

**File:** `tests/test_api_metadata_endpoints.py`

```python
def test_set_completion_status_valid(client):
    """Test setting completion status with valid values"""
    for status in ['not_started', 'in_progress', 'completed', 'abandoned']:
        response = client.post("/api/game/1/completion-status", json={"status": status})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["completion_status"] == status


def test_set_completion_status_invalid_value(client):
    """Test invalid status value returns 400"""
    response = client.post("/api/game/1/completion-status", json={"status": "invalid"})
    assert response.status_code == 400
    assert "Status must be" in response.json()["detail"]
```

---

## Performance Considerations

### Auto-Tagging Performance

**Bottlenecks:**
1. Database I/O for label lookups
2. Row-by-row processing in `update_all_auto_labels()`
3. Transaction commit frequency

**Optimizations:**

#### 1. Batch Processing with Single Transaction

```python
def update_all_auto_labels(conn):
    """Update auto labels for all Steam games in a single transaction."""
    cursor = conn.cursor()
    
    # Single query to get all Steam games
    cursor.execute("""
        SELECT id, playtime_hours FROM games WHERE store = 'steam'
    """)
    steam_games = cursor.fetchall()
    
    # Batch delete old auto tags
    game_ids = [game["id"] for game in steam_games]
    placeholders = ",".join("?" * len(game_ids))
    cursor.execute(f"""
        DELETE FROM game_labels
        WHERE game_id IN ({placeholders}) AND auto = 1
        AND label_id IN (SELECT id FROM labels WHERE system = 1)
    """, game_ids)
    
    # Batch insert new tags
    inserts = []
    for game in steam_games:
        label_id = _get_label_id_for_playtime(conn, game["playtime_hours"])
        if label_id:
            inserts.append((label_id, game["id"]))
    
    cursor.executemany("""
        INSERT INTO game_labels (label_id, game_id, auto)
        VALUES (?, ?, 1)
    """, inserts)
    
    conn.commit()  # Single commit
```

#### 2. Index Optimization

Ensure these indexes exist (already configured):

```sql
CREATE INDEX idx_game_labels_game_id ON game_labels(game_id);
CREATE INDEX idx_game_labels_label_id ON game_labels(label_id);
CREATE INDEX idx_labels_system ON labels(system);
CREATE INDEX idx_games_store ON games(store);  -- NEW for filtering Steam games
```

#### 3. Caching Label IDs

```python
# At module level or in a cache
_LABEL_ID_CACHE = {}

def _get_label_id_cached(conn, label_name):
    """Get label ID with caching to avoid repeated queries."""
    if label_name not in _LABEL_ID_CACHE:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM labels WHERE name = ? AND system = 1", (label_name,))
        row = cursor.fetchone()
        _LABEL_ID_CACHE[label_name] = row[0] if row else None
    return _LABEL_ID_CACHE[label_name]
```

### Expected Performance

| Library Size | Execution Time | Games/Second |
|--------------|----------------|--------------|
| 100 games | < 0.1s | 1000+ |
| 1,000 games | 0.5-1s | 1000-2000 |
| 5,000 games | 2-5s | 1000-2500 |
| 10,000 games | 5-10s | 1000-2000 |

**Target:** Sub-10 second auto-tagging for libraries up to 10,000 games.

---

## Migration Best Practices

### Idempotency

**Always check if migration is needed before executing:**

```python
def ensure_new_field():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if already migrated
    cursor.execute("PRAGMA table_info(games)")
    columns = {row[1] for row in cursor.fetchall()}
    
    if "new_field" in columns:
        conn.close()
        return  # Already migrated, skip
    
    # Perform migration
    cursor.execute("ALTER TABLE games ADD COLUMN new_field TEXT")
    conn.commit()
    conn.close()
```

### Testing with Production Data

**Before deploying:**

1. **Backup production database:**
   ```bash
   cp data/backlogia.db data/backlogia_backup_$(date +%Y%m%d).db
   ```

2. **Test migration on copy:**
   ```python
   import shutil
   shutil.copy("data/backlogia.db", "data/test_migration.db")
   DATABASE_PATH = "data/test_migration.db"
   ensure_new_migration()
   ```

3. **Verify results:**
   ```sql
   SELECT COUNT(*) FROM games WHERE new_field IS NOT NULL;
   ```

### Rollback Procedure

**Document how to undo migrations:**

```python
def rollback_new_field():
    """Rollback new_field addition (for testing only)."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # SQLite doesn't support DROP COLUMN before 3.35.0
    # Workaround: Create new table without column, copy data, rename
    
    cursor.execute("PRAGMA table_info(games)")
    columns = [row[1] for row in cursor.fetchall() if row[1] != 'new_field']
    columns_str = ", ".join(columns)
    
    cursor.execute(f"""
        CREATE TABLE games_new AS
        SELECT {columns_str} FROM games
    """)
    cursor.execute("DROP TABLE games")
    cursor.execute("ALTER TABLE games_new RENAME TO games")
    
    conn.commit()
    conn.close()
```

### Migration Checklist

- [ ] Migration function is idempotent (can run multiple times safely)
- [ ] CHECK constraints enforce data integrity
- [ ] Migration tested on production database copy
- [ ] Rollback procedure documented
- [ ] Migration runs at app startup (`web/main.py`)
- [ ] Database schema documentation updated
- [ ] Tests cover new field/migration
- [ ] Performance impact assessed (for large tables)

---

## Testing Guidelines

### Test Coverage Requirements

**Minimum coverage for new features:**

- **Unit tests:** Core logic functions (e.g., label assignment conditions)
- **Integration tests:** API endpoints with FastAPI TestClient
- **Database tests:** Migrations and constraints
- **Edge cases:** Boundary values, NULL handling, concurrent updates

### Test Structure

**Follow existing patterns in `tests/` directory:**

```python
# tests/test_new_feature.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3


@pytest.fixture
def test_db():
    """Create in-memory database with schema"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create tables...
    yield conn
    conn.close()


def test_feature_success_case(test_db):
    """Test feature with valid input"""
    # Arrange: Set up data
    # Act: Call function
    # Assert: Verify results
    pass


def test_feature_failure_case(test_db):
    """Test feature with invalid input"""
    # Assert error handling
    pass
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_system_labels_auto_tagging.py -v

# Run specific test
pytest tests/test_system_labels_auto_tagging.py::test_boundary_values -v

# Run with coverage
pytest tests/ --cov=web --cov-report=html
```

### Performance Testing

**Add benchmarks for potentially slow operations:**

```python
import time

def test_bulk_tagging_performance(test_db):
    """Ensure bulk tagging completes in reasonable time"""
    # Insert 1000 games
    for i in range(1000):
        cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, 'steam', ?)",
                      (f"Game {i}", i * 0.05))
    test_db.commit()
    
    # Time bulk tagging
    start = time.time()
    update_all_auto_labels(test_db)
    elapsed = time.time() - start
    
    # Assert performance threshold
    assert elapsed < 5.0, f"Tagging took {elapsed:.2f}s, expected < 5s"
```

---

## Additional Resources

- [Labels & Auto-Tagging User Guide](system-labels-auto-tagging.md)
- [API Metadata Endpoints](api-metadata-endpoints.md)
- [Database Schema](database-schema.md)
- [Filter System Reference](filter-system.md)

---

## Getting Help

**Before opening an issue:**

1. Check existing documentation (this guide + user docs)
2. Review test files for usage examples
3. Search existing GitHub issues

**When reporting bugs:**

- Include Backlogia version and database size
- Provide minimal reproduction steps
- Attach relevant logs and error messages

**For feature requests:**

- Explain use case and user benefit
- Propose API design (if adding endpoint)
- Consider backward compatibility
