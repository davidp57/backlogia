## Why

Backlogia currently requires users to manually start a server and navigate to localhost in their browser, creating friction in the user experience. Users want a simple, double-click application that runs autonomously without needing to understand servers, ports, or browser navigation. Transforming Backlogia into a standalone desktop application will make it accessible to a broader audience while minimizing changes to the existing codebase.

## What Changes

- **Desktop window wrapper** — Use PyWebView to wrap the existing FastAPI application in a native window (100% Python, no new languages)
- **Autonomous startup** — Single Python script that starts the FastAPI server in a thread and opens the native window
- **Minimal code changes** — Existing FastAPI backend and frontend remain unchanged, only add a launcher layer
- **Embedded backend** — FastAPI server runs in a background thread within the same Python process
- **Simple packaging** — Use PyInstaller to create standalone executables (.exe for Windows, binaries for macOS/Linux)
- **Auto port allocation** — Find available port automatically on startup
- **System tray option** — Optional system tray icon for background operation
- **Graceful shutdown** — Clean server shutdown when window closes
- **No browser dependency** — Uses native webview (Edge WebView2 on Windows, WebKit on macOS, GTK WebKit on Linux)

## Capabilities

### New Capabilities

- `desktop-launcher`: PyWebView-based launcher that starts FastAPI in a thread and displays it in a native window
- `auto-port-management`: Automatic port detection and allocation on startup to avoid conflicts
- `executable-packaging`: PyInstaller configuration to bundle the application into standalone executables
- `graceful-lifecycle`: Proper startup and shutdown sequences for the embedded server

### Modified Capabilities

- `backend-server`: FastAPI server adapted to run in a background thread with dynamic port allocation (minimal changes to existing routes)

## Impact

**Code Changes:**
- New launcher script (`desktop.py` or similar) - ~50-100 lines
- Minor adaptation to `main.py` to support threaded operation
- Optional: Port allocation utility function
- Minimal or no changes to existing routes, services, or frontend

**Dependencies:**
- Add `pywebview` (~3MB)
- Add `PyInstaller` (build-time only)
- Platform-specific webview dependencies (Edge WebView2 runtime on Windows, already installed on most systems)

**Build Process:**
- Simple PyInstaller build script
- No code signing required initially (though recommended for production)
- Single command to build executable

**User Experience:**
- Smooth transition: same interface, just launched differently
- Existing databases and settings work as-is (same file paths)
- Installation via executable instead of pip (optional: keep pip install for advanced users)

**Distribution:**
- Dual distribution: PyPI package (existing) + binary releases (new)
- Download size: ~30-50MB (vs. ~5MB for pip package)

**Testing:**
- Minimal new tests: launcher startup/shutdown
- Existing tests remain valid
- Manual testing on each platform for webview compatibility

**Backwards Compatibility:**
- Existing manual server start method still works
- No breaking changes to data formats or APIs
- Users can choose between desktop app or manual server mode
