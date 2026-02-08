"""
Gestionnaire de connexion Steam via steamctl/steam library.
Fournit une interface pour interroger les apps Steam via le protocole officiel.
"""
from steam.client import SteamClient
from steam.enums import EResult
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional


class SteamClientManager:
    """
    Singleton pour gérer une connexion Steam persistante.
    Utilise anonymous_login() pour éviter les credentials.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.client = SteamClient()
        self.logged_in = False
        self.last_login_attempt = None
        self.login_failures = 0
        self._initialized = True
        
        # Callbacks
        self.client.on('error', self._on_error)
        self.client.on('logged_on', self._on_logged_on)
        self.client.on('disconnected', self._on_disconnected)
    
    def connect(self, retry_on_failure: bool = True, force: bool = False) -> bool:
        """
        Tente une connexion anonyme à Steam.
        
        Args:
            retry_on_failure: Si False, arrête après 3 échecs
            force: Ignore le rate limiting (pour tests ou reconnexions forcées)
            
        Returns:
            bool: True si connecté avec succès
        """
        if self.logged_in:
            return True
        
        # Rate limit des tentatives de connexion (max 1 tentative / 10 secondes)
        # Plus permissif qu'avant pour permettre des reconnexions rapides
        if not force and self.last_login_attempt:
            elapsed = time.time() - self.last_login_attempt
            cooldown = 10  # seconds
            if elapsed < cooldown:
                # Don't spam logs for quick retries
                return False
        
        self.last_login_attempt = time.time()
        
        try:
            print("🔌 Attempting Steam anonymous login...")
            
            # Anonymous login ne nécessite pas de credentials
            result = self.client.anonymous_login()
            
            if result == EResult.OK:
                self.logged_in = True
                self.login_failures = 0
                print(f"✅ Steam client connected (anonymous)")
                return True
            else:
                self.login_failures += 1
                print(f"⚠️  Steam login failed: {result} (failure #{self.login_failures})")
                
                # Après 3 échecs, ne plus essayer automatiquement
                if self.login_failures >= 3 and not retry_on_failure:
                    print("❌ Too many Steam login failures, disabling auto-retry")
                    return False
                    
        except Exception as e:
            print(f"❌ Steam client error: {e}")
            self.login_failures += 1
        
        return False
    
    def get_product_info(self, app_ids: List[int]) -> Dict[int, Dict]:
        """
        Récupère les Product Info (PICS) pour une liste d'app_ids.
        
        Args:
            app_ids: Liste d'AppIDs Steam
            
        Returns:
            dict: Informations des apps, format:
                  {app_id: {'change_number': int, 'last_change': timestamp, ...}}
        """
        if not self.logged_in:
            if not self.connect():
                return {}
        
        try:
            # Limite à 50 apps par requête pour éviter timeouts
            batch_size = 50
            results = {}
            
            for i in range(0, len(app_ids), batch_size):
                batch = app_ids[i:i+batch_size]
                
                print(f"📦 Fetching product info for {len(batch)} apps (batch {i//batch_size + 1})...")
                
                # Ajouter timeout et gestion gevent
                resp = None
                try:
                    # Import gevent timeout handler
                    from gevent import Timeout  # type: ignore
                    
                    # Timeout de 30 secondes par batch
                    with Timeout(30):
                        resp = self.client.get_product_info(apps=batch)
                except Exception as timeout_err:
                    # Catch both Timeout and other gevent errors
                    if 'Timeout' in str(type(timeout_err).__name__):
                        print(f"⚠️  Timeout fetching batch {i//batch_size + 1}, skipping...")
                    else:
                        print(f"⚠️  Error fetching batch {i//batch_size + 1}: {timeout_err}")
                    continue
                
                if resp is None:
                    continue
                
                for app_id, app_data in resp['apps'].items():
                    if app_data is None:
                        continue
                    
                    results[app_id] = {
                        'change_number': app_data.get('_change_number', 0),
                        'last_change': datetime.now().timestamp(),
                        'depot_info': app_data.get('depots', {}),
                        'common': app_data.get('common', {}),
                    }
                
                # Small delay entre batches
                if i + batch_size < len(app_ids):
                    time.sleep(0.5)
            
            print(f"✅ Fetched info for {len(results)}/{len(app_ids)} apps")
            return results
            
        except Exception as e:
            print(f"❌ Error fetching product info: {e}")
            self.logged_in = False  # Force reconnect on next call
            return {}
    
    def get_change_number(self, app_id: int) -> Optional[int]:
        """
        Récupère uniquement le change_number pour un app_id donné.
        
        Args:
            app_id: AppID Steam
            
        Returns:
            int or None: change_number si trouvé
        """
        info = self.get_product_info([app_id])
        if app_id in info:
            return info[app_id].get('change_number')
        return None
    
    def _on_error(self, result):
        """Callback: erreur Steam"""
        print(f"🔴 Steam client error: {result}")
        self.logged_in = False
    
    def _on_logged_on(self):
        """Callback: connexion réussie"""
        print("🟢 Steam client logged on successfully")
        self.logged_in = True
    
    def _on_disconnected(self):
        """Callback: déconnexion"""
        print("🟡 Steam client disconnected")
        self.logged_in = False
    
    def disconnect(self):
        """Déconnexion propre"""
        if self.client and self.logged_in:
            print("👋 Disconnecting Steam client...")
            self.client.logout()
            self.logged_in = False


# Global instance
_steam_client = None

def get_steam_client() -> SteamClientManager:
    """Factory pour obtenir l'instance singleton"""
    global _steam_client
    if _steam_client is None:
        _steam_client = SteamClientManager()
    return _steam_client
