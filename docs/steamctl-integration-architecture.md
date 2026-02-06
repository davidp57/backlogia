# Architecture: Intégration SteamCTL pour Update Tracking

## Status
**PROPOSITION** - Non implémenté  
Date de création: 2026-02-06  
Branche actuelle: `updates-and-news` (API HTTP fonctionnel)

## Contexte

Actuellement, le système de tracking des mises à jour utilise des API HTTP publiques pour chaque store:
- **Steam**: `/appdetails/` API (rate limit: 1.5s entre requêtes)
- **Epic**: StorefrontAPI avec `lastModifiedDate`
- **GOG**: Product API

Cette approche fonctionne mais nécessite du rate limiting strict pour Steam. L'intégration de `steamctl` (bibliothèque Python Steam) permettrait d'utiliser le protocole Steam officiel pour des requêtes plus rapides et des données plus riches.

## Objectifs

### Objectifs Principaux
1. **Performance améliorée**: Réduire le temps de sync pour les jeux Steam
2. **Données plus riches**: Accès aux `change_number` officiels et métadonnées complètes
3. **Fiabilité**: Utiliser le protocole Steam officiel au lieu d'APIs publiques non documentées

### Non-Objectifs
- Ne remplace PAS les autres stores (Epic, GOG, etc.)
- Ne nécessite PAS de credentials utilisateur (login anonyme)
- N'ajoute PAS de complexité UI (transparent pour l'utilisateur)

## Architecture Proposée

### 1. Nouvelle Couche: Steam Client Manager

```
web/services/
├── steam_client_manager.py   # NOUVEAU - Gestion du client Steam
├── update_tracker.py          # MODIFIÉ - Utilise steam_client si disponible
├── jobs.py                    # Inchangé
└── ...
```

#### Fichier: `web/services/steam_client_manager.py`

```python
"""
Gestionnaire de connexion Steam via steamctl/steam library.
Fournit une interface pour interroger les apps Steam via le protocole officiel.
"""
from steam.client import SteamClient
from steam.enums import EResult
import threading
import time
from datetime import datetime

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
    
    def connect(self, retry_on_failure=True):
        """
        Tente une connexion anonyme à Steam.
        
        Returns:
            bool: True si connecté avec succès
        """
        if self.logged_in:
            return True
        
        # Rate limit des tentatives de connexion (max 1 tentative / minute)
        if self.last_login_attempt:
            elapsed = time.time() - self.last_login_attempt
            if elapsed < 60:
                return False
        
        self.last_login_attempt = time.time()
        
        try:
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
    
    def get_product_info(self, app_ids):
        """
        Récupère les Product Info (PICS) pour une liste d'app_ids.
        
        Args:
            app_ids (list[int]): Liste d'AppIDs Steam
            
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
                
                resp = self.client.get_product_info(apps=batch)
                
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
            
            return results
            
        except Exception as e:
            print(f"Error fetching product info: {e}")
            self.logged_in = False  # Force reconnect on next call
            return {}
    
    def _on_error(self, result):
        print(f"Steam client error: {result}")
        self.logged_in = False
    
    def _on_logged_on(self):
        print("Steam client logged on successfully")
        self.logged_in = True
    
    def _on_disconnected(self):
        print("Steam client disconnected")
        self.logged_in = False
    
    def disconnect(self):
        """Déconnexion propre"""
        if self.client and self.logged_in:
            self.client.logout()
            self.logged_in = False


# Global instance
_steam_client = None

def get_steam_client():
    """Factory pour obtenir l'instance singleton"""
    global _steam_client
    if _steam_client is None:
        _steam_client = SteamClientManager()
    return _steam_client
```

### 2. Modification: Update Tracker

#### Fichier: `web/services/update_tracker.py` (modifications)

```python
# Ajout en haut du fichier
from .steam_client_manager import get_steam_client

class UpdateTracker:
    """Détection des mises à jour de jeux"""
    
    def __init__(self):
        self.trackers = {
            'steam': SteamUpdateTracker(),
            'epic': EpicUpdateTracker(),
            'gog': GOGUpdateTracker(),
            # ... autres stores
        }
        
        # Tentative de connexion Steam au démarrage (non bloquant)
        self._initialize_steam_client()
    
    def _initialize_steam_client(self):
        """Initialise le client Steam en arrière-plan"""
        try:
            client = get_steam_client()
            # Tentative en arrière-plan, on ne bloque pas si ça échoue
            threading.Thread(target=client.connect, daemon=True).start()
        except Exception as e:
            print(f"Steam client initialization failed: {e}")


class SteamUpdateTracker(StoreUpdateTracker):
    """Tracker spécifique à Steam - MODIFIÉ"""
    
    def __init__(self):
        super().__init__()
        self.steam_client = None  # Lazy init
    
    def _get_steam_client(self):
        """Lazy initialization du Steam client"""
        if self.steam_client is None:
            self.steam_client = get_steam_client()
        return self.steam_client
    
    def check_updates_bulk(self, games):
        """
        NOUVEAU: Check updates pour plusieurs jeux en une fois.
        Utilise le Steam client si disponible, sinon fallback sur API HTTP.
        
        Args:
            games (list[Game]): Liste de jeux Steam
            
        Returns:
            dict: {game_id: update_info or None}
        """
        client = self._get_steam_client()
        
        # Tentative via Steam client
        if client.logged_in or client.connect():
            return self._check_via_steam_client(client, games)
        
        # Fallback sur API HTTP classique
        print("⚠️  Steam client unavailable, using HTTP API fallback")
        return self._check_via_http_api(games)
    
    def _check_via_steam_client(self, client, games):
        """Check updates via le protocole Steam"""
        app_ids = [int(game.store_id) for game in games]
        product_infos = client.get_product_info(app_ids)
        
        results = {}
        
        for game in games:
            app_id = int(game.store_id)
            info = product_infos.get(app_id)
            
            if not info:
                results[game.id] = None
                continue
            
            # Comparer change_number avec la dernière version connue
            last_change = self._get_last_change_number(game.id)
            current_change = info['change_number']
            
            if current_change > last_change:
                # Nouvelle mise à jour détectée !
                results[game.id] = {
                    'change_number': current_change,
                    'timestamp': int(info['last_change']),
                    'source': 'steam_client',
                }
            else:
                results[game.id] = None
        
        return results
    
    def _check_via_http_api(self, games):
        """Fallback: méthode HTTP actuelle"""
        results = {}
        
        for game in games:
            # Code actuel (fetch_metadata + check_updates_for_game)
            update_info = self.check_updates_for_game(game)
            results[game.id] = update_info
            
            # Rate limiting
            time.sleep(1.5)
        
        return results
    
    def _get_last_change_number(self, game_id):
        """Récupère le dernier change_number connu pour un jeu"""
        # Query depuis game_depot_updates ou nouvelle colonne
        # À implémenter selon structure DB choisie
        pass


# Modification de sync_updates_job pour utiliser bulk check
def sync_updates_job(job_id=None):
    """Job de synchronisation des updates - MODIFIÉ"""
    from .jobs import update_job_progress
    from ..database import get_connection
    
    conn = get_connection()
    games = conn.execute('''
        SELECT id, store, store_id, title
        FROM games
        WHERE store IN ('steam', 'epic', 'gog')
        ORDER BY store, store_id
    ''').fetchall()
    
    tracker = UpdateTracker()
    total = len(games)
    processed = 0
    
    # Group games by store pour bulk processing
    games_by_store = {}
    for game in games:
        store = game['store']
        if store not in games_by_store:
            games_by_store[store] = []
        games_by_store[store].append(game)
    
    # Process by store
    for store, store_games in games_by_store.items():
        if store == 'steam':
            # Bulk check pour Steam (rapide avec steam client)
            store_tracker = tracker.trackers[store]
            results = store_tracker.check_updates_bulk(store_games)
            
            for game in store_games:
                update_info = results.get(game['id'])
                if update_info:
                    # Save update to DB
                    pass
                
                processed += 1
                if job_id:
                    update_job_progress(job_id, processed, total)
        else:
            # Individual check pour autres stores
            # (code actuel)
            pass
```

### 3. Schéma de Base de Données

#### Nouvelle table: `steam_change_numbers` (optionnel)

```sql
-- Suivi des change_numbers Steam pour détecter les updates
CREATE TABLE IF NOT EXISTS steam_change_numbers (
    game_id INTEGER NOT NULL,
    change_number INTEGER NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE INDEX idx_steam_change_numbers_game ON steam_change_numbers(game_id);
```

Ou bien ajouter une colonne à `game_depot_updates`:

```sql
ALTER TABLE game_depot_updates 
ADD COLUMN change_number INTEGER;
```

### 4. Flux de Données

```
User clicks "Track Updates"
         |
         v
POST /api/sync/updates
         |
         v
sync_updates_job() launched
         |
         v
Group games by store
         |
         +------------------+------------------+
         |                  |                  |
         v                  v                  v
    [STEAM]            [EPIC]             [GOG]
         |                  |                  |
         v                  v                  v
 SteamClientManager   EpicTracker      GOGTracker
 (bulk: 50 at once)   (individual)     (individual)
         |                  |                  |
         v                  v                  v
    Steam Protocol      HTTP API         HTTP API
    (fast, rich)        (existing)       (existing)
         |                  |                  |
         +------------------+------------------+
                           |
                           v
                  Save to game_depot_updates
                           |
                           v
                    Update job progress
```

### 5. Stratégie de Fallback

```python
# Ordre de priorité pour Steam:
1. Steam Client (si connecté et disponible)
   └─> Si échec: marquer comme indisponible pour 5 minutes
2. HTTP API (fallback automatique)
   └─> Rate limit: 1.5s entre requêtes

# Critères pour désactiver Steam Client:
- 3 échecs de connexion consécutifs
- Timeout > 30 secondes sur get_product_info
- Exception non gérée

# Réactivation automatique:
- Toutes les 15 minutes, retry connection
- Si succès, restaurer comme méthode primaire
```

## Migration Plan

### Phase 1: Préparation (sans casser l'existant)
- [ ] Créer `steam_client_manager.py` avec tests unitaires
- [ ] Tests dans environnement isolé (pas de DB)
- [ ] Vérifier que anonymous_login fonctionne
- [ ] Benchmarker: temps de connexion, durée des requêtes

### Phase 2: Intégration douce
- [ ] Ajouter flag `USE_STEAM_CLIENT` dans config
- [ ] Modifier `update_tracker.py` avec condition:
  ```python
  if config.USE_STEAM_CLIENT:
      result = self._check_via_steam_client(...)
  else:
      result = self._check_via_http_api(...)
  ```
- [ ] Tests en production avec flag=False (aucun changement)
- [ ] Activer flag=True pour un petit subset de jeux (10-20)

### Phase 3: Déploiement progressif
- [ ] Activer pour 100 jeux Steam
- [ ] Monitorer: temps de sync, taux d'erreur, qualité des données
- [ ] Si OK: activer pour tous les jeux Steam
- [ ] Si KO: fallback sur HTTP API, investiguer

### Phase 4: Optimisation
- [ ] Implémenter bulk check (50 apps à la fois)
- [ ] Cache des change_numbers en mémoire (Redis?)
- [ ] Retry logic sophistiqué
- [ ] Métriques et monitoring (Prometheus?)

## Risques et Mitigations

### Risque 1: Connexion Steam échoue
**Impact**: Moyen  
**Probabilité**: Moyenne  
**Mitigation**: 
- Fallback automatique sur HTTP API
- Retry avec exponential backoff
- Alert si échecs > 3

### Risque 2: Rate limiting Steam
**Impact**: Élevé  
**Probabilité**: Faible  
**Mitigation**:
- Anonymous login normalement pas rate-limité
- Batch requests (50 apps max)
- Monitoring du taux d'erreur

### Risque 3: Complexité accrue
**Impact**: Moyen  
**Probabilité**: Élevée  
**Mitigation**:
- Phase de test approfondie
- Documentation complète
- Feature flag pour désactivation rapide

### Risque 4: Dépendance supplémentaire
**Impact**: Faible  
**Probabilité**: Moyenne  
**Mitigation**:
- `steamctl` bien maintenu par ValvePython
- Fallback sur HTTP API si installation échoue
- Tests CI avec et sans steamctl

## Métriques de Succès

### Performance
- Temps de sync Steam: **< 30 secondes** pour 2000 jeux (vs ~50 min actuellement)
- Bulk request: **50 apps en < 5 secondes**

### Fiabilité
- Taux de succès: **> 98%**
- Fallback automatique: **< 2 secondes** pour détecter échec

### Qualité des Données
- Change numbers précis: **100%** (vs estimation actuelle)
- False positives: **< 1%**

## Questions Ouvertes

1. **Anonymous login suffisant?**
   - À tester: est-ce que anonymous_login donne accès à get_product_info()?
   - Alternative: demander credentials optionnels dans settings

2. **Persistence de la connexion?**
   - Garder le client connecté en permanence?
   - Ou reconnect à chaque sync job?

3. **Gestion du threading?**
   - SteamClient est-il thread-safe?
   - Besoin d'un lock pour les requêtes concurrentes?

4. **Stockage des change_numbers?**
   - Table séparée ou colonne dans game_depot_updates?
   - Impact sur les requêtes de la page library?

## Références

- [ValvePython/steam](https://github.com/ValvePython/steam) - Library principale
- [ValvePython/steamctl](https://github.com/ValvePython/steamctl) - CLI tool (exemples)
- [Steam Protocol](https://github.com/SteamRE/SteamKit) - Documentation du protocole
- [SteamDatabase/SteamAppInfo](https://github.com/SteamDatabase/SteamAppInfo) - Format appinfo.vdf

## Alternatives Considérées

### Alternative 1: Parser appinfo.vdf local
**Status**: ❌ Rejeté  
**Raison**: Format V41 trop complexe, string table difficile à parser, données peuvent être obsolètes

### Alternative 2: Scraping SteamDB
**Status**: ❌ Rejeté  
**Raison**: Non éthique, rate limiting strict, risque de ban, données pas officielles

### Alternative 3: Garder HTTP API uniquement
**Status**: ✅ Actuel  
**Raison**: Fonctionne, simple, mais lent pour Steam (rate limit 1.5s)

## Décision

**Statut**: EN ATTENTE  
**Prochaine étape**: POC avec Steam Client anonymous login  
**Décideur**: @sam1am  
**Date limite**: Aucune (exploration)

---

**Document mis à jour**: 2026-02-06  
**Auteur**: GitHub Copilot  
**Reviewers**: @sam1am
