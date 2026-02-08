"""
Test du Steam Client avec la vraie base de données Backlogia.
Compare les performances et données entre Steam Client et HTTP API.
"""
import os
import sys
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# Add web to path
sys.path.insert(0, str(Path(__file__).parent))

from web.config import DATABASE_PATH


def get_steam_games_sample(limit=20):
    """Récupère un échantillon de jeux Steam depuis la DB"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, store_id, last_modified, development_status
        FROM games
        WHERE store = 'steam' AND store_id IS NOT NULL
        LIMIT ?
    """, (limit,))
    
    games = cursor.fetchall()
    conn.close()
    
    return games


def test_with_http_api(games):
    """Test avec l'API HTTP (méthode actuelle)"""
    print("\n" + "="*60)
    print("TEST 1: HTTP API (Méthode Actuelle)")
    print("="*60)
    
    # Disable Steam Client
    os.environ['USE_STEAM_CLIENT'] = 'false'
    
    # Force reload
    for mod in ['web.config', 'web.services.update_tracker']:
        if mod in sys.modules:
            del sys.modules[mod]
    
    from web.services.update_tracker import SteamUpdateTracker
    
    tracker = SteamUpdateTracker()
    
    print(f"\nFetching metadata for {len(games)} games via HTTP API...")
    print(f"Using: {tracker.__class__.__name__} (use_steam_client={tracker.use_steam_client})")
    
    results = []
    start = time.time()
    
    for game_id, name, store_id, db_last_mod, db_status in games:
        print(f"\n📦 {name} (AppID {store_id})")
        
        metadata = tracker.fetch_metadata(store_id)
        
        if metadata:
            print(f"   ✅ Metadata received")
            print(f"   - last_modified: {metadata.get('last_modified')}")
            print(f"   - development_status: {metadata.get('development_status')}")
            print(f"   - source: {metadata.get('source', 'http_api')}")
            
            results.append({
                'game_id': game_id,
                'name': name,
                'store_id': store_id,
                'success': True,
                'metadata': metadata
            })
        else:
            print(f"   ❌ Failed to fetch metadata")
            results.append({
                'game_id': game_id,
                'name': name,
                'store_id': store_id,
                'success': False,
                'metadata': None
            })
        
        # Rate limiting for HTTP API
        time.sleep(1.6)
    
    elapsed = time.time() - start
    
    success_count = sum(1 for r in results if r['success'])
    
    print(f"\n" + "="*60)
    print(f"⏱️  Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"📊 Success rate: {success_count}/{len(games)} ({success_count/len(games)*100:.0f}%)")
    print(f"⚡ Average: {elapsed/len(games):.1f}s per game")
    
    return results, elapsed


def test_with_steam_client(games):
    """Test avec le Steam Client (nouvelle méthode)"""
    print("\n" + "="*60)
    print("TEST 2: Steam Client (Nouvelle Méthode)")
    print("="*60)
    
    # Enable Steam Client
    os.environ['USE_STEAM_CLIENT'] = 'true'
    
    # Force reload
    for mod in ['web.config', 'web.services.update_tracker', 'web.services.steam_client_manager']:
        if mod in sys.modules:
            del sys.modules[mod]
    
    from web.services.update_tracker import SteamUpdateTracker
    
    tracker = SteamUpdateTracker()
    
    print(f"\nFetching metadata for {len(games)} games via Steam Client...")
    print(f"Using: {tracker.__class__.__name__} (use_steam_client={tracker.use_steam_client})")
    
    # Wait for connection
    print("\nWaiting for Steam Client connection...")
    time.sleep(2)
    
    results = []
    start = time.time()
    
    for game_id, name, store_id, db_last_mod, db_status in games:
        print(f"\n📦 {name} (AppID {store_id})")
        
        metadata = tracker.fetch_metadata(store_id)
        
        if metadata:
            print(f"   ✅ Metadata received")
            print(f"   - last_modified: {metadata.get('last_modified')}")
            print(f"   - development_status: {metadata.get('development_status')}")
            print(f"   - change_number: {metadata.get('change_number')}")
            print(f"   - source: {metadata.get('source', 'unknown')}")
            
            results.append({
                'game_id': game_id,
                'name': name,
                'store_id': store_id,
                'success': True,
                'metadata': metadata
            })
        else:
            print(f"   ❌ Failed to fetch metadata")
            results.append({
                'game_id': game_id,
                'name': name,
                'store_id': store_id,
                'success': False,
                'metadata': None
            })
        
        # Much shorter delay with Steam Client
        time.sleep(0.2)
    
    elapsed = time.time() - start
    
    success_count = sum(1 for r in results if r['success'])
    steam_client_count = sum(1 for r in results if r['success'] and r['metadata'].get('source') == 'steam_client')
    
    print(f"\n" + "="*60)
    print(f"⏱️  Total time: {elapsed:.1f}s")
    print(f"📊 Success rate: {success_count}/{len(games)} ({success_count/len(games)*100:.0f}%)")
    print(f"⚡ Average: {elapsed/len(games):.2f}s per game")
    print(f"🚀 Steam Client usage: {steam_client_count}/{success_count} requests")
    
    return results, elapsed


def compare_results(http_results, http_time, client_results, client_time):
    """Compare les résultats des deux méthodes"""
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    
    print(f"\n📊 Performance:")
    speedup = http_time / client_time if client_time > 0 else 0
    time_saved = http_time - client_time
    print(f"   - HTTP API: {http_time:.1f}s ({http_time/60:.1f} minutes)")
    print(f"   - Steam Client: {client_time:.1f}s")
    print(f"   - Speedup: {speedup:.1f}x faster")
    print(f"   - Time saved: {time_saved:.1f}s ({time_saved/60:.1f} minutes)")
    
    # Check for differences in data
    print(f"\n📋 Data Comparison:")
    
    http_success = {r['store_id']: r for r in http_results if r['success']}
    client_success = {r['store_id']: r for r in client_results if r['success']}
    
    # Games fetched by both
    both_ids = set(http_success.keys()) & set(client_success.keys())
    print(f"   - Both methods succeeded: {len(both_ids)} games")
    
    # Games only in HTTP
    http_only = set(http_success.keys()) - set(client_success.keys())
    if http_only:
        print(f"   - Only HTTP succeeded: {len(http_only)} games")
    
    # Games only in Steam Client
    client_only = set(client_success.keys()) - set(http_success.keys())
    if client_only:
        print(f"   - Only Steam Client succeeded: {len(client_only)} games")
    
    # Check change_numbers
    print(f"\n🔢 Change Numbers:")
    change_number_count = sum(1 for r in client_results 
                               if r['success'] and r['metadata'].get('change_number'))
    print(f"   - Games with change_number: {change_number_count}/{len(client_results)}")
    
    if change_number_count > 0:
        print(f"   ✅ Steam Client provides change_number tracking!")
    else:
        print(f"   ⚠️  No change_numbers retrieved")


def main():
    """Run comprehensive test"""
    print("\n" + "🎮"*30)
    print("STEAM CLIENT BACKLOGIA INTEGRATION TEST")
    print("🎮"*30)
    
    # Check database exists
    if not DATABASE_PATH.exists():
        print(f"\n❌ Database not found: {DATABASE_PATH}")
        print("Please make sure Backlogia is set up.")
        return
    
    print(f"\n📁 Using database: {DATABASE_PATH}")
    
    # Get sample games
    print("\n📥 Loading Steam games from database...")
    games = get_steam_games_sample(limit=10)  # Test with 10 games
    
    if not games:
        print("❌ No Steam games found in database!")
        return
    
    print(f"✅ Loaded {len(games)} Steam games:")
    for game_id, name, store_id, _, _ in games[:5]:
        print(f"   - {name} (AppID {store_id})")
    if len(games) > 5:
        print(f"   ... and {len(games) - 5} more")
    
    # Test 1: HTTP API
    http_results, http_time = test_with_http_api(games)
    
    # Small break
    print("\n⏸️  Waiting 5 seconds before starting Steam Client test...")
    time.sleep(5)
    
    # Test 2: Steam Client
    client_results, client_time = test_with_steam_client(games)
    
    # Compare
    compare_results(http_results, http_time, client_results, client_time)
    
    # Final verdict
    print("\n" + "="*60)
    print("VERDICT")
    print("="*60)
    
    if client_time < http_time * 0.5:  # At least 2x faster
        print("🎉 Steam Client is SIGNIFICANTLY faster!")
        print("✅ Recommendation: Enable Steam Client in production")
    elif client_time < http_time:
        print("✅ Steam Client is faster")
        print("👍 Recommendation: Consider enabling Steam Client")
    else:
        print("⚠️  Steam Client not faster than HTTP API")
        print("🤔 Recommendation: Investigate or stick with HTTP API")


if __name__ == "__main__":
    main()
