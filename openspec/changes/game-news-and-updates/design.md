## Context

Backlogia currently aggregates game libraries from multiple stores (Steam, Epic, GOG, etc.) and enriches metadata through external sync services (IGDB, ProtonDB, Metacritic). The existing architecture includes:

- SQLite database with a `games` table storing metadata, ratings, and playtime
- Sync services (`web/services/`) that fetch external data using background jobs
- A predefined filter system (`web/utils/filters.py`) enabling library queries
- Web routes (`web/routes/`) exposing APIs and serving templates

**Current Limitations:**
- No visibility into game updates/patches after initial import
- No tracking of development status (Early Access, Beta, Alpha, Released)
- No news feed for game announcements
- Users must check external sources (Steam store pages, community hubs) for update information

**Constraints:**
- Steam Web API access requires Steam API key (already configured via `STEAM_API_KEY` env var)
- Must maintain existing database schema patterns (use `ALTER TABLE` for new columns)
- Must integrate with existing sync job infrastructure (`web/routes/sync.py`)
- UI must follow existing template patterns (Jinja2 templates in `web/templates/`)

## Goals / Non-Goals

**Goals:**
- Display news articles for games in user's library
- Track depot update history showing when games receive patches (multi-store support)
- Display current development status and version for each game (all stores)
- Enable filtering games by status (Early Access, Released, etc.) and update recency (all stores)
- Integrate with Steam News API for news feed
- Use existing `last_modified` fields for Epic/GOG to track updates
- Provide background sync jobs similar to IGDB/ProtonDB
- Sync ALL games in library, not just played games

**Non-Goals:**
- News feed for non-Steam stores initially (Epic, GOG news APIs limited/unavailable)
- Real-time notifications/push updates (initial version is pull-based)
- Detailed patch notes or changelogs (just update timestamps and headlines)
- Automatic detection of status changes (e.g., leaving Early Access) - requires manual sync trigger

## Decisions

### 1. Database Schema - Three New Tables + Columns

**Rationale:** Separate concerns for news, updates, and status. Avoid bloating the `games` table.

**New Tables:**
- `game_news` - Stores news articles from Steam News API
  - Columns: `id`, `game_id` (FK), `title`, `content`, `author`, `url`, `published_at`, `fetched_at`
  - Index on `game_id`, `published_at` for efficient queries
  
- `game_depot_updates` - Tracks depot manifest changes
  - Columns: `id`, `game_id` (FK), `depot_id`, `manifest_id`, `update_timestamp`, `fetched_at`
  - Index on `game_id`, `update_timestamp` for sorting by recency
  - Note: Only available for Steam games with depot access

- `game_status` table **rejected** - too complex for initial version

**New Columns on `games` table:**
- `development_status` TEXT - Values: 'alpha', 'beta', 'early_access', 'released', NULL
- `game_version` TEXT - Current version string (e.g., "1.2.3")
- `status_last_synced` TIMESTAMP - When status was last updated

**Alternative Considered:** Store status history in separate table - **Rejected** due to complexity; current status is sufficient for filtering needs.

### 2. Data Sources - Multi-Store Support

**News Feed (Steam Only for v1):**
- **Steam News API:**
  - Endpoint: `http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count=10`
  - Returns JSON with news items (title, contents, url, date)
  - Public API, no authentication required
  - Rate limiting: ~200 requests/5 minutes (conservative approach)
- **Epic/GOG:** No public news APIs available - defer to future versions

**Update Tracking (All Stores):**
- **Steam:** Use `last_modified` field from store metadata
  - Track timestamp during Steam library sync
  - Compare with previous value to detect updates
  - **Alternative Considered:** Actual depot manifests - **Rejected** due to complexity
  
- **Epic Games:** Already imports `last_modified` field from Legendary CLI metadata
  - Field: `metadata.lastModifiedDate` from Epic's app metadata
  - Already stored in database during Epic sync
  - Just need to populate `games.last_modified` column consistently
  
- **GOG:** Limited update tracking capability
  - GOG Galaxy database doesn't expose update timestamps reliably
  - Use database import timestamp as fallback for "last synced"
  - **Future:** Investigate GOG Galaxy 2.0 plugin API for update events

**Development Status (All Stores):**
- **Steam:** Store metadata (`type` field indicates Early Access via category 29)
- **Epic:** Metadata includes early access flag in custom attributes
- **GOG:** Manual categorization or IGDB-based detection
- Fetch during store library import or dedicated sync
- Manual override capability for corrections

**Alternative Considered:** Scrape store pages for status - **Rejected** due to fragility and rate limit concerns.

### 3. Sync Service Architecture - Modular Background Jobs

**Pattern:** Follow existing sync services (`igdb_sync.py`, `protondb_sync.py`)

**New Service:** `web/services/news_sync.py`
- `NewsClient` class for Steam News API requests
- `sync_news(conn, store='steam', force=False, max_items=10)` - Fetch recent news for ALL games from specified store
- `sync_game_news(conn, game_id, max_items=10)` - Fetch news for a single game
- `get_news_stats(conn)` - Return counts of fetched articles
- Only implements Steam support initially; architecture allows adding Epic/GOG later

**New Service:** `web/services/status_sync.py`
- `sync_game_status(conn, game_id)` - Update status and version for a single game
- `sync_all_statuses(conn, store=None, force=False)` - Batch update ALL games (all stores if store=None)
- Store-specific status extraction:
  - Steam: `app_details` endpoint for Early Access flag
  - Epic: Parse metadata custom attributes from Legendary
  - GOG: Use IGDB data or manual tagging

**Integration:** Add new routes to `web/routes/sync.py`:
- `POST /api/sync/news/{mode}` - Sync news (mode: 'recent' or 'all')
- `POST /api/sync/status/{mode}` - Sync game statuses (mode: 'new' or 'all')

**Threading Strategy:** Use `ThreadPoolExecutor` (like ProtonDB sync) for parallel API requests, limiting to 5 workers to respect rate limits.

### 4. Filter System Extension

**Integration Point:** Extend `web/utils/filters.py` with new filter definitions

**New Filters:**
- `leaving-early-access` - Games where status changed from 'early_access' to 'released' (requires tracking status changes - **downgraded** to just showing current 'released' games in first version)
- `early-access` - Games with status = 'early_access'
- `alpha-beta` - Games with status IN ('alpha', 'beta')
- `released` - Games with status = 'released'
- `recently-updated-depot` - Games with depot updates in last 30 days

**Filter SQL Examples:**
```sql
-- Early Access
development_status = 'early_access'

-- Recently Updated (simplified version using last_modified)
last_modified IS NOT NULL AND last_modified >= date('now', '-30 days')

-- Released games
development_status = 'released'
```

**UI:** Add new "Development Status" category to filter bar in `web/templates/_filter_bar.html`

**Alternative Considered:** Use separate filtering page for advanced queries - **Rejected** to maintain consistency with existing UX.

### 5. UI Components - Game Detail Page + Library Enhancements

**Game Detail Page (`web/templates/game_detail.html`):**
- Add "News" section showing recent articles (collapsed by default, expand on click)
- Add "Update History" section showing recent depot updates
- Display status badge (Alpha/Beta/Early Access/Released) near game title
- Display version string if available

**Library Page (`web/templates/index.html`):**
- Add status badges to game cards (small icon/label)
- No changes to main layout, filters handle discovery

**API Endpoints:** (in `web/routes/api_games.py`)
- `GET /api/game/{game_id}/news` - Return news articles for a game (JSON)
- `GET /api/game/{game_id}/updates` - Return depot update history (JSON)

**Alternative Considered:** Dedicated news feed page - **Deferred** to future iteration; game detail integration is sufficient for v1.

## Risks / Trade-offs

### Performance Impact
**Risk:** Fetching news/status for large libraries (1000+ games) could be slow and hit rate limits.

**Mitigation:** 
- Sync ALL games but implement smart batching:
  - Process in chunks of 50 games with progress reporting
  - Use ThreadPoolExecutor (5 workers) for parallel requests
- Implement incremental sync (fetch only games without recent data or older than 24h)
- Cache news for 24 hours before re-fetching
- Rate limiting: 200 requests per 5 minutes for Steam API
- For Epic/GOG: Update tracking uses existing sync, no additional API calls

### Data Staleness
**Risk:** Status and news data become outdated if users don't manually trigger syncs.

**Mitigation:**
- Add "Last synced" timestamps visible in UI
- Provide "Sync All" button in settings
- **Future:** Implement automatic weekly background sync

### News Feed Steam-Only Limitation
**Risk:** Non-Steam games have no news feed data.

**Mitigation:**
- Clearly indicate "News available for Steam games" in UI
- Epic/GOG games still show update tracking via `last_modified`
- Leave architecture open for adding Epic/GOG news sources later
- Use NULL values gracefully (don't show empty news sections for non-Steam games)

**Note:** Update tracking (via `last_modified`) works for Steam and Epic, partial for GOG

### Depot Update Accuracy
**Risk:** `last_modified` field may not accurately reflect game updates (could indicate store page changes).

**Mitigation:**
- Label as "Last Modified" not "Last Updated" to set accurate expectations
- Accept some false positives (better than no data)
- **Future:** Investigate actual depot manifest tracking if demand exists

## Migration Plan

### Database Migration
1. Add new columns to `games` table using `ALTER TABLE` (similar to `add_igdb_columns()` pattern)
2. Create new tables `game_news` and `game_depot_updates` with indexes
3. Run migration on app startup in `web/main.py` (add `ensure_news_tables()` function)

### Rollout Steps
1. Deploy schema changes (no breaking changes, all columns nullable)
2. Add sync services and routes
3. Deploy UI changes (news sections hidden if no data)
4. Run initial status sync for Steam games
5. Enable news sync (manual trigger only initially)

### Rollback Strategy
- New columns/tables don't affect existing functionality
- Can disable features by skipping sync calls
- Drop tables/columns if needed (no dependencies)

## Open Questions

1. **Should we track status history?** Currently only storing current status. Detecting "leaving Early Access" requires historical tracking. Decision: Defer to v2 unless user feedback demands it.

2. **How often to sync news?** Decision: Manual sync for ALL games, with smart caching (24h) to avoid redundant API calls. Weekly auto-sync in v2.

3. **Should depot updates be separate from last_modified?** Using last_modified is simpler but less accurate. Decision: Start with last_modified for Steam/Epic, gather feedback on usefulness before investing in actual depot manifest parsing.

4. **Filter naming:** "Recently Updated" overlaps with existing filter (for Epic games). Rename to "Recently Modified" or "Updated Last 30 Days"? Decision: Use "Recently Modified" for consistency.

5. **GOG update tracking limitations:** GOG Galaxy database lacks reliable update timestamps. Decision: Accept limitation for v1, use library sync timestamp as fallback. Investigate Galaxy 2.0 plugin API for v2.
