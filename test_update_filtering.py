"""Test filtering official Steam announcements to find real updates."""
import requests

test_games = [
    (570, "Dota 2"),
    (1174180, "Red Dead Redemption 2"),
    (271590, "GTA V"),
    (730, "CS:GO"),
    (292030, "The Witcher 3"),
]

# Mots-clés pour vraies mises à jour
UPDATE_KEYWORDS = ['update', 'patch', 'hotfix', 'bugfix', 'version', 'build', 'fixed', 'changelog']

# Mots-clés pour exclure (promos, events, DLC)
EXCLUDE_KEYWORDS = ['sale', 'discount', 'free weekend', 'double xp', 'triple', 'rewards', 
                    'event', 'contest', 'tournament', 'season pass', 'new mode', 
                    'available now', 'out now', 'coming soon']

def is_real_update(title: str, contents: str) -> tuple[bool, str]:
    """Determine if a news item is a real technical update."""
    text = f"{title} {contents}".lower()
    
    # Check for exclusion keywords first
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in text:
            return False, f"excluded: '{keyword}'"
    
    # Check for update keywords
    for keyword in UPDATE_KEYWORDS:
        if keyword in title.lower():
            return True, f"matched: '{keyword}' in title"
    
    return False, "no update keywords in title"

for appid, name in test_games:
    print(f"\n{'='*80}")
    print(f"{name} (appid: {appid})")
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
            # Filter for official announcements
            official_news = [
                item for item in data['appnews']['newsitems']
                if item.get('feed_type') == 1 and 
                   item.get('feedname') == 'steam_community_announcements'
            ]
            
            print(f"\nFound {len(official_news)} official announcements")
            
            real_updates = []
            filtered_out = []
            
            for item in official_news:
                title = item.get('title', '')
                contents = item.get('contents', '')
                is_update, reason = is_real_update(title, contents)
                
                if is_update:
                    real_updates.append((title, reason))
                else:
                    filtered_out.append((title, reason))
            
            print(f"\n✅ Real updates: {len(real_updates)}")
            for title, reason in real_updates:
                print(f"  • {title[:70]}... ({reason})")
            
            print(f"\n❌ Filtered out: {len(filtered_out)}")
            for title, reason in filtered_out[:3]:  # Show first 3
                print(f"  • {title[:70]}... ({reason})")
    
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*80)
print("Conclusion: Avec ces filtres, on garde uniquement les vraies mises à jour techniques")
