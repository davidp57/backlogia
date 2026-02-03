## ADDED Requirements

### Requirement: Orderly startup sequence
The application SHALL follow a defined startup sequence to ensure proper initialization.

#### Scenario: Startup sequence completes successfully
- **WHEN** the launcher is executed
- **THEN** it SHALL find a free port first
- **AND** start the FastAPI server in a background thread second
- **AND** wait for server readiness third
- **AND** create the native window fourth
- **AND** all steps SHALL complete without errors

### Requirement: Server readiness detection
The launcher SHALL detect when the FastAPI server is ready to accept connections.

#### Scenario: Server becomes ready
- **WHEN** the server thread is started
- **THEN** the launcher SHALL poll the server port
- **AND** attempt to establish a TCP connection
- **AND** retry until connection succeeds or timeout is reached
- **AND** consider the server ready when a connection succeeds

#### Scenario: Server readiness timeout
- **WHEN** the server does not become ready within 10 seconds
- **THEN** the launcher SHALL log an error message
- **AND** exit with status code 1
- **AND** the error message SHALL indicate server startup failure

### Requirement: Graceful shutdown
The application SHALL shut down gracefully when the window is closed.

#### Scenario: Window close triggers shutdown
- **WHEN** the user closes the native window
- **THEN** the PyWebView event loop SHALL exit
- **AND** the main process SHALL terminate
- **AND** the daemon server thread SHALL terminate automatically
- **AND** no zombie processes SHALL remain

### Requirement: Database initialization
The application SHALL initialize the database before the server starts accepting requests.

#### Scenario: Database initialized on startup
- **WHEN** the FastAPI app is created
- **THEN** the database initialization function SHALL be called
- **AND** all required tables and columns SHALL be created
- **AND** IGDB columns SHALL be added
- **AND** collections tables SHALL be created

### Requirement: Error handling during startup
The launcher SHALL handle and report errors that occur during startup.

#### Scenario: Port allocation failure
- **WHEN** no free port can be found
- **THEN** the launcher SHALL display an error message
- **AND** the message SHALL explain the port allocation failure
- **AND** the launcher SHALL exit with status code 1

#### Scenario: Server startup failure
- **WHEN** the server fails to start
- **THEN** the launcher SHALL detect the failure within the timeout period
- **AND** display an error message indicating server failure
- **AND** exit with status code 1

#### Scenario: WebView creation failure
- **WHEN** PyWebView fails to create the window
- **THEN** the launcher SHALL catch the exception
- **AND** display an error message
- **AND** the server thread SHALL be allowed to terminate
- **AND** the launcher SHALL exit with status code 1

### Requirement: Process cleanup
The launcher SHALL ensure proper cleanup of resources on exit.

#### Scenario: Clean exit on success
- **WHEN** the window closes normally
- **THEN** the launcher SHALL print a confirmation message
- **AND** exit with status code 0
- **AND** all file handles SHALL be closed
- **AND** the socket SHALL be released

#### Scenario: Clean exit on error
- **WHEN** an error occurs during startup
- **THEN** the launcher SHALL clean up any allocated resources
- **AND** exit with an appropriate error code
- **AND** no resources SHALL be leaked
