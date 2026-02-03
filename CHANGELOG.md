# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Desktop Application Mode**: Backlogia can now run as a standalone desktop application
  - PyWebView-based native window wrapper for Windows, macOS, and Linux
  - Automatic server startup and port management
  - Elegant loading screen with animated gradient design
  - **Single instance lock** - Prevents multiple instances from running simultaneously
  - **System tray icon** - Optional tray menu for quick access (requires pystray)
- Desktop executable packaging with PyInstaller
  - One-folder distribution with all dependencies bundled
  - Custom application icon
  - Windows GUI mode (no console window)
  - Persistent data storage in user directories (`%APPDATA%\Backlogia` on Windows)
- Automated build script (`build.py`) for creating desktop executables
- Loading screen route (`/loading`) for smooth app startup experience
- Enhanced bookmarklet UI detection for desktop vs browser mode

### Changed
- Settings page now shows different bookmarklet instructions for desktop app users
- Application data directory logic updated to support both dev and frozen (PyInstaller) modes
- Log files now stored in `%APPDATA%\Backlogia\logs\` when running as desktop app

### Technical
- Added `desktop.py` launcher with threading-based server management
- Added PyInstaller configuration (`backlogia.spec`)
- Added development dependencies: `pywebview`, `pyinstaller`
- Server startup now waits for port availability before showing window
- Loading screen served via FastAPI endpoint for better compatibility

## [0.1.0] - Previous Version

### Added
- Initial release with web-based game library management
- Support for multiple game stores (Steam, GOG, Epic, etc.)
- IGDB integration for game metadata
- Collections and custom organization
- Bookmarklet for quick game additions
