# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Editable local games paths in Settings UI**: Users can now configure local game folder paths directly from the Settings page without needing to edit environment variables or .env files

### Changed
- `LOCAL_GAMES_PATHS` setting is now editable through the web interface and stored in the database
- Settings template updated to show an input field for local games paths instead of read-only display
- Docker users can still use `LOCAL_GAMES_DIR_1`, `LOCAL_GAMES_DIR_2`, etc. environment variables (these take precedence)

### Technical Details
- Modified `web/routes/settings.py` to handle saving and loading `LOCAL_GAMES_PATHS` from database
- Updated `web/templates/settings.html` to provide an editable text input for local games paths
- Added `.copilot-docs/` to `.gitignore` for development documentation
