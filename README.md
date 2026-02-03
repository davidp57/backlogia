# Backlogia

**Your entire game library, finally in one place.**

Stop jumping between Steam, Epic, GOG, Amazon, and a dozen other launchers just to see what you own. Backlogia aggregates all your games into a single, beautifully organized library with rich metadata, ratings, and discovery features—all running locally on your machine.

![Library View](docs/images/library.png)

---

## Supported Stores

<p align="center">
  <img src="web/static/images/steam-100.png" alt="Steam" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/epic-100.png" alt="Epic Games" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/gog-48.png" alt="GOG" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/amazon-120.png" alt="Amazon Games" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/itch-90.png" alt="itch.io" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/humble-96.png" alt="Humble Bundle" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/battlenet-100.png" alt="Battle.net" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/ea-256.png" alt="EA" width="48" height="48" style="margin: 0 10px;">
  <img src="web/static/images/ubisoft-96.png" alt="Ubisoft" width="48" height="48" style="margin: 0 10px;">
</p>

<p align="center">
  <strong>Steam</strong> &nbsp;•&nbsp; <strong>Epic Games</strong> &nbsp;•&nbsp; <strong>GOG</strong> &nbsp;•&nbsp; <strong>Amazon Games</strong> &nbsp;•&nbsp; <strong>itch.io</strong> &nbsp;•&nbsp; <strong>Humble Bundle</strong> &nbsp;•&nbsp; <strong>Battle.net</strong> &nbsp;•&nbsp; <strong>EA</strong> &nbsp;•&nbsp; <strong>Ubisoft</strong>
</p>

Please vote for which stores you would like to see supported next [here](https://github.com/sam1am/backlogia/discussions/1).

---

## Features

### Unified Library

All your games from every store, displayed in one place. Smart deduplication ensures games you own on multiple platforms appear as a single entry with all your purchase information intact.

![Library](docs/images/library.png)

- **Multi-store filtering** — Filter by store, genre, or search by name
- **Flexible sorting** — Sort by name, rating, playtime, or release date
- **Store indicators** — See at a glance which platforms you own each game on

### Rich Game Details

Every game is enriched with metadata from IGDB (Internet Game Database), giving you consistent information across all stores.

![Game Details](docs/images/game_preview.png)

- **Ratings** — Community ratings, critic scores, and aggregated scores
- **Screenshots** — High-quality screenshots from IGDB
- **Direct store links** — Jump straight to any store page
- **Playtime tracking** — See your Steam playtime stats

### Discover Your Library

Find your next game to play with curated discovery sections based on your actual library.

![Discover](docs/images/discover.png)

![Discover Sections](docs/images/discover_sections.png)

- **Popular games** — Based on IGDB popularity metrics
- **Highly rated** — Games scoring 90+ ratings
- **Hidden gems** — Quality games that deserve more attention
- **Most played** — Your games ranked by playtime
- **Random pick** — Can't decide? Let Backlogia choose for you

### Custom Collections

Organize games your way with custom collections that work across all stores.

![Collections](docs/images/collections.png)

- Create themed collections like "Weekend Playlist" or "Couch Co-op"
- Add games from any store to any collection
- Visual collection covers with game thumbnails

### Settings & Sync

Connect your accounts and sync your library with a single click.

![Settings](docs/images/settings.png)

- One-click sync per store or sync everything at once
- Secure credential storage
- IGDB integration for metadata enrichment

---

## Installation

### Option 1: Desktop Application (Recommended for Windows)

The easiest way to use Backlogia is with the standalone desktop application.

1. **Download the latest release**
   - Go to the [Releases page](https://github.com/sam1am/backlogia/releases)
   - Download `Backlogia-Windows.zip` for Windows
   - Download `Backlogia-macOS.zip` for macOS (if available)
   - Download `Backlogia-Linux.tar.gz` for Linux (if available)

2. **Extract and run**
   - Extract the archive to a folder of your choice
   - Run `Backlogia.exe` (Windows) or the appropriate executable
   - The application will open in a native window with a loading screen
   - Your game library data is stored in `%APPDATA%\Backlogia` (Windows) or equivalent user directory

3. **Configure your stores**
   - Go to Settings to connect your game store accounts
   - See [Configuration](#configuration) for details

#### System Requirements

**Windows:**
- Windows 10 or later
- Microsoft Edge WebView2 Runtime (usually pre-installed on Windows 11)
  - If missing, download from [Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/)

**macOS:**
- macOS 10.15 (Catalina) or later
- WebKit (built-in)

**Linux:**
- Ubuntu 20.04+ / Fedora 35+ or equivalent
- WebKitGTK 2.0: `sudo apt install gir1.2-webkit2-4.0` (Ubuntu/Debian)

### Option 2: Docker

For running Backlogia as a server (accessible from multiple devices):

1. **Clone the repository**
   ```bash
   git clone https://github.com/sam1am/backlogia.git
   cd backlogia
   ```

2. **Create your environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your API credentials** (see [Configuration](#configuration))

4. **Start the container**
   ```bash
   docker compose up -d
   ```

5. **Access Backlogia** at [http://localhost:5050](http://localhost:5050)

#### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `./data:/data` | Database and persistent storage |
| `./data/legendary:/root/.config/legendary` | Epic Games authentication cache |
| `./data/nile:/root/.config/nile` | Amazon Games authentication cache |
| `${GOG_DB_DIR}:/gog:ro` | GOG Galaxy database (read-only) |

#### Updating

To update Backlogia to the latest version:

```bash
git pull
docker compose down
docker compose up -d --build
```

### Option 3: Python/pip (For Developers)

For development or if you prefer running from source:

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/backlogia.git
   cd backlogia
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create your environment file**
   ```bash
   cp .env.example .env
   ```

5. **Edit `.env` with your API credentials** (see [Configuration](#configuration))

6. **Run the desktop launcher**
   ```bash
   python desktop.py
   ```

   Or run as a web server:
   ```bash
   python -m uvicorn web.main:app --host 127.0.0.1 --port 5050
   ```

7. **Access Backlogia** in the native window or at [http://localhost:5050](http://localhost:5050)

#### Updating

To update Backlogia to the latest version:

```bash
git pull
pip install -r requirements.txt
```

Then restart the application.

### Building the Desktop Application

To build the standalone executable yourself:

1. **Install build dependencies**
   ```bash
   pip install -r requirements-build.txt
   ```

2. **Run the build script**
   ```bash
   python build.py
   ```

3. **The executable will be in `dist/Backlogia/`**
   ```bash
   dist\Backlogia\Backlogia.exe  # Windows
   ```

---

## Troubleshooting

### Desktop Application Issues

**Windows: "Edge WebView2 not found"**
- Download and install [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)

**All ports in use error**
- Close some applications and try again
- The launcher tries ports 8000-8099 automatically

**Server failed to start**
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Run `python desktop.py` from the terminal to see error messages

**Linux: "webkit2gtk not found"**
- Ubuntu/Debian: `sudo apt install gir1.2-webkit2-4.0 python3-gi`
- Fedora: `sudo dnf install webkit2gtk3 python3-gobject`

**Application window is blank**
- Wait a few seconds for the server to fully start
- Check console output for errors
- Try running in web server mode to diagnose: `python -m uvicorn web.main:app`

---

## Configuration

Configure all store connections through the **Settings** page in Backlogia. Each store section includes step-by-step instructions for obtaining the required credentials.

### Where to Get Credentials

| Store | Credential Source |
|-------|-------------------|
| **Steam** | [Steam Web API](https://steamcommunity.com/dev/apikey) for API key |
| **IGDB** | [Twitch Developer Console](https://dev.twitch.tv/console/apps) (IGDB uses Twitch auth) |
| **Epic Games** | OAuth flow in Settings page |
| **GOG** | Reads from local GOG Galaxy database OR uses bookmarklet import (instructions in Settings) |
| **itch.io** | [itch.io API Keys](https://itch.io/user/settings/api-keys) |
| **Humble Bundle** | Session cookie from browser (instructions in Settings) |
| **Battle.net** | Session cookie from browser (instructions in Settings) |
| **Amazon** | OAuth flow in Settings page |
| **EA** | Bearer token via JavaScript snippet (instructions in Settings) |
| **Ubisoft** | Bookmarklet import from account.ubisoft.com (instructions in Settings) |

---

## Tech Stack

- **Backend**: FastAPI (Python)
- **Desktop**: PyWebView (native window wrapper)
- **Database**: SQLite
- **Frontend**: Jinja2 templates, vanilla JavaScript
- **Metadata**: IGDB API integration
- **Packaging**: PyInstaller
- **Deployment**: Docker + Docker Compose

---

## Acknowledgements

Backlogia is built on the shoulders of these excellent open-source projects:

- **[Legendary](https://github.com/derrod/legendary)** — Epic Games Store integration
- **[Nile](https://github.com/imLinguin/nile)** — Amazon Games integration
- **[PlayniteExtensions](https://github.com/Jeshibu/PlayniteExtensions)** — EA library integration method

---

## License

MIT License - See [LICENSE](LICENSE) for details.
