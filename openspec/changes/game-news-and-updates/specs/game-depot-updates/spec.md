## ADDED Requirements

### Requirement: Update timestamp tracking
The system SHALL track update timestamps for games using the last_modified field from store data.

#### Scenario: Store last_modified during import
- **WHEN** games are imported or synced from a store
- **THEN** system SHALL populate games.last_modified column with store-provided timestamp

#### Scenario: Steam last_modified tracking
- **WHEN** Steam game is synced
- **THEN** system SHALL store last_modified timestamp from Steam store metadata

#### Scenario: Epic last_modified tracking
- **WHEN** Epic game is synced via Legendary CLI
- **THEN** system SHALL store lastModifiedDate from Epic metadata

#### Scenario: GOG last_modified fallback
- **WHEN** GOG game is synced
- **THEN** system SHALL use current sync timestamp as fallback (Galaxy database lacks reliable update timestamps)

### Requirement: Depot update history storage
The system SHALL maintain a history table of depot updates with timestamps for tracking game patches.

#### Scenario: Update history record creation
- **WHEN** a game's last_modified changes from previous value
- **THEN** system SHALL create new record in game_depot_updates table

#### Scenario: Update record fields
- **WHEN** storing an update record
- **THEN** system SHALL include game_id, depot_id (null for non-Steam), manifest_id (null for non-Steam), update_timestamp, and fetched_at

#### Scenario: Multiple updates per game
- **WHEN** a game receives multiple updates over time
- **THEN** system SHALL maintain chronological history with separate records for each update

### Requirement: Update detection during sync
The system SHALL detect when games have been updated by comparing current and previous last_modified values.

#### Scenario: Detect new update
- **WHEN** game sync finds last_modified newer than stored value
- **THEN** system SHALL create depot update record and update games.last_modified

#### Scenario: No update detected
- **WHEN** game sync finds last_modified unchanged from stored value
- **THEN** system SHALL NOT create new depot update record

#### Scenario: First sync baseline
- **WHEN** game is synced for first time with last_modified value
- **THEN** system SHALL store timestamp but NOT create update record (baseline only)

### Requirement: Update history display
The system SHALL display update history on game detail pages for games with tracked updates.

#### Scenario: Update history section visibility
- **WHEN** user views game detail page for game with update records
- **THEN** system SHALL display "Update History" section with chronological list

#### Scenario: Update history hidden when empty
- **WHEN** user views game detail page for game without update records
- **THEN** system SHALL NOT display empty update history section

#### Scenario: Update display format
- **WHEN** update history is displayed
- **THEN** system SHALL show update timestamp in readable date format

#### Scenario: Update history sorting
- **WHEN** displaying multiple updates
- **THEN** system SHALL sort by update_timestamp in descending order (newest first)

#### Scenario: Update count limit
- **WHEN** displaying update history
- **THEN** system SHALL show maximum of 10 most recent updates

### Requirement: Update history API endpoint
The system SHALL provide an API endpoint to fetch update history for a specific game.

#### Scenario: API returns update history
- **WHEN** API request is made to /api/game/{game_id}/updates
- **THEN** system SHALL return JSON array of update records for that game

#### Scenario: API returns empty array for no updates
- **WHEN** API request is made for game without update records
- **THEN** system SHALL return empty JSON array with 200 status

#### Scenario: API returns error for invalid game ID
- **WHEN** API request is made with invalid game_id
- **THEN** system SHALL return 404 error

### Requirement: Multi-store update tracking
The system SHALL track updates for Steam, Epic, and GOG games with store-appropriate mechanisms.

#### Scenario: Steam update tracking
- **WHEN** syncing Steam games
- **THEN** system SHALL use last_modified from Steam store data

#### Scenario: Epic update tracking
- **WHEN** syncing Epic games via Legendary
- **THEN** system SHALL use lastModifiedDate from metadata

#### Scenario: GOG limited tracking
- **WHEN** syncing GOG games
- **THEN** system SHALL document limitation and use sync timestamp as proxy

#### Scenario: Store indicator in UI
- **WHEN** displaying update history
- **THEN** system SHALL indicate which stores have reliable vs limited update tracking

### Requirement: Update recency calculation
The system SHALL calculate how recently games were updated for filtering and display purposes.

#### Scenario: Recently updated identification
- **WHEN** system checks if game is recently updated
- **THEN** system SHALL compare most recent update_timestamp or last_modified against current date

#### Scenario: 30-day recency threshold
- **WHEN** determining recent updates for filtering
- **THEN** system SHALL use 30 days as default threshold

#### Scenario: Null value handling
- **WHEN** game has no last_modified or update records
- **THEN** system SHALL treat as not recently updated
