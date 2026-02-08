"""
Test POC pour le Steam Client Manager.
Teste la connexion anonyme et la récupération de product info.
"""
import sys
import time
from pathlib import Path

# Add web to path
sys.path.insert(0, str(Path(__file__).parent))

from web.services.steam_client_manager import get_steam_client


def test_anonymous_login():
    """Test 1: Connexion anonyme"""
    print("\n" + "="*60)
    print("TEST 1: Anonymous Login")
    print("="*60)
    
    client = get_steam_client()
    success = client.connect()
    
    if success:
        print("✅ Test PASSED: Anonymous login successful")
        return True
    else:
        print("❌ Test FAILED: Could not connect anonymously")
        return False


def test_get_product_info():
    """Test 2: Récupération de product info pour quelques jeux connus"""
    print("\n" + "="*60)
    print("TEST 2: Get Product Info")
    print("="*60)
    
    client = get_steam_client()
    
    # Test avec 3 jeux populaires
    test_apps = [
        (730, "Counter-Strike 2"),
        (570, "Dota 2"),
        (1091500, "Cyberpunk 2077"),
    ]
    
    app_ids = [app_id for app_id, _ in test_apps]
    
    print(f"\nFetching info for: {', '.join(name for _, name in test_apps)}")
    
    start = time.time()
    results = client.get_product_info(app_ids)
    elapsed = time.time() - start
    
    print(f"\n⏱️  Request took {elapsed:.2f} seconds")
    
    success = True
    for app_id, name in test_apps:
        if app_id in results:
            info = results[app_id]
            change_num = info.get('change_number', 'N/A')
            print(f"✅ {name} (AppID {app_id}): change_number={change_num}")
        else:
            print(f"❌ {name} (AppID {app_id}): No data received")
            success = False
    
    if success:
        print("\n✅ Test PASSED: All apps retrieved successfully")
    else:
        print("\n⚠️  Test PARTIAL: Some apps failed")
    
    return success


def test_bulk_performance():
    """Test 3: Performance test avec 50 apps"""
    print("\n" + "="*60)
    print("TEST 3: Bulk Performance (50 apps)")
    print("="*60)
    
    client = get_steam_client()
    
    # 50 AppIDs Steam populaires
    bulk_apps = [
        730, 570, 440, 271590, 252490, 578080, 1172470, 1091500, 
        377160, 8930, 292030, 582010, 813780, 779340, 1145360,
        548430, 359550, 620, 413150, 227300, 250900, 322330,
        346110, 255710, 8930, 435150, 1086940, 374320, 1174180,
        1517290, 1599340, 1172380, 311210, 990080, 1938090, 812140,
        524220, 1332010, 1203220, 976310, 1237970, 427520, 291550,
        105600, 239140, 304930, 236390, 1245620, 466560, 1237320
    ]
    
    print(f"Fetching info for {len(bulk_apps)} apps...")
    
    start = time.time()
    results = client.get_product_info(bulk_apps)
    elapsed = time.time() - start
    
    print(f"\n⏱️  Bulk request took {elapsed:.2f} seconds")
    print(f"📊 Success rate: {len(results)}/{len(bulk_apps)} apps ({len(results)/len(bulk_apps)*100:.1f}%)")
    print(f"⚡ Average: {elapsed/len(bulk_apps)*1000:.0f}ms per app")
    
    # Compare avec HTTP API (estimé à 1.5s/app)
    http_estimate = len(bulk_apps) * 1.5
    speedup = http_estimate / elapsed if elapsed > 0 else 0
    
    print(f"\n📈 Performance vs HTTP API:")
    print(f"   - HTTP API estimated time: {http_estimate:.0f}s ({http_estimate/60:.1f} minutes)")
    print(f"   - Steam Client time: {elapsed:.1f}s")
    print(f"   - Speedup: {speedup:.1f}x faster")
    
    if elapsed < 30:
        print("\n✅ Test PASSED: Bulk request under 30 seconds")
        return True
    else:
        print("\n⚠️  Test WARNING: Bulk request took longer than expected")
        return False


def test_change_number_tracking():
    """Test 4: Simulation du tracking de change_number"""
    print("\n" + "="*60)
    print("TEST 4: Change Number Tracking Simulation")
    print("="*60)
    
    client = get_steam_client()
    
    app_id = 730  # CS2
    
    print(f"Fetching change_number for AppID {app_id}...")
    
    # Première lecture
    change1 = client.get_change_number(app_id)
    print(f"First read: change_number = {change1}")
    
    # Attendre 2 secondes
    print("Waiting 2 seconds...")
    time.sleep(2)
    
    # Deuxième lecture
    change2 = client.get_change_number(app_id)
    print(f"Second read: change_number = {change2}")
    
    if change1 and change2:
        if change1 == change2:
            print(f"\n✅ Test PASSED: change_number stable ({change1})")
            print("   (This is expected - game hasn't updated in 2 seconds)")
        else:
            print(f"\n🎉 Test BONUS: change_number changed! ({change1} -> {change2})")
            print("   (This means the game was updated during the test!)")
        return True
    else:
        print("\n❌ Test FAILED: Could not retrieve change_number")
        return False


def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("STEAM CLIENT MANAGER POC")
    print("🚀"*30)
    
    tests = [
        ("Anonymous Login", test_anonymous_login),
        ("Product Info", test_get_product_info),
        ("Bulk Performance", test_bulk_performance),
        ("Change Number Tracking", test_change_number_tracking),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Cleanup
    print("\n" + "="*60)
    print("CLEANUP")
    print("="*60)
    client = get_steam_client()
    client.disconnect()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n📊 Total: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.0f}%)")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Steam Client is ready for integration.")
    elif passed_count > 0:
        print("\n⚠️  SOME TESTS FAILED: Review logs above for details.")
    else:
        print("\n❌ ALL TESTS FAILED: Steam Client not working as expected.")


if __name__ == "__main__":
    main()
