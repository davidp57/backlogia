# amazon.py
# Fetches owned games from Amazon Games using OAuth device registration
# Supports both local SQLite database (Windows native) and API access (Docker/cross-platform)

import json
import sqlite3
import requests
import os
import hashlib
import secrets
import base64
from pathlib import Path
from datetime import datetime
from settings import get_amazon_credentials, set_setting, AMAZON_ACCESS_TOKEN

DATABASE_PATH = Path(__file__).parent.parent / "game_library.db"

# Amazon OAuth endpoints (from Playnite reverse engineering)
AMAZON_SIGNIN_URL = "https://www.amazon.com/ap/signin"
AMAZON_REGISTER_URL = "https://api.amazon.com/auth/register"
AMAZON_TOKEN_URL = "https://api.amazon.com/auth/token"
API_ENTITLEMENTS = "https://gaming.amazon.com/api/distribution/entitlements"

# Client credentials (from Amazon Games Launcher)
# Note: LOGIN_CLIENT_ID has "device:" prefix, AUTH_CLIENT_ID does not
LOGIN_CLIENT_ID = "device:3733646238643238366332613932346432653737653161663637373636363435234132554d56484f58375550345637"
AUTH_CLIENT_ID = "3733646238643238366332613932346432653737653161663637373636363435234132554d56484f58375550345637"
DEVICE_TYPE = "A2UMVHOX7UP4V7"

# Request headers for device registration
REGISTER_HEADERS = {
    "User-Agent": "AGSLauncher/1.0.0",
    "Content-Type": "application/json",
}

# Request headers for API calls
API_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "com.amazon.agslauncher.win/3.0.9495.3",
    "Content-Type": "application/json",
}

# Default Windows path for Amazon Games SQLite database
AMAZON_DB_DEFAULT_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Amazon Games" / "Data" / "Games" / "Sql" / "GameInstallInfo.sqlite"


def generate_code_verifier():
    """Generate a random code verifier for PKCE."""
    # Generate 32 random bytes and base64url encode them (gives ~43 chars)
    random_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    return verifier[:43]  # Ensure 43 chars like Playnite


def generate_code_challenge(verifier):
    """Generate SHA256 code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return challenge


def get_login_url():
    """Generate the Amazon login URL for OAuth."""
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.mode": "checkid_setup",
        "openid.oa2.scope": "device_auth_access",
        "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
        "openid.oa2.response_type": "code",
        "openid.oa2.code_challenge_method": "S256",
        "openid.oa2.code_challenge": code_challenge,
        "openid.oa2.client_id": LOGIN_CLIENT_ID,
        "openid.return_to": "https://www.amazon.com/ap/maplanding",
        "openid.assoc_handle": "amzn_sonic_games_launcher",
        "pageId": "amzn_sonic_games_launcher",
        "language": "en_US",
    }

    query_string = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    login_url = f"{AMAZON_SIGNIN_URL}?{query_string}"

    return login_url, code_verifier


def get_device_serial():
    """Generate a unique device serial."""
    import uuid
    # Generate a consistent device ID based on machine
    try:
        # Try to get a consistent machine ID
        machine_id = str(uuid.getnode())  # MAC address based
    except:
        machine_id = str(uuid.uuid4())
    return hashlib.sha256(machine_id.encode()).hexdigest()[:32].upper()


def extract_auth_code_from_url(url):
    """Extract the authorization code from a redirect URL."""
    from urllib.parse import urlparse, parse_qs

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Look for the authorization code in various possible parameter names
        for key in ["openid.oa2.authorization_code", "authorization_code", "code"]:
            if key in params:
                return params[key][0]

        return None
    except Exception:
        return None


def exchange_code_for_tokens(auth_code, code_verifier):
    """Exchange authorization code for access tokens via device registration."""
    try:
        device_serial = get_device_serial()

        # Get OS version
        import platform
        os_version = platform.version() or "10.0.19041.0"

        # Payload structure matching Playnite's implementation
        payload = {
            "auth_data": {
                "use_global_authentication": False,
                "authorization_code": auth_code,
                "code_verifier": code_verifier,
                "code_algorithm": "SHA-256",
                "client_id": AUTH_CLIENT_ID,  # Without "device:" prefix
                "client_domain": "DeviceLegacy",
            },
            "registration_data": {
                "app_name": "AGSLauncher for Windows",
                "app_version": "1.0.0",
                "device_model": "Windows",
                "device_serial": device_serial,
                "device_type": DEVICE_TYPE,
                "domain": "Device",
                "os_version": os_version,
            },
            "requested_extensions": ["customer_info", "device_info"],
            "requested_token_type": ["bearer", "mac_dms"],
        }

        response = requests.post(AMAZON_REGISTER_URL, json=payload, headers=REGISTER_HEADERS)

        if response.status_code != 200:
            print(f"  Token exchange failed: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return None

        data = response.json()

        # Extract tokens from response
        success = data.get("response", {}).get("success", {})
        tokens = success.get("tokens", {}).get("bearer", {})

        if not tokens:
            print("  No tokens in response")
            return None

        return {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in"),
        }

    except Exception as e:
        print(f"  Error exchanging code: {e}")
        return None


def refresh_tokens(refresh_token):
    """Refresh access token using refresh token."""
    try:
        payload = {
            "source_token": refresh_token,
            "source_token_type": "refresh_token",
            "requested_token_type": "access_token",
            "app_name": "AGSLauncher for Windows",
            "app_version": "1.0.0",
        }

        response = requests.post(AMAZON_TOKEN_URL, json=payload, headers=REGISTER_HEADERS)

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("access_token")

    except Exception as e:
        print(f"  Error refreshing token: {e}")
        return None


def get_local_database_path():
    """Get the path to the local Amazon Games SQLite database."""
    creds = get_amazon_credentials()
    custom_path = creds.get("db_path")

    if custom_path:
        return Path(custom_path)

    if AMAZON_DB_DEFAULT_PATH.exists():
        return AMAZON_DB_DEFAULT_PATH

    return None


def get_games_from_local_db():
    """Fetch installed games from the local Amazon Games SQLite database."""
    db_path = get_local_database_path()

    if not db_path or not db_path.exists():
        print("  Amazon Games local database not found")
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM DbSet")
        rows = cursor.fetchall()

        games = []
        for row in rows:
            game_data = dict(row)
            game = {
                "product_id": game_data.get("Id") or game_data.get("ProductId"),
                "name": game_data.get("ProductTitle") or game_data.get("Title"),
                "installed": game_data.get("Installed", 0) == 1,
                "install_directory": game_data.get("InstallDirectory"),
                "install_date": game_data.get("InstallDate"),
                "is_streaming": False,  # Local DB = installable games
                "raw_data": game_data,
            }

            if game["name"]:
                games.append(game)

        conn.close()
        return games

    except Exception as e:
        print(f"  Error reading Amazon Games database: {e}")
        return None


def get_entitlements_from_api(access_token):
    """Fetch game entitlements from Amazon Gaming API."""
    try:
        import uuid
        games = []
        next_token = None

        # Headers matching Playnite exactly
        headers = {
            "User-Agent": "com.amazon.agslauncher.win/3.0.9495.3",
            "Content-Type": "application/json",
            "X-Amz-Target": "com.amazon.animusdistributionservice.entitlement.AnimusEntitlementsService.GetEntitlements",
            "x-amzn-token": access_token,
            "Expect": "100-continue",
            "Content-Encoding": "amz-1.0",
        }

        while True:
            # Generate a random hardware hash (GUID without hyphens)
            hardware_hash = uuid.uuid4().hex

            # Payload matching Playnite's EntitlementsRequest class
            payload = {
                "Operation": "GetEntitlements",
                "clientId": "Sonic",
                "syncPoint": 0,
                "maxResults": 500,
                "keyId": "d5dc8b8b-86c8-4fc4-ae93-18c0def5314d",
                "hardwareHash": hardware_hash,
                "productIdFilter": None,
                "disableStateFilter": True,
            }

            if next_token:
                payload["nextToken"] = next_token

            response = requests.post(API_ENTITLEMENTS, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"  Entitlements API failed: {response.status_code}")
                try:
                    print(f"  Response: {response.text[:200]}")
                except:
                    pass
                break

            data = response.json()
            entitlements = data.get("entitlements", [])

            for ent in entitlements:
                product = ent.get("product", {})
                product_line = product.get("productLine", "")

                # Skip Twitch fuel entitlements
                if product_line == "Twitch:FuelEntitlement":
                    continue

                # Determine if this is a streaming game (Luna)
                is_streaming = "Luna" in product_line or ent.get("channelId") == "Luna"

                game = {
                    "product_id": product.get("id") or product.get("asin"),
                    "name": product.get("title"),
                    "publisher": product.get("publisher"),
                    "developer": product.get("developer"),
                    "product_line": product_line,
                    "icon_url": product.get("iconUrl"),
                    "is_streaming": is_streaming,
                    "raw_data": ent,
                }

                if game["name"]:
                    games.append(game)

            next_token = data.get("nextToken")
            if not next_token:
                break

        return games

    except Exception as e:
        print(f"  Error fetching entitlements: {e}")
        return []


def get_stored_tokens():
    """Get stored OAuth tokens."""
    creds = get_amazon_credentials()
    token_data = creds.get("access_token")

    if not token_data:
        return None, None

    # Check if it's JSON (new format with both tokens) or just access token
    try:
        data = json.loads(token_data)
        return data.get("access_token"), data.get("refresh_token")
    except (json.JSONDecodeError, TypeError):
        # Old format - just access token
        return token_data, None


def save_tokens(access_token, refresh_token=None):
    """Save OAuth tokens."""
    if refresh_token:
        token_data = json.dumps({
            "access_token": access_token,
            "refresh_token": refresh_token,
        })
    else:
        token_data = access_token

    set_setting(AMAZON_ACCESS_TOKEN, token_data)


def get_amazon_library():
    """Fetch all games from Amazon Games library."""
    all_games = []
    seen_ids = set()

    # Method 1: Try local database first (Windows native)
    print("  Checking for local Amazon Games database...")
    local_games = get_games_from_local_db()
    if local_games:
        print(f"  Found {len(local_games)} games in local database")
        for game in local_games:
            product_id = game.get("product_id")
            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)
                all_games.append(game)

    # Method 2: Try API with OAuth tokens
    print("  Checking for OAuth tokens...")
    access_token, refresh_token = get_stored_tokens()

    if access_token:
        print("  Fetching entitlements from Amazon Gaming API...")
        api_games = get_entitlements_from_api(access_token)

        # If access token expired, try refresh
        if not api_games and refresh_token:
            print("  Access token may be expired, trying refresh...")
            new_access_token = refresh_tokens(refresh_token)
            if new_access_token:
                save_tokens(new_access_token, refresh_token)
                api_games = get_entitlements_from_api(new_access_token)

        if api_games:
            print(f"  Found {len(api_games)} games via API")
            streaming_count = sum(1 for g in api_games if g.get("is_streaming"))
            installable_count = len(api_games) - streaming_count
            print(f"    ({installable_count} installable, {streaming_count} streaming)")

            for game in api_games:
                product_id = game.get("product_id")
                if product_id and product_id not in seen_ids:
                    seen_ids.add(product_id)
                    all_games.append(game)
    elif not local_games:
        print("Error: Amazon Games not configured")
        print("\nTo set up Amazon Games, use the 'Authenticate' button in Settings")
        print("This will open a browser for you to log in to Amazon")
        return None

    if not all_games:
        print("  No Amazon games found")
        return None

    return all_games


def authenticate_amazon(auth_code, code_verifier):
    """Complete Amazon authentication with authorization code."""
    print("Exchanging authorization code for tokens...")
    tokens = exchange_code_for_tokens(auth_code, code_verifier)

    if not tokens:
        return False, "Failed to exchange authorization code"

    # Save tokens
    save_tokens(tokens["access_token"], tokens.get("refresh_token"))

    # Verify by fetching entitlements
    games = get_entitlements_from_api(tokens["access_token"])
    if games:
        return True, f"Successfully authenticated! Found {len(games)} games."
    else:
        return True, "Authenticated, but couldn't fetch games. Token saved anyway."


def import_to_database(games):
    """Import Amazon games to the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    count = 0
    for game in games:
        try:
            developers = [game.get("developer")] if game.get("developer") else None
            publishers = [game.get("publisher")] if game.get("publisher") else None

            # Store streaming flag in extra_data
            extra_data = game.get("raw_data", {})
            extra_data["is_streaming"] = game.get("is_streaming", False)

            cursor.execute(
                """INSERT OR REPLACE INTO games (
                    name, store, store_id, cover_image, icon,
                    developers, publishers, extra_data, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    game.get("name"),
                    "amazon",
                    game.get("product_id"),
                    game.get("icon_url"),
                    game.get("icon_url"),
                    json.dumps(developers) if developers else None,
                    json.dumps(publishers) if publishers else None,
                    json.dumps(extra_data),
                    datetime.now().isoformat(),
                ),
            )
            count += 1
        except Exception as e:
            print(f"  Error importing {game.get('name')}: {e}")

    conn.commit()
    conn.close()
    return count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import Amazon Games library")
    parser.add_argument("--export", type=str, help="Export to JSON file instead of database")
    parser.add_argument("--auth", action="store_true", help="Start authentication flow")
    args = parser.parse_args()

    if args.auth:
        print("Amazon Games Authentication")
        print("=" * 60)
        login_url, code_verifier = get_login_url()
        print("\n1. Open this URL in your browser:\n")
        print(login_url)
        print("\n2. Log in to Amazon")
        print("3. After login, you'll be redirected to a page with a URL like:")
        print("   https://www.amazon.com/ap/maplanding?openid.oa2.authorization_code=...")
        print("\n4. Copy the 'authorization_code' value from the URL and paste it here:")

        auth_code = input("\nAuthorization code: ").strip()
        if auth_code:
            success, message = authenticate_amazon(auth_code, code_verifier)
            print(f"\n{message}")
        return

    print("Amazon Games Library Import")
    print("=" * 60)

    games = get_amazon_library()
    if not games:
        print("Failed to fetch Amazon Games library")
        return

    print(f"\nFound {len(games)} unique games")

    if args.export:
        with open(args.export, "w") as f:
            json.dump(games, f, indent=2, default=str)
        print(f"Exported to {args.export}")
    else:
        count = import_to_database(games)
        print(f"Imported {count} games to database")


if __name__ == "__main__":
    main()
