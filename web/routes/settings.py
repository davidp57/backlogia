# routes/settings.py
# Settings page routes

from flask import Blueprint, render_template, request, redirect, url_for

from ..database import get_db

settings_bp = Blueprint('settings', __name__)


@settings_bp.route("/settings")
def settings_page():
    """Settings page for configuring API credentials."""
    # Import here to avoid circular imports
    from ..services.settings import (
        get_setting, STEAM_ID, STEAM_API_KEY, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET,
        ITCH_API_KEY, HUMBLE_SESSION_COOKIE, BATTLENET_SESSION_COOKIE, GOG_DB_PATH
    )

    settings = {
        "steam_id": get_setting(STEAM_ID, ""),
        "steam_api_key": get_setting(STEAM_API_KEY, ""),
        "igdb_client_id": get_setting(IGDB_CLIENT_ID, ""),
        "igdb_client_secret": get_setting(IGDB_CLIENT_SECRET, ""),
        "itch_api_key": get_setting(ITCH_API_KEY, ""),
        "humble_session_cookie": get_setting(HUMBLE_SESSION_COOKIE, ""),
        "battlenet_session_cookie": get_setting(BATTLENET_SESSION_COOKIE, ""),
        "gog_db_path": get_setting(GOG_DB_PATH, ""),
    }
    success = request.args.get("success") == "1"

    # Get hidden count
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM games WHERE hidden = 1")
    hidden_count = cursor.fetchone()[0]
    conn.close()

    return render_template("settings.html", settings=settings, success=success, hidden_count=hidden_count)


@settings_bp.route("/settings", methods=["POST"])
def save_settings():
    """Save settings from the form."""
    # Import here to avoid circular imports
    from ..services.settings import (
        set_setting, STEAM_ID, STEAM_API_KEY, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET,
        ITCH_API_KEY, HUMBLE_SESSION_COOKIE, BATTLENET_SESSION_COOKIE, GOG_DB_PATH
    )

    # Get form values and save them
    set_setting(STEAM_ID, request.form.get("steam_id", "").strip())
    set_setting(STEAM_API_KEY, request.form.get("steam_api_key", "").strip())
    set_setting(IGDB_CLIENT_ID, request.form.get("igdb_client_id", "").strip())
    set_setting(IGDB_CLIENT_SECRET, request.form.get("igdb_client_secret", "").strip())
    set_setting(ITCH_API_KEY, request.form.get("itch_api_key", "").strip())
    set_setting(HUMBLE_SESSION_COOKIE, request.form.get("humble_session_cookie", "").strip())
    set_setting(BATTLENET_SESSION_COOKIE, request.form.get("battlenet_session_cookie", "").strip())
    set_setting(GOG_DB_PATH, request.form.get("gog_db_path", "").strip())

    return redirect(url_for("settings.settings_page", success=1))
