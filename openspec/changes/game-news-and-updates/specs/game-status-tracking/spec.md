## ADDED Requirements

### Requirement: Development status storage
The system SHALL store development status for games in the games table using standardized status values.

#### Scenario: Status field values
- **WHEN** storing development status
- **THEN** system SHALL use one of: 'alpha', 'beta', 'early_access', 'released', or NULL

#### Scenario: Status column addition
- **WHEN** system initializes
- **THEN** system SHALL ensure development_status column exists in games table

#### Scenario: Status nullable
- **WHEN** game status is unknown or not applicable
- **THEN** system SHALL allow NULL value in development_status field

### Requirement: Game version tracking
The system SHALL store current version information for games.

#### Scenario: Version string storage
- **WHEN** game version is available
- **THEN** system SHALL store version in game_version TEXT field (e.g., "1.2.3", "v2.0")

#### Scenario: Version column addition
- **WHEN** system initializes
- **THEN** system SHALL ensure game_version column exists in games table

#### Scenario: Version nullable
- **WHEN** version information is unavailable
- **THEN** system SHALL allow NULL value in game_version field

### Requirement: Status sync timestamp
The system SHALL track when status information was last synchronized for staleness detection.

#### Scenario: Sync timestamp storage
- **WHEN** status is synchronized for a game
- **THEN** system SHALL update status_last_synced timestamp

#### Scenario: Timestamp column addition
- **WHEN** system initializes
- **THEN** system SHALL ensure status_last_synced column exists in games table

#### Scenario: Initial timestamp on sync
- **WHEN** game status is synced for first time
- **THEN** system SHALL set status_last_synced to current timestamp

### Requirement: Steam status detection
The system SHALL detect Early Access status for Steam games using Steam store metadata.

#### Scenario: Steam Early Access detection
- **WHEN** syncing status for Steam game
- **THEN** system SHALL check for category 29 (Early Access) in Steam app details

#### Scenario: Steam released status
- **WHEN** Steam game lacks Early Access category
- **THEN** system SHALL set development_status to 'released'

#### Scenario: Steam API integration
- **WHEN** fetching Steam game status
- **THEN** system SHALL use Steam Store API app_details endpoint

### Requirement: Epic status detection
The system SHALL detect Early Access status for Epic games using metadata from Legendary CLI.

#### Scenario: Epic Early Access flag
- **WHEN** syncing status for Epic game
- **THEN** system SHALL check customAttributes for early access indicators in metadata

#### Scenario: Epic metadata parsing
- **WHEN** Epic game metadata is available
- **THEN** system SHALL extract status from Legendary CLI JSON output

#### Scenario: Epic released default
- **WHEN** Epic game has no early access flag
- **THEN** system SHALL default to 'released' status

### Requirement: GOG status detection
The system SHALL support manual status categorization for GOG games with IGDB fallback.

#### Scenario: GOG IGDB fallback
- **WHEN** GOG game has IGDB metadata
- **THEN** system SHALL use IGDB status information if available

#### Scenario: GOG manual override
- **WHEN** user manually sets status for GOG game
- **THEN** system SHALL accept and store user-provided status

#### Scenario: GOG default status
- **WHEN** GOG game lacks status information
- **THEN** system SHALL leave development_status as NULL

### Requirement: Status display in game detail page
The system SHALL display development status badge on game detail pages when status is available.

#### Scenario: Status badge visibility
- **WHEN** user views game detail page with development_status set
- **THEN** system SHALL display status badge near game title

#### Scenario: Status badge styling
- **WHEN** displaying status badge
- **THEN** system SHALL use distinct colors/styles for alpha, beta, early_access, released

#### Scenario: Status badge hidden when NULL
- **WHEN** game has NULL development_status
- **THEN** system SHALL NOT display status badge

#### Scenario: Version display
- **WHEN** game has game_version set
- **THEN** system SHALL display version string below or near status badge

### Requirement: Status display in library view
The system SHALL display status indicators on game cards in library view.

#### Scenario: Library card status badge
- **WHEN** user views library with games having development_status
- **THEN** system SHALL show small status badge/icon on game cards

#### Scenario: Badge size appropriate for cards
- **WHEN** displaying status on game cards
- **THEN** system SHALL use compact badge that doesn't obscure cover art

#### Scenario: Badge tooltip
- **WHEN** user hovers over status badge in library
- **THEN** system SHALL show tooltip with full status text

### Requirement: Status sync service
The system SHALL provide background sync service to fetch and update development status for games.

#### Scenario: Sync all games status
- **WHEN** status sync is triggered with mode 'all'
- **THEN** system SHALL fetch status for all games in library

#### Scenario: Store-specific sync
- **WHEN** status sync is triggered with specific store parameter
- **THEN** system SHALL sync only games from that store

#### Scenario: Incremental sync
- **WHEN** status sync runs without force flag
- **THEN** system SHALL skip games with status_last_synced within last 7 days

#### Scenario: Force sync
- **WHEN** status sync runs with force flag
- **THEN** system SHALL sync all games regardless of last sync time

#### Scenario: Sync progress reporting
- **WHEN** status sync is running
- **THEN** system SHALL report progress with current/total counts

### Requirement: Status sync route
The system SHALL provide HTTP endpoint to trigger status synchronization.

#### Scenario: Trigger status sync via API
- **WHEN** POST request is made to /api/sync/status/{mode}
- **THEN** system SHALL initiate status sync with specified mode (all/new)

#### Scenario: Sync returns statistics
- **WHEN** status sync completes
- **THEN** system SHALL return JSON with success status, message, and counts (synced/failed)

### Requirement: Manual status override
The system SHALL allow users to manually set or correct development status for any game.

#### Scenario: User sets custom status
- **WHEN** user manually sets development_status via UI
- **THEN** system SHALL accept and store the user-provided value

#### Scenario: User clears status
- **WHEN** user clears manually set status
- **THEN** system SHALL set development_status to NULL

#### Scenario: Override persists across syncs
- **WHEN** game has manually set status and sync runs
- **THEN** system SHALL preserve manual override unless force override flag is set

### Requirement: Status history consideration
The system SHALL document that status history tracking is deferred to future versions.

#### Scenario: No status change tracking
- **WHEN** game status changes (e.g., exits Early Access)
- **THEN** system SHALL update current status but NOT maintain historical record

#### Scenario: Status change detection unavailable
- **WHEN** user wants to see "games that left Early Access"
- **THEN** system SHALL document this requires status history (v2 feature)
