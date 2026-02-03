## ADDED Requirements

### Requirement: Desktop launcher starts application
The desktop launcher SHALL start the FastAPI backend server and display the application in a native window when executed.

#### Scenario: Successful application launch
- **WHEN** user executes the desktop launcher
- **THEN** the FastAPI server starts in a background thread
- **AND** a native window opens displaying the application interface
- **AND** the window shows the application at the correct localhost URL

### Requirement: Native window configuration
The launcher SHALL create a native window with appropriate default dimensions and behavior.

#### Scenario: Window opens with correct settings
- **WHEN** the native window is created
- **THEN** the window has a width of 1280 pixels and height of 800 pixels
- **AND** the window is resizable
- **AND** the window has a minimum size of 800x600 pixels
- **AND** the window title is "Backlogia"

### Requirement: Server startup verification
The launcher SHALL verify that the FastAPI server is responding before opening the native window.

#### Scenario: Server ready before window opens
- **WHEN** the server thread is started
- **THEN** the launcher polls the server port for connectivity
- **AND** waits until a successful connection is established
- **AND** only then creates and displays the native window

#### Scenario: Server fails to start within timeout
- **WHEN** the server does not respond within 10 seconds
- **THEN** the launcher SHALL display an error message
- **AND** exit with a non-zero status code

### Requirement: PyWebView integration
The launcher SHALL use PyWebView to create and manage the native window.

#### Scenario: Window uses native webview
- **WHEN** the window is created on Windows
- **THEN** it uses Edge WebView2 as the rendering engine
- **WHEN** the window is created on macOS
- **THEN** it uses WebKit as the rendering engine
- **WHEN** the window is created on Linux
- **THEN** it uses GTK WebKit as the rendering engine

### Requirement: Single process operation
The launcher and server SHALL run in a single Python process with the server in a daemon thread.

#### Scenario: Server runs as daemon thread
- **WHEN** the launcher starts the server
- **THEN** the server runs in a daemon thread
- **AND** the thread does not block the main process
- **AND** the thread terminates when the main process exits

### Requirement: Clean process termination
The launcher SHALL exit cleanly when the native window is closed.

#### Scenario: Window closure terminates application
- **WHEN** user closes the native window
- **THEN** the PyWebView event loop exits
- **AND** the main process terminates
- **AND** the daemon server thread terminates automatically
- **AND** the application prints a closure confirmation message
