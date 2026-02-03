## ADDED Requirements

### Requirement: PyInstaller executable generation
The system SHALL provide configuration to generate standalone executables using PyInstaller.

#### Scenario: Executable builds successfully
- **WHEN** running PyInstaller with the project configuration
- **THEN** a standalone executable SHALL be generated
- **AND** the executable SHALL include the Python runtime
- **AND** all dependencies SHALL be bundled

### Requirement: Static files inclusion
The executable SHALL include all required static files and templates.

#### Scenario: Web assets are bundled
- **WHEN** the executable is built
- **THEN** all files in web/static/ SHALL be included
- **AND** all files in web/templates/ SHALL be included
- **AND** the application SHALL be able to locate these files at runtime

### Requirement: Platform-specific builds
The packaging process SHALL support generating executables for Windows, macOS, and Linux.

#### Scenario: Windows executable
- **WHEN** building on Windows
- **THEN** an .exe file SHALL be generated
- **AND** it SHALL run on Windows without requiring Python installation

#### Scenario: macOS executable
- **WHEN** building on macOS
- **THEN** a macOS application bundle SHALL be generated
- **AND** it SHALL run on macOS without requiring Python installation

#### Scenario: Linux executable
- **WHEN** building on Linux
- **THEN** a Linux binary SHALL be generated
- **AND** it SHALL run on compatible Linux distributions without requiring Python installation

### Requirement: Icon configuration
The packaged executable SHALL have an appropriate application icon.

#### Scenario: Windows executable has icon
- **WHEN** the Windows executable is built
- **THEN** it SHALL have a .ico icon file
- **AND** the icon SHALL appear in Windows Explorer

#### Scenario: macOS executable has icon
- **WHEN** the macOS executable is built
- **THEN** it SHALL have a .icns icon file
- **AND** the icon SHALL appear in Finder and the Dock

### Requirement: Dependency bundling
The executable SHALL bundle all Python dependencies including PyWebView and FastAPI.

#### Scenario: All dependencies included
- **WHEN** the executable runs
- **THEN** it SHALL NOT require any external Python packages
- **AND** pywebview SHALL be bundled
- **AND** fastapi and uvicorn SHALL be bundled
- **AND** all other requirements.txt dependencies SHALL be bundled

### Requirement: Executable size optimization
The packaging configuration SHALL optimize for reasonable executable size.

#### Scenario: Executable size is acceptable
- **WHEN** the executable is built
- **THEN** the total size SHALL be less than 100MB for single-file distribution
- **AND** the size SHALL be less than 80MB for one-folder distribution

### Requirement: Build script automation
The system SHALL provide automated build scripts for generating executables.

#### Scenario: Build script executes successfully
- **WHEN** the build script is run
- **THEN** it SHALL install PyInstaller if not present
- **AND** execute PyInstaller with the correct configuration
- **AND** output the executable to a dist/ directory
- **AND** report build success or failure clearly
