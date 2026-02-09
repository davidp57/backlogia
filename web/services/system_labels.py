"""System labels management for auto-tagging based on playtime and other metadata."""

SYSTEM_LABELS = {
    "never-launched": {
        "name": "Never Launched",
        "icon": "🎮",
        "color": "#64748b",
        "condition": lambda game: game["playtime_hours"] is None or game["playtime_hours"] == 0
    },
    "just-tried": {
        "name": "Just Tried",
        "icon": "👀",
        "color": "#f59e0b",
        "condition": lambda game: game["playtime_hours"] is not None and 0 < game["playtime_hours"] < 2
    },
    "played": {
        "name": "Played",
        "icon": "🎯",
        "color": "#3b82f6",
        "condition": lambda game: game["playtime_hours"] is not None and 2 <= game["playtime_hours"] < 10
    },
    "well-played": {
        "name": "Well Played",
        "icon": "⭐",
        "color": "#8b5cf6",
        "condition": lambda game: game["playtime_hours"] is not None and 10 <= game["playtime_hours"] < 50
    },
    "heavily-played": {
        "name": "Heavily Played",
        "icon": "🏆",
        "color": "#10b981",
        "condition": lambda game: game["playtime_hours"] is not None and game["playtime_hours"] >= 50
    }
}


def ensure_system_labels(conn):
    """Create or update system labels to match current definitions."""
    cursor = conn.cursor()

    # Map of old French names to new English names for migration
    name_migrations = {
        "Jamais lancé": "Never Launched",
        "Juste essayé": "Just Tried",
        "Joué": "Played",
        "Bien joué": "Well Played",
        "Beaucoup joué": "Heavily Played"
    }

    # First, migrate old French names to English
    for old_name, new_name in name_migrations.items():
        cursor.execute("""
            UPDATE labels
            SET name = ?
            WHERE name = ? AND system = 1 AND type = 'system_tag'
        """, (new_name, old_name))
        if cursor.rowcount > 0:
            print(f"[OK] Migrated system label: {old_name} -> {new_name}")

    # Then create any missing labels
    for label_id, data in SYSTEM_LABELS.items():
        cursor.execute("""
            SELECT id FROM labels WHERE name = ? AND system = 1
        """, (data["name"],))

        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO labels (name, type, icon, color, system)
                VALUES (?, 'system_tag', ?, ?, 1)
            """, (data["name"], data["icon"], data["color"]))
            print(f"[OK] Created system label: {data['name']}")

    conn.commit()


def update_auto_labels_for_game(conn, game_id):
    """Update automatic system labels for a single game based on playtime."""
    cursor = conn.cursor()

    # Get game data
    cursor.execute("SELECT playtime_hours, store FROM games WHERE id = ?", (game_id,))
    game_row = cursor.fetchone()
    if not game_row:
        return

    game = {
        "playtime_hours": game_row["playtime_hours"],
        "store": game_row["store"]
    }

    # Only auto-apply for Steam games with playtime data
    # For other stores, users can manually apply tags
    if game["store"] != "steam" or game["playtime_hours"] is None:
        return

    # Remove all existing auto system labels for this game
    cursor.execute("""
        DELETE FROM game_labels
        WHERE game_id = ? AND auto = 1
        AND label_id IN (
            SELECT id FROM labels WHERE system = 1 AND type = 'system_tag'
        )
    """, (game_id,))

    # Apply matching system labels
    for label_id, data in SYSTEM_LABELS.items():
        if data["condition"](game):
            cursor.execute("""
                SELECT id FROM labels WHERE name = ? AND system = 1
            """, (data["name"],))
            label = cursor.fetchone()

            if label:
                cursor.execute("""
                    INSERT OR IGNORE INTO game_labels (label_id, game_id, auto)
                    VALUES (?, ?, 1)
                """, (label["id"], game_id))

    conn.commit()


def update_all_auto_labels(conn):
    """Update automatic labels for all Steam games."""
    cursor = conn.cursor()

    # Get all Steam games with playtime data
    cursor.execute("""
        SELECT id FROM games
        WHERE store = 'steam' AND playtime_hours IS NOT NULL
    """)
    games = cursor.fetchall()

    print(f"Updating auto labels for {len(games)} Steam games...")

    for game in games:
        update_auto_labels_for_game(conn, game["id"])

    print(f"[OK] Updated auto labels for {len(games)} games")


def get_system_labels_for_game(conn, game_id):
    """Get all system labels for a specific game."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.*, gl.auto
        FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND l.system = 1 AND l.type = 'system_tag'
    """, (game_id,))

    return cursor.fetchall()


def remove_auto_labels_for_game(conn, game_id):
    """Remove all automatic system labels for a game (but keep manual ones)."""
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM game_labels
        WHERE game_id = ? AND auto = 1
        AND label_id IN (
            SELECT id FROM labels WHERE system = 1 AND type = 'system_tag'
        )
    """, (game_id,))

    conn.commit()
