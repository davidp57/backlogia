# API Metadata Endpoints

This document describes all API endpoints for managing game metadata, including priority, personal ratings, manual playtime tags, and bulk operations.

## Table of Contents

1. [Single Game Operations](#single-game-operations)
   - [Set Game Priority](#set-game-priority)
   - [Set Personal Rating](#set-personal-rating)
   - [Set Manual Playtime Tag](#set-manual-playtime-tag)
   - [Toggle Hidden Status](#toggle-hidden-status)
   - [Toggle NSFW Status](#toggle-nsfw-status)
   - [Delete Game](#delete-game)
2. [Bulk Operations](#bulk-operations)
   - [Bulk Set Priority](#bulk-set-priority)
   - [Bulk Set Personal Rating](#bulk-set-personal-rating)
   - [Bulk Hide Games](#bulk-hide-games)
   - [Bulk Mark NSFW](#bulk-mark-nsfw)
   - [Bulk Delete Games](#bulk-delete-games)
   - [Bulk Add to Collection](#bulk-add-to-collection)
3. [System Operations](#system-operations)
   - [Update System Tags](#update-system-tags)
4. [Error Codes](#error-codes)

---

## Single Game Operations

### Set Game Priority

Set or clear the priority level for a game.

**Endpoint:** `POST /api/game/{game_id}/priority`

**Request Body:**
```json
{
  "priority": "high"
}
```

**Valid Priority Values:**
- `"high"` - High priority (red badge)
- `"medium"` - Medium priority (amber badge)
- `"low"` - Low priority (green badge)
- `null` - Clear priority

**Response (200 OK):**
```json
{
  "success": true,
  "priority": "high"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/game/123/priority \
  -H "Content-Type: application/json" \
  -d '{"priority": "high"}'
```

**Error Responses:**
- `400 Bad Request` - Invalid priority value (must be 'high', 'medium', 'low', or null)
- `404 Not Found` - Game not found

---

### Set Personal Rating

Set or clear the personal rating (0-10) for a game.

**Endpoint:** `POST /api/game/{game_id}/personal-rating`

**Request Body:**
```json
{
  "rating": 8
}
```

**Valid Rating Values:**
- `0` - Remove rating (sets to NULL)
- `1-10` - Rating with star visualization

**Response (200 OK):**
```json
{
  "success": true,
  "rating": 8
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/game/123/personal-rating \
  -H "Content-Type: application/json" \
  -d '{"rating": 8}'
```

**Remove Rating:**
```bash
curl -X POST http://localhost:5050/api/game/123/personal-rating \
  -H "Content-Type: application/json" \
  -d '{"rating": 0}'
```

**Error Responses:**
- `400 Bad Request` - Rating out of range (must be 0-10)
- `404 Not Found` - Game not found

---

### Set Manual Playtime Tag

Manually assign a playtime tag to override auto-tagging or tag non-Steam games.

**Endpoint:** `POST /api/game/{game_id}/manual-playtime-tag`

**Request Body:**
```json
{
  "label_name": "Well Played"
}
```

**Valid Label Names:**
- `"Never Launched"`
- `"Just Tried"`
- `"Played"`
- `"Well Played"`
- `"Heavily Played"`
- `null` - Remove all playtime tags

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Tag 'Well Played' applied"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/game/123/manual-playtime-tag \
  -H "Content-Type: application/json" \
  -d '{"label_name": "Well Played"}'
```

**Remove Tag:**
```bash
curl -X POST http://localhost:5050/api/game/123/manual-playtime-tag \
  -H "Content-Type: application/json" \
  -d '{"label_name": null}'
```

**Behavior:**
- Manual tags (auto=0) persist through auto-tagging cycles
- Replaces any existing playtime tag (manual or auto)
- Useful for non-Steam games or overriding playtime-based tags

**Error Responses:**
- `404 Not Found` - Game or label not found

---

### Toggle Hidden Status

Show or hide a game in the library.

**Endpoint:** `POST /api/game/{game_id}/hidden`

**Request Body:**
```json
{
  "hidden": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "hidden": true
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/game/123/hidden \
  -H "Content-Type: application/json" \
  -d '{"hidden": true}'
```

---

### Toggle NSFW Status

Mark a game as NSFW (Not Safe For Work).

**Endpoint:** `POST /api/game/{game_id}/nsfw`

**Request Body:**
```json
{
  "nsfw": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "nsfw": true
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/game/123/nsfw \
  -H "Content-Type: application/json" \
  -d '{"nsfw": true}'
```

---

### Delete Game

Permanently delete a game from the library.

**Endpoint:** `DELETE /api/game/{game_id}`

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Deleted 'Game Name' from library"
}
```

**Example (curl):**
```bash
curl -X DELETE http://localhost:5050/api/game/123
```

**Behavior:**
- Removes game from database
- Cascades to remove all label associations (game_labels entries)

**Error Responses:**
- `404 Not Found` - Game not found

---

## Bulk Operations

### Bulk Set Priority

Set priority for multiple games at once.

**Endpoint:** `POST /api/games/bulk/set-priority`

**Request Body:**
```json
{
  "game_ids": [123, 456, 789],
  "priority": "high"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "updated": 3
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/games/bulk/set-priority \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789], "priority": "high"}'
```

**Error Responses:**
- `400 Bad Request` - No games selected or invalid priority value
- `200 OK` with `updated: 0` - Game IDs not found (partial success possible)

---

### Bulk Set Personal Rating

Set personal rating for multiple games at once.

**Endpoint:** `POST /api/games/bulk/set-personal-rating`

**Request Body:**
```json
{
  "game_ids": [123, 456, 789],
  "rating": 8
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "updated": 3
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/games/bulk/set-personal-rating \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789], "rating": 8}'
```

**Remove Ratings in Bulk:**
```bash
curl -X POST http://localhost:5050/api/games/bulk/set-personal-rating \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789], "rating": 0}'
```

**Error Responses:**
- `400 Bad Request` - No games selected or rating out of range (0-10)

---

### Bulk Hide Games

Hide multiple games from the library at once.

**Endpoint:** `POST /api/games/bulk/hide`

**Request Body:**
```json
{
  "game_ids": [123, 456, 789]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "updated": 3
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/games/bulk/hide \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789]}'
```

**Error Responses:**
- `400 Bad Request` - No games selected

---

### Bulk Mark NSFW

Mark multiple games as NSFW at once.

**Endpoint:** `POST /api/games/bulk/nsfw`

**Request Body:**
```json
{
  "game_ids": [123, 456, 789]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "updated": 3
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/games/bulk/nsfw \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789]}'
```

**Error Responses:**
- `400 Bad Request` - No games selected

---

### Bulk Delete Games

Delete multiple games from the library at once.

**Endpoint:** `POST /api/games/bulk/delete`

**Request Body:**
```json
{
  "game_ids": [123, 456, 789]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "deleted": 3
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/games/bulk/delete \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789]}'
```

**Behavior:**
- Permanently deletes games from database
- Removes all associated label entries (game_labels)
- Cannot be undone

**Error Responses:**
- `400 Bad Request` - No games selected

---

### Bulk Add to Collection

Add multiple games to a collection (label) at once.

**Endpoint:** `POST /api/games/bulk/add-to-collection`

**Request Body:**
```json
{
  "game_ids": [123, 456, 789],
  "collection_id": 5
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "added": 3
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/games/bulk/add-to-collection \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [123, 456, 789], "collection_id": 5}'
```

**Behavior:**
- Uses `INSERT OR IGNORE` to prevent duplicates
- Returns count of newly added associations (0 if all games were already in collection)
- Updates collection's `updated_at` timestamp

**Error Responses:**
- `400 Bad Request` - No games selected
- `404 Not Found` - Collection (label) not found

---

## System Operations

### Update System Tags

Manually trigger auto-tagging for all Steam games.

**Endpoint:** `POST /api/labels/update-system-tags`

**Request Body:** *(None)*

**Response (200 OK):**
```json
{
  "success": true,
  "message": "System tags updated"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:5050/api/labels/update-system-tags
```

**Behavior:**
- Updates auto labels (auto=1) for all Steam games based on current playtime
- Manual tags (auto=0) are preserved and not overwritten
- Non-Steam games are unaffected
- Typically called automatically after Steam sync, but can be triggered manually

**Use Cases:**
- Re-tag after adjusting system label boundaries (requires code change)
- Fix incorrect auto-tags after database issues
- Test auto-tagging logic

---

## Error Codes

### 400 Bad Request

**Causes:**
- Invalid priority value (not 'high', 'medium', 'low', or null)
- Rating out of range (not 0-10)
- Empty game_ids array in bulk operations

**Example Response:**
```json
{
  "detail": "Priority must be 'high', 'medium', 'low', or null"
}
```

### 404 Not Found

**Causes:**
- Game ID does not exist
- Label/Collection ID does not exist
- System label name not found

**Example Response:**
```json
{
  "detail": "Game not found"
}
```

### 500 Internal Server Error

**Causes:**
- Database connection failure
- Unexpected exception during operation

**Example Response:**
```json
{
  "detail": "Internal server error"
}
```

---

## Related Documentation

- [Labels, Tags & Auto-Tagging](system-labels-auto-tagging.md) - Complete labels system guide
- [Database Schema](database-schema.md) - Database structure for labels and metadata
- [Filter System](filter-system.md) - Using metadata in filters

---

## Notes for Developers

### Request Validation

All endpoints use Pydantic models for request validation:

```python
class UpdatePriorityRequest(BaseModel):
    priority: Optional[str] = None  # 'high', 'medium', 'low', or None

class UpdatePersonalRatingRequest(BaseModel):
    rating: int  # 0-10

class ManualPlaytimeTagRequest(BaseModel):
    label_name: Optional[str] = None

class BulkGameIdsRequest(BaseModel):
    game_ids: list[int]
```

### Database Transactions

- All bulk operations run in a single transaction
- Single-game operations commit immediately
- Failed operations trigger rollback

### Performance Considerations

- Bulk operations use parameterized queries with placeholders for efficiency
- `INSERT OR IGNORE` prevents duplicate entries without checking first
- Indexes on `game_labels.game_id` and `game_labels.label_id` optimize queries

### Testing

See [test_api_metadata_endpoints.py](../tests/test_api_metadata_endpoints.py) for comprehensive integration tests covering all endpoints.
