## Context

Backlogia is currently a FastAPI web application that requires users to manually start a server (`python -m uvicorn`) and navigate to `localhost` in their browser. This creates friction for non-technical users who just want to use the application.

**Current State:**
- FastAPI backend with multiple routes (library, sync, settings, etc.)
- Jinja2 templates for frontend
- SQLite database for game library
- Multi-store game detection (Steam, Epic, GOG, etc.)
- IGDB and Metacritic metadata sync

**Constraints:**
- Must minimize changes to existing codebase
- Should preserve existing functionality (pip install, manual server mode)
- Need cross-platform support (Windows primary, macOS/Linux secondary)
- Limited development resources (solo developer)

**Stakeholders:**
- End users: Want simple, one-click experience
- Developer: Wants minimal maintenance burden
- Advanced users: May still prefer manual server control

## Goals / Non-Goals

**Goals:**
- Create a desktop launcher that starts the application with one click
- Wrap existing FastAPI app in a native window (no browser required)
- Automatic port allocation to avoid conflicts
- Graceful shutdown when window closes
- Simple executable packaging for distribution
- Preserve all existing functionality

**Non-Goals:**
- Complete rewrite of the application
- Advanced system integration (system tray, notifications, auto-start) - can be added later
- Code signing and auto-update in initial version
- Changes to database schema or API contracts
- Native mobile apps or web deployment changes

## Decisions

### 1. Desktop Framework: PyWebView

**Decision:** Use PyWebView instead of Electron, Tauri, or other frameworks.

**Rationale:**
- **100% Python**: No need to learn Rust (Tauri) or JavaScript (Electron)
- **Minimal changes**: Existing FastAPI app works as-is
- **Lightweight**: ~3MB library, uses native webview (Edge WebView2 on Windows)
- **Simple integration**: ~70 lines of launcher code

**Alternatives Considered:**
- **Electron**: Rejected - requires JavaScript/TypeScript, 150MB+ bundle size, overkill for our needs
- **Tauri**: Rejected - requires learning Rust, more complex IPC bridge, though lightweight
- **CEFPython**: Rejected - unmaintained, complex build process
- **Manual browser**: Current state - rejected due to poor UX

**Trade-offs:**
- Depends on system webview (Edge WebView2 on Windows) - requires WebView2 runtime installed
- Less control over webview compared to embedded Chromium (Electron/CEF)
- Limited API compared to full desktop frameworks

### 2. Server Architecture: Threaded uvicorn

**Decision:** Run FastAPI server in a daemon thread within the same process.

**Rationale:**
- **Simplicity**: Single process, no IPC complexity
- **Clean lifecycle**: Server dies when main process exits
- **No changes needed**: Existing FastAPI app works without modification
- **Fast startup**: No subprocess spawn overhead

**Alternatives Considered:**
- **Subprocess**: Rejected - more complex lifecycle management, IPC needed for shutdown
- **Separate process**: Rejected - requires process monitoring, port file management
- **Async event loop**: Rejected - would require rewriting main launcher logic

**Implementation:**
```python
server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
server_thread.start()
```

**Trade-offs:**
- Daemon thread doesn't allow graceful FastAPI shutdown (acceptable for desktop use)
- Can't easily restart server without restarting entire app
- Thread-safety considerations if we add server control APIs later

### 3. Port Management: Dynamic Allocation

**Decision:** Find first available port starting from 8000, fail if none found in reasonable range.

**Rationale:**
- **Avoids conflicts**: Users may have other apps on port 8000
- **No configuration**: Works out of the box
- **Deterministic**: Tries ports sequentially, not random

**Implementation:**
```python
def find_free_port(start_port=8000, max_attempts=100):
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError("Could not find a free port")
```

**Alternatives Considered:**
- **Fixed port**: Rejected - causes conflicts
- **Random port**: Rejected - less deterministic, harder to debug
- **Port configuration file**: Rejected - adds complexity for minimal benefit

### 4. Packaging: PyInstaller

**Decision:** Use PyInstaller for creating standalone executables.

**Rationale:**
- **Mature**: Well-established, good Python 3.13 support
- **Simple**: Single command to build
- **Cross-platform**: Works on Windows, macOS, Linux
- **Bundle everything**: Includes Python runtime, all dependencies

**Alternatives Considered:**
- **Nuitka**: Rejected - complex compilation, not needed for our use case
- **py2exe**: Rejected - Windows-only, less maintained
- **cx_Freeze**: Rejected - more complex, less popular

**Configuration:**
```python
# pyinstaller.spec (to be created)
- Include all templates, static files
- Bundle Python runtime
- Set appropriate icons
- Configure for one-file vs one-folder distribution
```

**Trade-offs:**
- Larger executable (~30-50MB) vs pip package (~5MB)
- Slower startup (unpacking) with --onefile mode
- Antivirus false positives possible (common with PyInstaller)

### 5. Startup Sequence

**Decision:** Server starts → wait for ready → open window.

**Implementation:**
```python
1. Find free port
2. Start server thread
3. Poll port until connection succeeds (max 10s)
4. Create webview window
5. webview.start() blocks until window closes
6. Process exits, daemon thread terminates
```

**Rationale:**
- **Reliable**: Ensures server is actually responding before opening window
- **Fast**: 10s timeout catches startup failures quickly
- **Simple**: Linear flow, easy to debug

**Trade-offs:**
- Blocking wait during startup (acceptable - typically <1s)
- No loading screen (window opens when ready)
- Can't show server logs in GUI (acceptable for v1)

## Risks / Trade-offs

### Technical Risks

**[Risk]** WebView2 runtime not installed on Windows
→ **Mitigation:** Check for WebView2 presence, show clear error message with download link. Consider bundling WebView2 bootstrapper in installer.

**[Risk]** Port exhaustion (all ports 8000-8099 taken)
→ **Mitigation:** 100 port attempts should be sufficient. Show clear error message. Could add config file for advanced users to specify port range.

**[Risk]** PyWebView compatibility issues on Linux (different distros use different webview backends)
→ **Mitigation:** Document supported distros (Ubuntu, Fedora). Provide troubleshooting guide for installing webkit2gtk.

**[Risk]** PyInstaller executable flagged by antivirus
→ **Mitigation:** Document issue in README. Consider code signing (costs money). Provide pip install as alternative.

**[Risk]** Database file permissions when running as bundled app
→ **Mitigation:** Use standard user data directories. Test thoroughly on all platforms.

### User Experience Trade-offs

**[Trade-off]** No browser DevTools easily accessible
→ **Impact:** Harder to debug for users. Consider adding debug mode flag.

**[Trade-off]** Larger download size (executable vs pip)
→ **Impact:** Acceptable for target audience (non-technical users). Keep pip install for devs.

**[Trade-off]** Can't have multiple windows/tabs of same app
→ **Impact:** Single window only. Acceptable for this use case.

### Maintenance Trade-offs

**[Trade-off]** Need to build binaries for each platform
→ **Impact:** More CI/CD complexity. Start with Windows only, add others later.

**[Trade-off]** Two distribution methods (pip + binaries)
→ **Impact:** More documentation needed. Worth it for target audience reach.

## Migration Plan

### Phase 1: Development (Current)
1. ✅ Create `desktop.py` launcher
2. Install pywebview dependency
3. Test on development machine

### Phase 2: Refinement
1. Add error handling (port conflicts, server startup failures)
2. Add window icon and splash screen
3. Test WebView2 detection on Windows
4. Create PyInstaller spec file
5. Test bundled executable locally

### Phase 3: Cross-Platform Testing
1. Test on clean Windows VM
2. Test on macOS (if available)
3. Test on Ubuntu/Linux (if available)
4. Document platform-specific requirements

### Phase 4: Distribution Setup
1. Update requirements.txt with pywebview
2. Create build scripts for PyInstaller
3. Set up GitHub Actions for automated builds
4. Create releases with downloadable executables
5. Update README with installation instructions for both methods

### Phase 5: Documentation
1. Add "Download" section to README with binary links
2. Document system requirements (WebView2 on Windows, etc.)
3. Create troubleshooting guide
4. Update CHANGELOG

### Rollback Strategy
- Pip install method remains unchanged - always available as fallback
- No breaking changes to database or config files
- Users can switch between desktop app and manual server at any time
- No forced migration

### Backwards Compatibility
- Existing `python -m uvicorn web.main:app` method still works
- Database files remain in same location
- Config files unchanged
- No API changes

## Open Questions

1. **Window icon**: What icon should we use? Need .ico for Windows, .icns for macOS
   - *Proposal*: Create from existing web favicon

2. **Installer vs portable**: Should we create a proper installer (.msi) or just a portable .exe?
   - *Proposal*: Start with portable .exe (simpler), add installer later if needed

3. **Auto-update mechanism**: Should v1 include auto-update?
   - *Proposal*: No - add in v2 after stability proven. Manual download for now.

4. **Debug mode**: How should users access logs if something goes wrong?
   - *Proposal*: Add `--debug` flag that shows console window and enables verbose logging

5. **Multiple instances**: Should we prevent/allow multiple app instances?
   - *Proposal*: Allow for now (different ports), add single-instance lock later if needed

6. **macOS/Linux priority**: Which platform after Windows?
   - *Proposal*: Test on both, prioritize based on user requests

7. **Code signing**: Worth the cost (~$200-300/year)?
   - *Proposal*: Not for v1. Reassess if antivirus issues are widespread.
