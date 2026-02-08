"""
Parser for Steam's appinfo.vdf file (V41 format - June 2024).
Uses correct binary structure with string table.
"""
import os
import struct
from datetime import datetime

def parse_steam_appinfo_v41(appinfo_path, max_apps=None):
    """
    Parse Steam's appinfo.vdf file in V41 format.
    
    Format V41 (0x07564429) structure:
    Header:
      - uint32 (4): Magic (0x07564429)
      - uint32 (4): Universe (1)
      - int64 (8): String Table Offset (NEW in V41!)
    
    App Entry (repeated):
      - uint32 (4): App ID
      - uint32 (4): Size (VDF data size)
      - uint32 (4): Info State
      - uint32 (4): Last Updated (Unix timestamp)
      - uint64 (8): PICS Token
      - bytes (20): SHA-1 Hash
      - uint32 (4): Change Number
      - bytes (20): Binary SHA-1
      - bytes (variable): Binary VDF data
    
    Args:
        appinfo_path: Path to appinfo.vdf file
        max_apps: Maximum number of apps to parse (None = all)
        
    Returns:
        Dictionary mapping appid -> app metadata
    """
    if not os.path.exists(appinfo_path):
        print(f"❌ File not found: {appinfo_path}")
        return {}
    
    print(f"📁 Parsing: {appinfo_path}")
    print(f"📊 File size: {os.path.getsize(appinfo_path) / (1024*1024):.2f} MB\n")
    
    apps = {}
    
    try:
        with open(appinfo_path, 'rb') as f:
            # Read V41 header (16 bytes total)
            magic = struct.unpack('<I', f.read(4))[0]
            universe = struct.unpack('<I', f.read(4))[0]
            string_table_offset = struct.unpack('<Q', f.read(8))[0]  # NEW in V41
            
            print(f"Magic: 0x{magic:08X}")
            print(f"Universe: {universe}")
            print(f"String Table Offset: {string_table_offset}")
            
            if magic != 0x07564429:
                print(f"⚠️  Expected V41 format (0x07564429), got 0x{magic:08X}")
                return {}
            
            print("Format: V41 (June 2024)\n")
            
            # Read apps until we hit the end marker
            app_count = 0
            while True:
                if max_apps and app_count >= max_apps:
                    print(f"\n⚠️  Reached max_apps limit ({max_apps})")
                    break
                
                # Check if we've reached string table
                current_pos = f.tell()
                if current_pos >= string_table_offset:
                    print(f"\n✅ Reached string table at position {current_pos}")
                    break
                
                # Read App ID
                appid_bytes = f.read(4)
                if len(appid_bytes) < 4:
                    print(f"\n✅ End of file at position {current_pos}")
                    break
                
                appid = struct.unpack('<I', appid_bytes)[0]
                if appid == 0:
                    print(f"\n✅ Found end marker (appid=0) at position {current_pos}")
                    break
                
                # Read app metadata
                size = struct.unpack('<I', f.read(4))[0]
                info_state = struct.unpack('<I', f.read(4))[0]
                last_updated = struct.unpack('<I', f.read(4))[0]
                pics_token = struct.unpack('<Q', f.read(8))[0]
                sha1_hash = f.read(20)
                change_number = struct.unpack('<I', f.read(4))[0]
                binary_sha1 = f.read(20)  # V40+ field
                
                # Skip binary VDF data (we only want metadata)
                vdf_data_size = size - 48  # size excludes the fixed-size fields
                if vdf_data_size > 0:
                    f.read(vdf_data_size)
                
                # Store app metadata
                apps[appid] = {
                    'appid': appid,
                    'last_updated': last_updated,
                    'change_number': change_number,
                    'info_state': info_state,
                    'pics_token': pics_token,
                }
                
                app_count += 1
                
                # Show progress
                if app_count % 500 == 0:
                    print(f"Processed {app_count} apps...", end='\r')
            
            print(f"\n✅ Parsed {len(apps)} apps from appinfo.vdf\n")
            
    except Exception as e:
        print(f"❌ Error parsing appinfo: {e}")
        import traceback
        traceback.print_exc()
        return {}
    
    # Show sample apps
    print("📋 Sample apps with update info:")
    valid_timestamps = []
    
    for appid, info in list(apps.items())[:20]:
        timestamp = info['last_updated']
        if timestamp > 0 and timestamp < 2147483647:  # Valid Unix timestamp
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            valid_timestamps.append(timestamp)
            if len(valid_timestamps) <= 10:  # Show first 10 valid ones
                print(f"  {appid}: Updated {date_str} (Change #{info['change_number']})")
    
    if valid_timestamps:
        print(f"\n📊 {len(valid_timestamps)} apps have valid timestamps")
        print(f"   Most recent: {datetime.fromtimestamp(max(valid_timestamps)).strftime('%Y-%m-%d')}")
        print(f"   Oldest: {datetime.fromtimestamp(min(valid_timestamps)).strftime('%Y-%m-%d')}")
    
    return apps


if __name__ == '__main__':
    import sys
    
    # Default Steam path
    steam_path = r"c:\jeux\Steam\appcache\appinfo.vdf"
    
    # Allow override via command line
    if len(sys.argv) > 1:
        steam_path = sys.argv[1]
    
    # Parse small sample first to test
    print("=" * 60)
    print("Testing with first 50 apps...")
    print("=" * 60 + "\n")
    apps = parse_steam_appinfo_v41(steam_path, max_apps=50)
    
    if apps:
        print(f"\n✅ Successfully parsed {len(apps)} Steam apps")
        print("💾 Data structure ready for integration")
        
        # Ask if user wants to parse all apps
        print("\n" + "=" * 60)
        response = input("Parse all apps? (y/n): ")
        if response.lower() == 'y':
            print("\n" + "=" * 60)
            print("Parsing all apps...")
            print("=" * 60 + "\n")
            apps = parse_steam_appinfo_v41(steam_path)
            print(f"\n✅ Complete! Parsed {len(apps)} total Steam apps")
