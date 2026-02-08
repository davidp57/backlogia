"""Test SteamDB API to see what endpoints are available."""
import requests
import json

# Test the SteamDB API
base_url = "https://steamapi.xpaw.me"

# Try to get app info
test_appid = 271590  # GTA V

endpoints_to_test = [
    f"/v1/app/{test_appid}",
    f"/v1/app/{test_appid}/depots",
    f"/v1/app/{test_appid}/history",
    f"/v1/app/{test_appid}/changes",
    f"/ISteamApps/GetAppList/v2/",
]

print("Testing SteamDB API endpoints...")
print("=" * 80)

for endpoint in endpoints_to_test:
    url = f"{base_url}{endpoint}"
    print(f"\n🔍 Testing: {endpoint}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ JSON response received")
                print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                
                # Show a preview
                preview = json.dumps(data, indent=2)[:500]
                print(f"   Preview:\n{preview}...")
            except:
                print(f"   Content: {response.text[:200]}...")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "=" * 80)
