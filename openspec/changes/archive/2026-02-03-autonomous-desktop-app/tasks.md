## 1. Desktop Launcher Implementation

- [x] 1.1 Create desktop.py launcher script
- [x] 1.2 Implement find_free_port() function with 100 port range
- [x] 1.3 Implement run_server() function with uvicorn configuration
- [x] 1.4 Implement server readiness polling with 10s timeout
- [x] 1.5 Create PyWebView window with correct dimensions (1280x800, min 800x600)
- [x] 1.6 Configure server for daemon thread operation
- [x] 1.7 Add startup status messages ([OK]/[FAIL] format)
- [x] 1.8 Add error handling for port allocation failures
- [x] 1.9 Add error handling for server startup failures
- [x] 1.10 Add error handling for webview creation failures

## 2. Dependencies and Requirements

- [x] 2.1 Add pywebview to requirements.txt
- [x] 2.2 Add pyinstaller to build requirements (requirements-build.txt or similar)
- [x] 2.3 Document WebView2 runtime requirement for Windows in README
- [x] 2.4 Document webkit2gtk requirement for Linux in README

## 3. PyInstaller Configuration

- [x] 3.1 Create pyinstaller.spec file
- [x] 3.2 Configure data files inclusion (static/, templates/)
- [x] 3.3 Configure hidden imports for FastAPI and dependencies
- [x] 3.4 Set application icon paths (Windows .ico, macOS .icns)
- [x] 3.5 Configure one-folder distribution mode
- [x] 3.6 Test executable generation locally
- [x] 3.7 Create build script (build.py or build.sh)
- [x] 3.8 Add clean command to remove build artifacts

## 4. Backend Server Adaptation

- [x] 4.1 Verify CORS configuration allows localhost origins
- [x] 4.2 Test all routes work correctly in threaded mode
- [x] 4.3 Verify database operations are thread-safe
- [x] 4.4 Test sync operations work in background thread

## 5. Icon and Branding

- [x] 5.1 Create or adapt application icon
- [x] 5.2 Generate .ico file for Windows (multiple sizes: 16,32,48,256)
- [x] 5.3 Generate .icns file for macOS
- [x] 5.4 Add icon to static assets
- [x] 5.5 Update window title if needed

## 6. Testing

- [x] 6.1 Test desktop launcher on Windows
- [x] 6.2 Test port conflict handling (occupy port 8000 first)
- [x] 6.3 Test server startup timeout handling
- [x] 6.4 Test window close gracefully terminates app
- [x] 6.5 Test multiple app instances use different ports
- [x] 6.6 Test WebView2 presence detection on Windows
- [~] 6.7 Test on macOS (if available) - *Not planned: requires macOS system*
- [~] 6.8 Test on Linux Ubuntu/Fedora (if available) - *Not planned: requires Linux system*

## 7. Executable Packaging

- [x] 7.1 Build Windows executable with PyInstaller
- [x] 7.2 Test executable on clean Windows system (without Python)
- [x] 7.3 Verify executable size is under 100MB
- [x] 7.4 Test executable includes all static files
- [x] 7.5 Test executable database file creation/access
- [x] 7.6 Build macOS executable (if available)
- [x] 7.7 Build Linux executable (if available)

## 8. Documentation

- [x] 8.1 Update README with desktop app download section
- [x] 8.2 Document system requirements (OS versions, WebView2, etc.)
- [x] 8.3 Create troubleshooting guide for common issues
- [x] 8.4 Document build process for developers
- [x] 8.5 Update CHANGELOG with new desktop launcher feature
- [~] 8.6 Add screenshots of desktop app to docs/ - *Not planned: can be added in future release*
- [x] 8.7 Document both installation methods (pip vs executable)

## 9. Distribution Setup

- [x] 9.1 Create GitHub release workflow
- [x] 9.2 Configure GitHub Actions to build executables
- [x] 9.3 Add Windows build job to CI
- [x] 9.4 Add macOS build job to CI (if supported)
- [x] 9.5 Add Linux build job to CI (if supported)
- [x] 9.6 Configure artifact upload to releases
- [x] 9.7 Test automated build process

## 10. Optional Enhancements

- [~] 10.1 Add --debug flag for verbose logging - *Not planned: can be added in future release*
- [~] 10.2 Add command-line argument for custom port range - *Not planned: can be added in future release*
- [x] 10.3 Add splash screen while server starts
- [x] 10.4 Add system tray icon support
- [x] 10.5 Add minimize-to-tray functionality
- [x] 10.6 Add single-instance lock to prevent multiple copies
- [~] 10.7 Consider code signing for Windows/macOS - *Not planned: future consideration*
