## MODIFIED Requirements

### Requirement: FastAPI server runs in thread
The FastAPI server SHALL be capable of running in a background thread within the launcher process.

#### Scenario: Server starts in thread
- **WHEN** the launcher calls the server start function
- **THEN** uvicorn SHALL start with the provided configuration
- **AND** run the FastAPI app on the specified host and port
- **AND** execute within the calling thread context
- **AND** not interfere with other threads in the process

### Requirement: Dynamic host and port configuration
The FastAPI server SHALL accept dynamic host and port configuration at startup.

#### Scenario: Server binds to specified port
- **WHEN** the server is started with a specific port (e.g., 8002)
- **THEN** it SHALL bind to 127.0.0.1:8002
- **AND** be accessible at http://127.0.0.1:8002

### Requirement: Reduced logging verbosity
The FastAPI server SHALL support reduced logging for desktop application use.

#### Scenario: Warning-level logging enabled
- **WHEN** the server is configured for desktop mode
- **THEN** the log level SHALL be set to "warning"
- **AND** access logs SHALL be disabled
- **AND** only errors and warnings SHALL be logged to console

### Requirement: Thread-safe operation
The FastAPI server SHALL operate safely when run in a daemon thread.

#### Scenario: Server handles requests in thread
- **WHEN** the server receives HTTP requests
- **THEN** it SHALL process them correctly within the thread
- **AND** responses SHALL be sent successfully
- **AND** no thread-safety issues SHALL occur
- **AND** the main thread SHALL not be blocked

### Requirement: Existing functionality preserved
All existing FastAPI routes and functionality SHALL work without modification when run in threaded mode.

#### Scenario: Library route works in threaded mode
- **WHEN** a request is made to the library route
- **THEN** the route SHALL respond correctly
- **AND** database queries SHALL execute successfully
- **AND** templates SHALL render properly

#### Scenario: Sync route works in threaded mode
- **WHEN** a request is made to sync game data
- **THEN** the sync SHALL execute correctly in the thread
- **AND** database updates SHALL complete successfully
- **AND** the response SHALL be returned to the client

#### Scenario: API routes work in threaded mode
- **WHEN** API requests are made (games, metadata, etc.)
- **THEN** the API SHALL respond with correct data
- **AND** JSON serialization SHALL work correctly
- **AND** error handling SHALL function properly

### Requirement: CORS configuration for localhost
The FastAPI server SHALL maintain CORS configuration that allows requests from localhost origins.

#### Scenario: Localhost CORS allowed
- **WHEN** the webview makes requests to the server
- **THEN** CORS headers SHALL allow the requests
- **AND** requests from 127.0.0.1 SHALL be permitted
- **AND** requests from localhost SHALL be permitted
