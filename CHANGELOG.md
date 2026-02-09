# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Editable local games paths in Settings UI (non-Docker)**: Users running Backlogia locally can now configure game folder paths directly from the Settings page without needing to edit environment variables or .env files
- **Docker deployment detection**: Automatically detects Docker environment and adapts UI accordingly

### Changed
- Settings UI now conditionally renders based on deployment mode:
  - **Non-Docker**: Editable input field for `LOCAL_GAMES_PATHS` with database storage
  - **Docker**: Read-only display with instructions for configuring via `.env` and `docker-compose.yml`
- Docker deployments prevent `LOCAL_GAMES_PATHS` from being saved through the UI (paths must be volume-mounted)
- Settings template updated with deployment-specific instructions and help text

### Technical Details
- Modified `web/routes/settings.py` to detect Docker environment using `/.dockerenv` file
- Added conditional rendering in `web/templates/settings.html` based on `is_docker` flag
- POST handler skips `LOCAL_GAMES_PATHS` database save in Docker mode
- Added `.copilot-docs/` to `.gitignore` for development documentation
