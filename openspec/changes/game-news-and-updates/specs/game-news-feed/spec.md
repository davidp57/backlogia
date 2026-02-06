## ADDED Requirements

### Requirement: News article storage
The system SHALL store news articles in a dedicated database table with game associations, metadata, and timestamps.

#### Scenario: News article is stored with required fields
- **WHEN** a news article is fetched from Steam News API
- **THEN** system SHALL store article with id, game_id, title, content, author, url, published_at, and fetched_at fields

#### Scenario: Multiple articles per game
- **WHEN** multiple news articles exist for a single game
- **THEN** system SHALL store all articles with unique IDs and maintain game_id foreign key relationship

#### Scenario: Article updates
- **WHEN** an article with the same URL is fetched again
- **THEN** system SHALL update existing article rather than creating duplicate

### Requirement: Steam News API integration
The system SHALL fetch news articles from Steam News API for Steam games in the user's library.

#### Scenario: Fetch news for Steam game
- **WHEN** news sync is triggered for a Steam game with valid store_id
- **THEN** system SHALL request news from Steam API endpoint with game's appid

#### Scenario: Configurable article count
- **WHEN** fetching news articles
- **THEN** system SHALL allow configurable maximum article count (default 10)

#### Scenario: Handle API rate limits
- **WHEN** making multiple API requests
- **THEN** system SHALL respect rate limit of 200 requests per 5 minutes

#### Scenario: Handle API errors gracefully
- **WHEN** Steam News API returns an error or timeout
- **THEN** system SHALL log error and continue processing other games without crashing

### Requirement: News display in game detail page
The system SHALL display news articles on the game detail page for games that have news data.

#### Scenario: News section visibility
- **WHEN** user views a game detail page for a game with news articles
- **THEN** system SHALL display a "News" section with article list

#### Scenario: News section hidden for games without news
- **WHEN** user views a game detail page for a game without news articles
- **THEN** system SHALL NOT display an empty news section

#### Scenario: Article display format
- **WHEN** news articles are displayed
- **THEN** system SHALL show title, author, publish date, and truncated content for each article

#### Scenario: Article links
- **WHEN** user clicks on a news article
- **THEN** system SHALL open the full article URL in a new tab

#### Scenario: Article sorting
- **WHEN** displaying multiple news articles
- **THEN** system SHALL sort by publish date in descending order (newest first)

### Requirement: News API endpoint
The system SHALL provide an API endpoint to fetch news articles for a specific game.

#### Scenario: API returns news for game
- **WHEN** API request is made to /api/game/{game_id}/news
- **THEN** system SHALL return JSON array of news articles for that game

#### Scenario: API returns empty array for game without news
- **WHEN** API request is made for a game with no news articles
- **THEN** system SHALL return empty JSON array with 200 status

#### Scenario: API returns error for invalid game ID
- **WHEN** API request is made with invalid game_id
- **THEN** system SHALL return 404 error

### Requirement: Sync service for news
The system SHALL provide a background sync service to fetch news for all or selected games.

#### Scenario: Sync all Steam games
- **WHEN** news sync is triggered with mode 'all'
- **THEN** system SHALL fetch news for all Steam games in library

#### Scenario: Incremental sync
- **WHEN** news sync is triggered without force flag
- **THEN** system SHALL skip games with news fetched within last 24 hours

#### Scenario: Force sync
- **WHEN** news sync is triggered with force flag
- **THEN** system SHALL fetch news for all games regardless of last fetch time

#### Scenario: Sync progress reporting
- **WHEN** news sync is running
- **THEN** system SHALL report progress with current/total counts

#### Scenario: Batch processing
- **WHEN** syncing large libraries
- **THEN** system SHALL process games in chunks of 50 with parallel workers

#### Scenario: Steam-only limitation
- **WHEN** news sync encounters non-Steam games
- **THEN** system SHALL skip those games (no news API available for Epic/GOG)

### Requirement: News sync route
The system SHALL provide an HTTP endpoint to trigger news synchronization.

#### Scenario: Trigger news sync via API
- **WHEN** POST request is made to /api/sync/news/{mode}
- **THEN** system SHALL initiate news sync with specified mode (all/recent)

#### Scenario: Sync returns statistics
- **WHEN** news sync completes
- **THEN** system SHALL return JSON with success status, message, and counts (fetched/failed)

#### Scenario: Sync requires authentication
- **WHEN** unauthenticated user attempts to trigger sync
- **THEN** system SHALL return 401 Unauthorized error

### Requirement: News caching
The system SHALL cache news articles to minimize redundant API requests.

#### Scenario: Recently fetched news is cached
- **WHEN** news for a game was fetched within last 24 hours
- **THEN** system SHALL use cached data instead of making new API request

#### Scenario: Cache expiration
- **WHEN** news for a game is older than 24 hours
- **THEN** system SHALL fetch fresh news from API

#### Scenario: Manual cache bypass
- **WHEN** user triggers force sync
- **THEN** system SHALL bypass cache and fetch fresh data
