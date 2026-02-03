# Database Schema Documentation

## Overview

Backlogia uses SQLite as its database engine. The database consolidates game libraries from multiple stores (Steam, Epic, GOG, itch.io, Humble Bundle, Battle.net, EA, Amazon Games, Xbox, and local folders) into a centralized location.

**Database Path**: Configured via `DATABASE_PATH` in `config.py`

## Tables

### 1. games

The main table storing all games from all sources.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Primary key, auto-incremented |
| `name` | TEXT | No | Game title |
| `store` | TEXT | No | Source store (steam, epic, gog, itch, humble, battlenet, ea, amazon, xbox, local, ubisoft) |
| `store_id` | TEXT | Yes | Unique identifier from the source store |
| `description` | TEXT | Yes | Game description/summary |
| `developers` | TEXT | Yes | JSON array of developer names |
| `publishers` | TEXT | Yes | JSON array of publisher names |
| `genres` | TEXT | Yes | JSON array of genre/theme tags |
| `cover_image` | TEXT | Yes | URL or path to cover/box art image |
| `background_image` | TEXT | Yes | URL or path to background/hero image |
| `icon` | TEXT | Yes | URL or path to icon/logo image |
| `supported_platforms` | TEXT | Yes | JSON array of platform names (Windows, Mac, Linux, Android, etc.) |
| `release_date` | TEXT | Yes | Release date in ISO format or timestamp |
| `created_date` | TEXT | Yes | Creation date from store |
| `last_modified` | TEXT | Yes | Last modification date from store |
| `playtime_hours` | REAL | Yes | Total hours played (Steam only) |
| `critics_score` | REAL | Yes | Critic/user score from store (0-100 scale) |
| `average_rating` | REAL | Yes | Computed average across all available ratings (0-100 scale) |
| `can_run_offline` | BOOLEAN | Yes | Whether game can run without internet connection |
| `dlcs` | TEXT | Yes | JSON array of DLC information |
| `extra_data` | TEXT | Yes | JSON object for store-specific additional data |
| `added_at` | TIMESTAMP | No | When the game was first added to database (default: current timestamp) |
| `updated_at` | TIMESTAMP | No | When the game was last updated (default: current timestamp) |
| `hidden` | BOOLEAN | Yes | User flag to hide game from main views (default: 0) |
| `nsfw` | BOOLEAN | Yes | User flag to mark game as NSFW (default: 0) |
| `cover_url_override` | TEXT | Yes | User-specified cover image URL override |
| `igdb_id` | TEXT | Yes | IGDB identifier for the game |
| `igdb_rating` | REAL | Yes | IGDB rating (0-100 scale) |
| `aggregated_rating` | REAL | Yes | IGDB aggregated rating (0-100 scale) |
| `total_rating` | REAL | Yes | IGDB total rating (0-100 scale) |
| `metacritic_score` | REAL | Yes | Metacritic critic score (0-100 scale) |
| `metacritic_user_score` | REAL | Yes | Metacritic user score (0-10 scale) |
| `metacritic_url` | TEXT | Yes | URL to Metacritic page |
| `protondb_tier` | TEXT | Yes | ProtonDB compatibility tier (platinum, gold, silver, bronze, borked) |
| `protondb_score` | REAL | Yes | ProtonDB score (0-100 scale) |
| `ubisoft_id` | TEXT | Yes | Ubisoft Connect game identifier |

**Indexes:**
- `idx_games_store` on `store`
- `idx_games_name` on `name`

**Unique Constraint:** `(store, store_id)` - ensures no duplicate games per store

#### Average Rating Calculation

The `average_rating` column is computed from all available rating sources:
- `critics_score` (Steam reviews, 0-100)
- `igdb_rating` (IGDB rating, 0-100)
- `aggregated_rating` (IGDB aggregated, 0-100)
- `total_rating` (IGDB total, 0-100)
- `metacritic_score` (Metacritic critics, 0-100)
- `metacritic_user_score` (Metacritic users, normalized from 0-10 to 0-100)

All ratings are normalized to a 0-100 scale, then averaged. Returns `None` if no ratings are available.

### 2. collections

User-created game collections for organizing games.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Primary key, auto-incremented |
| `name` | TEXT | No | Collection name |
| `description` | TEXT | Yes | Collection description |
| `created_at` | TIMESTAMP | No | When the collection was created (default: current timestamp) |
| `updated_at` | TIMESTAMP | No | When the collection was last modified (default: current timestamp) |

### 3. collection_games

Junction table linking games to collections (many-to-many relationship).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `collection_id` | INTEGER | No | Foreign key to collections.id (CASCADE on delete) |
| `game_id` | INTEGER | No | Foreign key to games.id (CASCADE on delete) |
| `added_at` | TIMESTAMP | No | When the game was added to collection (default: current timestamp) |

**Primary Key:** `(collection_id, game_id)`

**Foreign Keys:**
- `collection_id` → `collections(id)` ON DELETE CASCADE
- `game_id` → `games(id)` ON DELETE CASCADE

### 4. settings

Application settings storage (key-value pairs).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `key` | TEXT | No | Setting key (primary key) |
| `value` | TEXT | Yes | Setting value (stored as text, JSON for complex values) |
| `updated_at` | TIMESTAMP | No | When the setting was last updated (default: current timestamp) |

## Store-Specific Data

### Steam
- `store_id`: Steam AppID
- `cover_image`: `https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg`
- `background_image`: `https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_hero.jpg`
- `playtime_hours`: Total playtime
- `critics_score`: User review score (percentage)

### Epic Games Store
- `store_id`: Epic app_name
- `can_run_offline`: Offline capability
- `dlcs`: List of DLCs

### GOG
- `store_id`: GOG product_id
- `genres`: Combined genres and themes (deduplicated, case-insensitive)
- `release_date`: Unix timestamp converted to ISO format

### itch.io
- `store_id`: itch.io game ID
- `supported_platforms`: Built from platform flags (windows, mac, linux, android)

### Humble Bundle
- `store_id`: Humble machine_name
- `publishers`: Contains payee information

### Battle.net
- `store_id`: Blizzard title_id
- `extra_data`: Contains raw Battle.net data

### EA
- `store_id`: EA offer_id

### Amazon Games
- `store_id`: Amazon product_id

### Xbox
- `store_id`: Xbox store ID
- `extra_data`: Contains:
  - `is_streaming`: Whether it's a cloud streaming game
  - `acquisition_type`: How the game was acquired
  - `title_id`: Xbox title ID
  - `pfn`: Package family name

### Local
- `store_id`: Generated from folder path
- `extra_data`: Contains:
  - `folder_path`: Path to game folder
  - `manual_igdb_id`: User-specified IGDB ID for metadata matching

### Ubisoft Connect
- `store_id`: Ubisoft game ID
- `ubisoft_id`: Alternative Ubisoft identifier

## Database Connection

The `database.py` module provides:
- `get_db()`: Returns a connection with `row_factory = sqlite3.Row` for dict-like access

## Migration Functions

The following functions handle database schema migrations:

- `ensure_extra_columns()`: Adds `hidden`, `nsfw`, and `cover_url_override` columns
- `ensure_collections_tables()`: Creates `collections` and `collection_games` tables
- `add_average_rating_column()`: Adds `average_rating` column

## Import Pipeline

The `database_builder.py` module contains functions to import games from each store:

1. `create_database()`: Initialize all tables and indexes
2. `import_steam_games(conn)`
3. `import_epic_games(conn)`
4. `import_gog_games(conn)`
5. `import_itch_games(conn)`
6. `import_humble_games(conn)`
7. `import_battlenet_games(conn)`
8. `import_ea_games(conn)`
9. `import_amazon_games(conn)`
10. `import_xbox_games(conn)`
11. `import_local_games(conn)`

Each import function:
- Returns the count of imported games
- Uses `ON CONFLICT(store, store_id) DO UPDATE` to handle duplicates
- Updates the `updated_at` timestamp
- Prints progress messages with `[OK]` style indicators

## Utility Functions

### Rating Management

```python
calculate_average_rating(
    critics_score=None,
    igdb_rating=None,
    aggregated_rating=None,
    total_rating=None,
    metacritic_score=None,
    metacritic_user_score=None
) -> float | None
```

Computes average rating from available sources (0-100 scale).

```python
update_average_rating(conn, game_id) -> float | None
```

Updates the `average_rating` for a specific game by fetching all rating fields and computing the average.

### Statistics

```python
get_stats(conn) -> dict
```

Returns:
```json
{
  "total": 1234,
  "by_store": {
    "steam": 500,
    "epic": 200,
    "gog": 300,
    ...
  }
}
```

## JSON Fields

Several columns store JSON arrays or objects as TEXT:

- `developers`: `["Studio A", "Studio B"]`
- `publishers`: `["Publisher A"]`
- `genres`: `["Action", "RPG", "Adventure"]`
- `supported_platforms`: `["Windows", "Linux"]`
- `dlcs`: Array of DLC objects
- `extra_data`: Store-specific additional information

Always use `json.loads()` and `json.dumps()` when reading/writing these fields.

## Best Practices

1. **Always use parameterized queries** to prevent SQL injection
2. **Commit after batch operations** for performance
3. **Handle exceptions per-game** during imports to avoid losing entire batch
4. **Update `updated_at`** whenever modifying game records
5. **Call `update_average_rating()`** after updating any rating field
6. **Use `get_db()`** for row factory access to treat rows as dictionaries
7. **Run migration functions** (`ensure_extra_columns()`, `ensure_collections_tables()`) on startup

## Error Handling

Import functions print errors but continue processing:
```python
try:
    # import game
except Exception as e:
    print(f"  Error importing {game.get('name')}: {e}")
```

This ensures one failing game doesn't block the entire import process.

## Example Queries

### Get all games from a specific store
```python
cursor.execute("SELECT * FROM games WHERE store = ?", ("steam",))
```

### Get games with ratings above 80
```python
cursor.execute("SELECT * FROM games WHERE average_rating >= 80 ORDER BY average_rating DESC")
```

### Get games in a collection
```python
cursor.execute("""
    SELECT g.* FROM games g
    JOIN collection_games cg ON g.id = cg.game_id
    WHERE cg.collection_id = ?
""", (collection_id,))
```

### Search games by name
```python
cursor.execute("SELECT * FROM games WHERE name LIKE ? ORDER BY name", (f"%{search_term}%",))
```

### Get hidden/NSFW games
```python
cursor.execute("SELECT * FROM games WHERE hidden = 1")
cursor.execute("SELECT * FROM games WHERE nsfw = 1")
```
