## ADDED Requirements

### Requirement: Automatic port allocation
The system SHALL automatically find and allocate an available port for the FastAPI server on startup.

#### Scenario: Default port is available
- **WHEN** the launcher attempts to find a free port
- **AND** port 8000 is available
- **THEN** the system SHALL bind to port 8000

#### Scenario: Default port is occupied
- **WHEN** the launcher attempts to find a free port
- **AND** port 8000 is already in use
- **THEN** the system SHALL try the next port (8001)
- **AND** continue incrementing until a free port is found

### Requirement: Port range limits
The system SHALL search within a defined port range and fail gracefully if no port is available.

#### Scenario: Port found within range
- **WHEN** searching for a free port starting at 8000
- **AND** a port is available within the next 100 ports
- **THEN** the system SHALL allocate that port

#### Scenario: No port available in range
- **WHEN** searching for a free port starting at 8000
- **AND** all ports from 8000 to 8099 are occupied
- **THEN** the system SHALL raise a RuntimeError
- **AND** display a clear error message to the user

### Requirement: Port detection method
The system SHALL use socket binding to verify port availability.

#### Scenario: Port availability check
- **WHEN** checking if a port is available
- **THEN** the system SHALL attempt to bind a socket to 127.0.0.1 on that port
- **AND** if binding succeeds, the port is available
- **AND** if binding fails with OSError, the port is occupied
- **AND** the socket SHALL be properly closed after the check

### Requirement: Localhost binding
The server SHALL bind only to the localhost interface for security.

#### Scenario: Server binds to localhost
- **WHEN** the server starts on the allocated port
- **THEN** it SHALL bind to 127.0.0.1
- **AND** SHALL NOT bind to 0.0.0.0 or other network interfaces
- **AND** the server SHALL only be accessible from the local machine

### Requirement: Port communication to window
The launcher SHALL communicate the allocated port to the webview window.

#### Scenario: Window URL uses allocated port
- **WHEN** a free port is found (e.g., 8002)
- **THEN** the webview window SHALL be created with URL http://127.0.0.1:8002
- **AND** the window SHALL successfully connect to the server on that port
