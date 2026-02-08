# routes/steam_client.py
# Steam Client management endpoints

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.settings import get_setting, set_setting, USE_STEAM_CLIENT, STEAM_USERNAME, STEAM_PASSWORD

router = APIRouter()


class SteamClientStatus(BaseModel):
    """Steam Client status response"""
    enabled: bool
    connected: bool
    connection_method: str  # 'anonymous', 'credentials', 'disconnected'
    login_failures: int
    last_login_attempt: Optional[float]


class SteamClientSettings(BaseModel):
    """Steam Client settings"""
    enabled: bool
    username: Optional[str] = None
    password: Optional[str] = None


@router.get("/api/steam-client/status")
def get_steam_client_status() -> SteamClientStatus:
    """Get current Steam Client connection status."""
    enabled = get_setting(USE_STEAM_CLIENT, "false").lower() == "true"
    
    if not enabled:
        return SteamClientStatus(
            enabled=False,
            connected=False,
            connection_method="disconnected",
            login_failures=0,
            last_login_attempt=None
        )
    
    # Try to get Steam Worker instance
    try:
        from ..services.steam_worker import get_steam_worker
        worker = get_steam_worker()
        
        if not worker.is_alive():
            return SteamClientStatus(
                enabled=True,
                connected=False,
                connection_method="error",
                login_failures=99,
                last_login_attempt=None
            )
        
        status = worker.get_status()
        
        return SteamClientStatus(
            enabled=True,
            connected=status.get('logged_in', False),
            connection_method="anonymous" if status.get('logged_in') else "disconnected",
            login_failures=status.get('login_failures', 0),
            last_login_attempt=None
        )
    except Exception as e:
        return SteamClientStatus(
            enabled=True,
            connected=False,
            connection_method="error",
            login_failures=0,
            last_login_attempt=None
        )


@router.post("/api/steam-client/settings")
def update_steam_client_settings(settings: SteamClientSettings):
    """Update Steam Client settings."""
    # Save enabled state
    set_setting(USE_STEAM_CLIENT, "true" if settings.enabled else "false")
    
    # Save credentials if provided
    if settings.username:
        set_setting(STEAM_USERNAME, settings.username)
    if settings.password:
        set_setting(STEAM_PASSWORD, settings.password)
    
    # If disabling, disconnect current client
    if not settings.enabled:
        try:
            from ..services.steam_client_manager import get_steam_client
            client = get_steam_client()
            client.disconnect()
        except Exception:
            pass
    
    return {"success": True, "message": "Steam Client settings updated"}


@router.post("/api/steam-client/connect")
def connect_steam_client():
    """Manually trigger Steam Client connection."""
    enabled = get_setting(USE_STEAM_CLIENT, "false") or "false"
    
    if enabled.lower() != "true":
        raise HTTPException(status_code=400, detail="Steam Client is disabled")
    
    try:
        from ..services.steam_worker import get_steam_worker
        worker = get_steam_worker()
        
        # Try to connect
        success = worker.connect()
        
        if success:
            return {"success": True, "message": "Connected to Steam"}
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to Steam")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting: {str(e)}")


@router.post("/api/steam-client/disconnect")
def disconnect_steam_client():
    """Manually disconnect Steam Client."""
    try:
        from ..services.steam_worker import get_steam_worker
        worker = get_steam_worker()
        worker.disconnect()
        return {"success": True, "message": "Disconnected from Steam"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")
