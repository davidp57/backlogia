# routes/settings.py
# Settings page routes

import sys
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..dependencies import get_db

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    success: str = "",
    conn: sqlite3.Connection = Depends(get_db)
):
    """Settings page for configuring API credentials."""
    # Import here to avoid circular imports
    from ..services.settings import (
        get_setting, STEAM_ID, STEAM_API_KEY, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET,
        ITCH_API_KEY, HUMBLE_SESSION_COOKIE, BATTLENET_SESSION_COOKIE, GOG_DB_PATH,
        EA_BEARER_TOKEN
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
        "ea_bearer_token": get_setting(EA_BEARER_TOKEN, ""),
    }
    success_flag = success == "1"

    # Get hidden count
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM games WHERE hidden = 1")
    hidden_count = cursor.fetchone()[0]

    # Check if running as PyInstaller executable (desktop app)
    is_desktop_app = getattr(sys, 'frozen', False)

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "success": success_flag,
            "hidden_count": hidden_count,
            "is_desktop_app": is_desktop_app
        }
    )


@router.post("/settings", response_class=RedirectResponse)
def save_settings(
    steam_id: str = Form(default=""),
    steam_api_key: str = Form(default=""),
    igdb_client_id: str = Form(default=""),
    igdb_client_secret: str = Form(default=""),
    itch_api_key: str = Form(default=""),
    humble_session_cookie: str = Form(default=""),
    battlenet_session_cookie: str = Form(default=""),
    gog_db_path: str = Form(default=""),
    ea_bearer_token: str = Form(default=""),
):
    """Save settings from the form."""
    # Import here to avoid circular imports
    from ..services.settings import (
        set_setting, STEAM_ID, STEAM_API_KEY, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET,
        ITCH_API_KEY, HUMBLE_SESSION_COOKIE, BATTLENET_SESSION_COOKIE, GOG_DB_PATH,
        EA_BEARER_TOKEN
    )

    # Save all form values
    set_setting(STEAM_ID, steam_id.strip())
    set_setting(STEAM_API_KEY, steam_api_key.strip())
    set_setting(IGDB_CLIENT_ID, igdb_client_id.strip())
    set_setting(IGDB_CLIENT_SECRET, igdb_client_secret.strip())
    set_setting(ITCH_API_KEY, itch_api_key.strip())
    set_setting(HUMBLE_SESSION_COOKIE, humble_session_cookie.strip())
    set_setting(BATTLENET_SESSION_COOKIE, battlenet_session_cookie.strip())
    set_setting(GOG_DB_PATH, gog_db_path.strip())
    set_setting(EA_BEARER_TOKEN, ea_bearer_token.strip())

    return RedirectResponse(url="/settings?success=1", status_code=303)
