## 1. Database Schema

- [x] 1.1 Create migration function to add columns to games table (development_status, game_version, status_last_synced)
- [x] 1.2 Create game_news table with indexes on game_id and published_at
- [x] 1.3 Create game_depot_updates table with indexes on game_id and update_timestamp
- [x] 1.4 Add database indexes on development_status and last_modified columns
- [x] 1.5 Call migration on app startup in web/main.py

## 2. News Sync Service

- [x] 2.1 Create web/services/news_sync.py with NewsClient class for Steam News API
- [x] 2.2 Implement fetch_news_for_game(appid, count) method with rate limiting
- [x] 2.3 Implement sync_news(conn, store, force, max_items) to sync all games
- [x] 2.4 Implement sync_game_news(conn, game_id, max_items) for single game
- [x] 2.5 Add 24-hour caching logic to skip recently fetched news
- [x] 2.6 Implement batch processing with ThreadPoolExecutor (5 workers)
- [x] 2.7 Implement get_news_stats(conn) to return sync statistics
- [x] 2.8 Add error handling for API failures and timeouts

## 3. Status Sync Service

- [x] 3.1 Create web/services/status_sync.py with status detection functions
- [x] 3.2 Implement sync_game_status(conn, game_id) for single game status update
- [x] 3.3 Implement Steam status detection using app_details API (category 29 for Early Access)
- [x] 3.4 Implement Epic status detection from Legendary metadata custom attributes
- [x] 3.5 Implement GOG status detection with IGDB fallback
- [x] 3.6 Implement sync_all_statuses(conn, store, force) for batch updates
- [x] 3.7 Add incremental sync logic (skip games synced within 7 days unless force)
- [x] 3.8 Implement update timestamp tracking during store imports (last_modified)
- [x] 3.9 Implement update detection logic (compare last_modified, create depot_update records)

## 4. API Routes - Sync Endpoints

- [x] 4.1 Add POST /api/sync/news/{mode} route in web/routes/sync.py
- [x] 4.2 Add POST /api/sync/status/{mode} route in web/routes/sync.py
- [x] 4.3 Implement authentication checks for sync endpoints
- [x] 4.4 Return JSON responses with success status and statistics

## 5. API Routes - Game Endpoints

- [x] 5.1 Add GET /api/game/{game_id}/news endpoint in web/routes/api_games.py
- [x] 5.2 Add GET /api/game/{game_id}/updates endpoint in web/routes/api_games.py
- [x] 5.3 Add error handling for invalid game IDs (404 responses)
- [x] 5.4 Return properly sorted results (newest first)

## 6. Filter System Extension

- [x] 6.1 Add "Development Status" category to QUERY_CATEGORIES in web/utils/filters.py
- [x] 6.2 Add filter definitions to PREDEFINED_QUERIES: early-access, alpha-beta, released, in-development
- [x] 6.3 Add update recency filters: recently-modified (30d), updated-this-week (7d), updated-this-month (30d)
- [x] 6.4 Update filter SQL generation to handle new status-based conditions
- [x] 6.5 Add filter counting logic for status filters in get_query_filter_counts()
- [x] 6.6 Add help text for store compatibility of update filters

## 7. UI - Filter Bar

- [x] 7.1 Add "Development Status" dropdown section in web/templates/_filter_bar.html
- [x] 7.2 Add filter options with labels and count badges
- [x] 7.3 Update web/static/js/filters.js to handle status filter toggles
- [x] 7.4 Update web/static/css/filters.css for status filter styling
- [ ] 7.5 Add tooltips/help text for filters with store limitations

## 8. UI - Game Detail Page

- [x] 8.1 Add status badge display near game title in web/templates/game_detail.html
- [x] 8.2 Add version string display below/near status badge
- [x] 8.3 Create collapsible "News" section for Steam games
- [x] 8.4 Fetch and display news articles with title, author, date, truncated content
- [x] 8.5 Add article links that open in new tab
- [x] 8.6 Create "Update History" section for games with depot updates
- [x] 8.7 Display update timestamps in readable format (limit to 10 most recent)
- [x] 8.8 Hide sections when no data available (NULL handling)

## 9. UI - Library View

- [x] 9.1 Add compact status badges to game cards in web/templates/index.html
- [x] 9.2 Style badges to not obscure cover art
- [x] 9.3 Add tooltips on badge hover showing full status text
- [x] 9.4 Apply status-specific colors (alpha/beta/early_access/released)

## 10. Store Integration Updates

- [x] 10.1 Update Steam import to populate last_modified from store metadata
- [x] 10.2 Verify Epic import already captures lastModifiedDate (ensure consistency)
- [x] 10.3 Update GOG import to use sync timestamp as fallback for last_modified
- [x] 10.4 Add update detection during store sync (compare and create depot_update records)

## 11. Manual Status Override

- [x] 11.1 Add UI controls in game detail page for manual status setting
- [x] 11.2 Create API endpoint for updating development_status manually
- [x] 11.3 Implement logic to preserve manual overrides during sync (unless force flag)

## 12. Settings & Configuration

- [x] 12.1 Add sync buttons for news and status in web/templates/settings.html
- [x] 12.2 Add JavaScript handlers for triggering news/status sync
- [x] 12.3 Display last sync timestamps for news and status data

## 13. Testing

- [x] 13.1 Create tests/test_news_sync.py with unit tests for NewsClient
- [x] 13.2 Create tests/test_status_sync.py with unit tests for status detection
- [x] 13.3 Add integration tests for /api/sync/news and /api/sync/status routes
- [x] 13.4 Add tests for /api/game/{id}/news and /api/game/{id}/updates endpoints
- [x] 13.5 Add tests for new filter definitions and SQL generation
- [x] 13.6 Add tests for filter combinations and counting
- [x] 13.7 Test UI rendering with and without news/update data
- [x] 13.8 Test multi-store update tracking (Steam/Epic/GOG)

## 14. Documentation

- [x] 14.1 Document news sync service in .copilot-docs/news-sync.md
- [x] 14.2 Document status tracking in .copilot-docs/status-tracking.md
- [x] 14.3 Update filter system docs in docs/filter-system.md with new filters
- [x] 14.4 Document database schema changes in docs/database-schema.md
- [x] 14.5 Add API endpoint documentation for news and updates routes
- [x] 14.6 Document store compatibility and limitations (update tracking accuracy)

## 15. Performance & Polish

- [x] 15.1 Verify database index creation for performance
- [x] 15.2 Test sync performance with large libraries (1000+ games)
- [x] 15.3 Optimize filter counting queries
- [x] 15.4 Add loading states for sync operations in UI
- [x] 15.5 Test rate limiting behavior for Steam News API

## 16. CHANGELOG & Release

- [x] 16.1 Update CHANGELOG.md with new features under [Unreleased]
- [x] 16.2 Document news feed, update tracking, status tracking, and new filters
- [x] 16.3 Note store compatibility (Steam news only, Steam/Epic updates reliable)
- [x] 16.4 Run all tests to ensure everything passes
- [x] 16.5 Check for VS Code errors and warnings
