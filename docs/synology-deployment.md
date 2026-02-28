# Deploying Backlogia on Synology NAS

This guide explains how to deploy Backlogia on a Synology NAS using Docker/Container Manager.

## Prerequisites

- Synology NAS with DSM 7.0 or higher
- **Container Manager** package installed (via Package Center)
- At least 2 GB of free disk space
- Administrator access to the NAS

## Target Architecture

- **Supported CPU:** AMD64/x86_64 (Intel/AMD)
- **Docker Image:** ~500 MB - 1 GB
- **Port:** 5050 (HTTP)
- **Database:** SQLite (stored in `/data` volume)

---

## Method A: Via Synology Container Manager UI (Recommended)

This method uses Synology's graphical interface and requires **no command line**.

### Step 1: Download the Docker Image

1. Open the project's GitHub repository: https://github.com/[YOUR-USERNAME]/backlogia
2. Go to the **Actions** tab (top)
3. Select the **"Build Docker Image for Synology"** workflow
4. Click on the latest successful run (✅)
5. Scroll down to the **Artifacts** section
6. Download `backlogia-docker-image.zip`
7. Extract the file to get `backlogia.tar.gz`

> **Note:** Artifacts are kept for 30 days. If no artifact is available, manually trigger the workflow using the "Run workflow" button.

### Step 2: Transfer the Image to the NAS

**Option A: Via File Station (web interface)**
1. Open **File Station** on DSM
2. Create a folder to store the image (e.g., `/docker/images`)
3. Upload `backlogia.tar.gz` to this folder

**Option B: Via SFTP**
```bash
# From your PC
scp backlogia.tar.gz admin@[NAS-IP]:/volume1/docker/images/
```

### Step 3: Import the Image into Container Manager

1. Open **Container Manager** (formerly "Docker")
2. Go to the **Image** tab
3. Click the **Add** button (dropdown in top right)
4. Select **Add from File**
5. Browse and select `backlogia.tar.gz`
6. Wait for the import (may take 2-5 minutes)
7. Verify that the `backlogia:latest` image appears in the list

### Step 4: Create Data Directories

Create a folder to store Backlogia's persistent data:

**Via File Station:**
1. Open **File Station**
2. Create the folder `/docker/backlogia` (or `/volume1/docker/backlogia`)
3. Create subfolders:
   - `/docker/backlogia/data`
   - `/docker/backlogia/logs`

**Via SSH (optional):**
```bash
mkdir -p /volume1/docker/backlogia/data
mkdir -p /volume1/docker/backlogia/logs
```

### Step 5: Create and Configure the Container

1. In **Container Manager**, go to the **Container** tab
2. Click **Create**
3. Select the `backlogia:latest` image
4. Click **Next**

#### General Configuration
- **Container Name:** `backlogia`
- **Resource Limitation:** (leave as default)

#### Port Configuration
Click **Add** in the **Port Settings** section:
- **Local Port:** `5050`
- **Container Port:** `5050`
- **Type:** TCP

#### Volume Configuration
Click **Add Folder** for each volume:

| Folder (File/Folder) | Mount Path | Mode |
|---|---|---|
| `/docker/backlogia/data` | `/data` | Read/Write |
| `/docker/backlogia/data` | `/root/.config/legendary` | Read/Write |
| `/docker/backlogia/data` | `/root/.config/nile` | Read/Write |
| `/docker/backlogia/logs` | `/app/logs` | Read/Write |

> **Optional:** If you have local games on the NAS, add them in **Read Only** mode:
> - `/volume1/games` → `/local-games-1` (Read Only)
> - `/volume2/media/games` → `/local-games-2` (Read Only)

#### Environment Variables
Click **Add** in the **Environment** section:

| Variable | Value |
|---|---|
| `DATABASE_PATH` | `/data/game_library.db` |
| `PORT` | `5050` |
| `DEBUG` | `false` |

> **Note:** API keys (Steam, IGDB, itch.io, etc.) are NOT configured here. They will be configured via the web interface after first startup.

#### Advanced Options
In the **Advanced Settings** tab:
- **Auto-restart:** Enable (Always restart)
- **Enable resource limitation:** (optional, based on your needs)

5. Click **Done**

### Step 6: Start the Container

1. In the container list, select `backlogia`
2. Click **Action** → **Start**
3. Wait a few seconds for the container to start
4. The status should change to **Running** (✅)

### Step 7: Access Backlogia

1. Open a web browser
2. Go to: `http://[NAS-IP]:5050`
3. The Backlogia interface should appear

> **Example:** If your NAS IP is `192.168.1.100`, go to `http://192.168.1.100:5050`

### Step 8: Configure API Keys

1. In the Backlogia interface, click **Settings** (top right)
2. Fill in the API keys for the stores you use:

| Store | How to get the key |
|---|---|
| **Steam** | Get an API key from https://steamcommunity.com/dev/apikey |
| **IGDB** | Create an account at https://api-docs.igdb.com/ |
| **itch.io** | Generate a key at https://itch.io/user/settings/api-keys |
| **Humble Bundle** | Copy the session cookie from your browser |
| **Battle.net** | Copy the session cookie from your browser |
| **Epic Games** | Authentication via OAuth (button in the interface) |
| **Amazon Games** | Authentication via Nile (button in the interface) |

3. Click **Save**

### Step 9: Sync Your Libraries

1. In the Backlogia interface, go to **Library**
2. Click **Sync** for each configured store
3. Wait for synchronization (may take a few minutes depending on library size)
4. Games should appear in your library

---

## Updating Backlogia

### Via Container Manager UI

1. **Download the new image:**
   - GitHub → Actions → Download the latest `backlogia-docker-image.zip` artifact
   - Extract `backlogia.tar.gz`

2. **Import the new image:**
   - Container Manager → Image → Add from File
   - Select the new `backlogia.tar.gz`

3. **Restart with the new image:**
   - Container Manager → Container → Select `backlogia`
   - Action → Stop
   - Action → Clear (delete container, **NOT the image**)
   - Recreate the container following Step 5 above
   - Volumes and data will be preserved

> **Important:** Deleting the container does NOT delete data. Volumes mounted in `/docker/backlogia/data` are preserved.

---

## Method B: Via Docker Compose Command Line

For advanced users who prefer using SSH and the command line.

### Prerequisites
- SSH enabled on the NAS (Control Panel → Terminal & SNMP)
- Root access or user in the `docker` group

### Step 1: Download and Import the Image

```bash
# Connect to NAS via SSH
ssh admin@[NAS-IP]

# Go to a working directory
cd /volume1/docker

# Transfer the image (from your PC or download from GitHub)
# Option A: If image is already on NAS
gunzip backlogia.tar.gz
docker load -i backlogia.tar

# Verify image is loaded
docker images | grep backlogia
```

### Step 2: Prepare Configuration

```bash
# Create directories
mkdir -p /volume1/docker/backlogia/data
mkdir -p /volume1/docker/backlogia/logs

# Copy docker-compose.synology.yml to NAS
# (from your PC via SCP or create the file directly)
cd /volume1/docker/backlogia
```

Create or transfer the `docker-compose.synology.yml` file (see content in repository).

### Step 3: Start Backlogia

```bash
# Start in detached mode
docker compose -f docker-compose.synology.yml up -d

# Check logs
docker compose -f docker-compose.synology.yml logs -f

# Check status
docker ps | grep backlogia
```

### Step 4: Access and Configuration

Access `http://[NAS-IP]:5050` and follow steps 8-9 from Method A.

### Updating via Docker Compose

```bash
# Stop the container
docker compose -f docker-compose.synology.yml down

# Load the new image
gunzip backlogia.tar.gz
docker load -i backlogia.tar

# Restart
docker compose -f docker-compose.synology.yml up -d
```

---

## Troubleshooting

### Container Won't Start

1. Check logs in Container Manager:
   - Container Manager → Container → Select `backlogia` → Details → Log

2. Verify directories exist and are accessible:
   ```bash
   ls -la /volume1/docker/backlogia/data
   ```

3. Check that port 5050 is not already in use:
   ```bash
   netstat -tuln | grep 5050
   ```

### Cannot Access Web Interface

1. **Check DSM Firewall:**
   - Control Panel → Security → Firewall
   - Add a rule to allow port 5050

2. **Verify container is running:**
   - Container Manager → Container → Check status

3. **Test from NAS itself:**
   ```bash
   curl http://localhost:5050
   ```

### API Keys Not Saved

1. Verify the `/data` volume is correctly mounted
2. Check directory permissions:
   ```bash
   ls -la /volume1/docker/backlogia/data
   chmod -R 755 /volume1/docker/backlogia/data
   ```

### SQLite Database Corrupted

1. Backup the old database:
   ```bash
   cp /volume1/docker/backlogia/data/game_library.db /volume1/docker/backlogia/data/game_library.db.backup
   ```

2. Delete and restart container (database will be recreated)

---

## Alternative Deployment Options

### Option 1: Local Registry on NAS

If you update frequently, install a local Docker registry:

```bash
# Install registry:2
docker run -d -p 5000:5000 --name registry --restart=always \
  -v /volume1/docker/registry:/var/lib/registry \
  registry:2

# From your development PC
docker tag backlogia:latest [NAS-IP]:5000/backlogia:latest
docker push [NAS-IP]:5000/backlogia:latest

# On NAS
docker pull [NAS-IP]:5000/backlogia:latest
```

### Option 2: GitHub Container Registry (ghcr.io)

Modify the GitHub Action to push to ghcr.io (requires GitHub token):

```yaml
- name: Login to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Push to GHCR
  run: |
    docker tag backlogia:latest ghcr.io/${{ github.repository }}:latest
    docker push ghcr.io/${{ github.repository }}:latest
```

Then, on NAS:
```bash
docker pull ghcr.io/[YOUR-USERNAME]/backlogia:latest
```

### Option 3: Build Directly on NAS

Clone the Git repository directly on NAS and build:

```bash
cd /volume1/docker
git clone https://github.com/[YOUR-USERNAME]/backlogia.git
cd backlogia
docker compose build
docker compose up -d
```

> **Note:** Building on NAS is slower (10-15 minutes depending on model).

---

## Resources

- **Official Synology Documentation:** https://kb.synology.com/en-global/DSM/help/ContainerManager
- **GitHub Repository:** https://github.com/[YOUR-USERNAME]/backlogia
- **Docker Compose Reference:** https://docs.docker.com/compose/

---

## Support

For questions or issues:
1. Check container logs
2. Review GitHub issues: https://github.com/[YOUR-USERNAME]/backlogia/issues
3. Create a new issue with logs and configuration details
