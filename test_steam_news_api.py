"""Quick test to see Steam News API response structure."""
import requests
import json

# Test with multiple games to see feed_type variations
test_games = [
    (1091500, "Cyberpunk 2077"),  # Big game with lots of news
    (570, "Dota 2"),  # Valve game with official updates
    (1174180, "Red Dead Redemption 2"),  # Rockstar game
    (271590, "GTA V"),  # Another Rockstar
]

for appid, name in test_games:
    print(f"\n{'='*80}")
    print(f"Testing: {name} (appid: {appid})")
    print('='*80)
    
    url = "http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
    params = {
        'appid': appid,
        'count': 10,
        'maxlength': 300,
        'format': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'appnews' in data and 'newsitems' in data['appnews']:
            # Group by feed_type and feedname
            feed_types = {}
            for item in data['appnews']['newsitems']:
                feed_type = item.get('feed_type', 'unknown')
                feedname = item.get('feedname', 'unknown')
                
                if feed_type not in feed_types:
                    feed_types[feed_type] = {}
                if feedname not in feed_types[feed_type]:
                    feed_types[feed_type][feedname] = []
                
                feed_types[feed_type][feedname].append({
                    'title': item.get('title'),
                    'is_external': item.get('is_external_url', False)
                })
            
            print(f"\nFeed types found:")
            for feed_type, feeds in feed_types.items():
                print(f"  feed_type={feed_type}:")
                for feedname, items in feeds.items():
                    print(f"    {feedname}: {len(items)} items (external: {sum(1 for i in items if i['is_external'])})")
                    if items:
                        print(f"      Sample: {items[0]['title'][:80]}...")
    
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*80)
print("Feed type documentation:")
print("  0 = External articles (press, blogs)")
print("  1 = Official updates/patch notes (steam_community)")
print("  (Source: empirical observation)")

