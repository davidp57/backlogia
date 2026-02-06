## Why

Users need visibility into game updates, news, and development status to stay informed about their library. Currently, Backlogia shows game metadata but lacks real-time information about patches, announcements, and Early Access/Alpha statuses, forcing users to check external sources.

## What Changes

- Add a news feed displaying game-related announcements and updates
- Implement depot update history tracking to show when games are patched
- Display game development status (Alpha, Early Access, Released) and version information
- Create UI components to surface this information in game detail pages and library views
- Add data synchronization from Steam depot manifest and news APIs
- Add predefined filters to query games by development status and update recency:
  - Games leaving Early Access
  - Games in specific states (Alpha, Beta, Early Access, Released, etc.)
  - Games updated recently (based on depot update history)

## Capabilities

### New Capabilities
- `game-news-feed`: Fetch, store, and display news articles and announcements for games in the user's library
- `game-depot-updates`: Track and display depot update history showing when game files are updated/patched
- `game-status-tracking`: Store and display game development status (Alpha, Beta, Early Access, Released) and current version information
- `game-status-filters`: Filter games by development status and update recency in the library view

### Modified Capabilities
<!-- No existing capabilities require requirement changes -->

## Impact

**Affected Areas:**
- **Database schema**: New tables for news articles, depot updates, and status tracking; new columns for game status and version
- **Web routes**: New API endpoints for fetching news/updates data
- **Services**: New sync services for Steam News API and depot manifests
- **Templates**: Game detail page updates to display news feed, update history, and status badges
- **Filter system**: Extension of predefined filters to include status-based and update-based filters
- **Dependencies**: May require Steam Web API integration for news and depot data
