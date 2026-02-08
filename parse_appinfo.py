"""
Parser for Steam's appinfo.vdf file to extract game update information.
Uses binary parsing to read V28/V29 format.
"""
import os
import struct
from datetime import datetime

def parse_steam_appinfo(appinfo_path):
    """
    Parse Steam's appinfo.vdf file and extract app metadata.
    
    Args:
        appinfo_path: Path to appinfo.vdf file
        
    Returns:
        Dictionary mapping appid -> app data
    """
    if not os.path.exists(appinfo_path):
        print(f"❌ File not found: {appinfo_path}")
        return {}
    
    print(f"📁 Parsing: {appinfo_path}")
    print(f"📊 File size: {os.path.getsize(appinfo_path) / (1024*1024):.2f} MB\n")
    
    apps = {}
    
    try:
        with open(appinfo_path, 'rb') as f:
            # Read header
            magic = struct.unpack('<I', f.read(4))[0]
            universe = struct.unpack('<I', f.read(4))[0]
            
            print(f"Magic: 0x{magic:08X}")
            print(f"Universe: {universe}")
            
            if magic == 0x07564428:  # V28 format ('(VD' + 0x28)
                print("Format: V28 (Steam's binary appinfo)")
            elif magic == 0x07564429:  # V29 format
                print("Format: V29")
            else:
                print(f"⚠️  Unknown format: 0x{magic:08X}")
                return {}
            
            # For V28/V29, read apps one by one
            app_count = 0
            errors = 0
            max_errors = 5
            
            print("📖 Reading app entries...\n")
            
            while True:
                # Save position for debugging
                pos = f.tell()
                
                # Read app ID (4 bytes)
                appid_bytes = f.read(4)
                if len(appid_bytes) < 4:
                    print(f"End of file at position {pos}")
                    break
                    
                appid = struct.unpack('<I', appid_bytes)[0]
                
                if app_count < 3:  # Debug first 3 apps
                    print(f"App #{app_count + 1} at position {pos}: AppID = {appid}")
                
                if appid == 0:  # End marker
                    print(f"Found end marker (appid=0) at position {pos}")
                    break
                
                try:
                    # Read size (4 bytes) - this is the size of the VDF data section only
                    size_bytes = f.read(4)
                    if len(size_bytes) < 4:
                        break
                    size = struct.unpack('<I', size_bytes)[0]
                    
                    if app_count < 3:
                        print(f"  Size field: {size} bytes")
                    
                    # Read info_state (4 bytes)
                    info_state = struct.unpack('<I', f.read(4))[0]
                    
                    # Read last_updated (4 bytes)
                    last_updated = struct.unpack('<I', f.read(4))[0]
                    
                    if app_count < 3:
                        print(f"  Info state: {info_state}")
                        print(f"  Last updated (raw): {last_updated}")
                        if last_updated > 0 and last_updated < 2000000000:  # Reasonable timestamp
                            from datetime import datetime
                            print(f"  Last updated: {datetime.fromtimestamp(last_updated)}")
                    
                    # Read access_token (8 bytes)
                    f.read(8)  # Skip access token
                    
                    # Read SHA1 hash (20 bytes)
                    f.read(20)  # Skip SHA1
                    
                    # Read change_number (4 bytes)
                    change_number = struct.unpack('<I', f.read(4))[0]
                    
                    if app_count < 3:
                        print(f"  Change number: {change_number}")
                        print(f"  About to skip {size} bytes of VDF data\n")
                    
                    # The 'size' field contains the size of the VDF data section
                    # Skip the VDF data for now (we're only interested in metadata)
                    if size > 0:
                        f.read(size)
                    
                    # Store app info
                    apps[appid] = {
                        'appid': appid,
                        'last_updated': last_updated,
                        'change_number': change_number,
                        'info_state': info_state,
                    }
                    
                    app_count += 1
                    
                    # Show progress every 500 apps
                    if app_count % 500 == 0:
                        print(f"Processed {app_count} apps...", end='\r')
                        
                except Exception as e:
                    errors += 1
                    if errors <= max_errors:
                        print(f"\n⚠️  Error reading app {appid} at position {pos}: {e}")
                        import traceback
                        traceback.print_exc()
                    if errors >= max_errors:
                        print("\n❌ Too many errors, stopping parse")
                        break
                    continue
            
            print(f"\n✅ Parsed {len(apps)} apps from appinfo.vdf\n")
            
    except Exception as e:
        print(f"❌ Error parsing appinfo: {e}")
        import traceback
        traceback.print_exc()
        return {}
    
    # Show some examples
    print("📋 Sample apps with update info:")
    for i, (appid, info) in enumerate(list(apps.items())[:10]):
        if info['last_updated'] > 0:
            date_str = datetime.fromtimestamp(info['last_updated']).strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_str = "N/A"
        print(f"  {appid}: Updated {date_str} (Change #{info['change_number']})")
    
    return apps


if __name__ == '__main__':
    # Default Steam path
    steam_path = r"c:\jeux\Steam\appcache\appinfo.vdf"
    
    # Allow override via command line
    import sys
    if len(sys.argv) > 1:
        steam_path = sys.argv[1]
    
    apps = parse_steam_appinfo(steam_path)
    
    if apps:
        print(f"\n✅ Successfully parsed {len(apps)} Steam apps")
        print(f"💾 Data structure ready for integration")
