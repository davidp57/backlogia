"""Parse Steam's appinfo.vdf file to extract game update information."""
import struct
import os

# Based on: https://github.com/SteamDatabase/SteamAppInfo

def read_cstring(f):
    """Read a null-terminated string."""
    chars = []
    while True:
        c = f.read(1)
        if not c or c == b'\x00':
            break
        chars.append(c)
    return b''.join(chars).decode('utf-8', errors='ignore')

def read_int32(f):
    """Read a 32-bit integer."""
    data = f.read(4)
    if len(data) < 4:
        return None
    return struct.unpack('<I', data)[0]

def read_uint64(f):
    """Read a 64-bit unsigned integer."""
    data = f.read(8)
    if len(data) < 8:
        return None
    return struct.unpack('<Q', data)[0]

def skip_value(f, value_type):
    """Skip a value based on its type."""
    if value_type == 0x00:  # String
        read_cstring(f)
    elif value_type == 0x01:  # Int32
        f.read(4)
    elif value_type == 0x02:  # Float
        f.read(4)
    elif value_type == 0x07:  # Uint64
        f.read(8)
    elif value_type == 0x08:  # End of section
        pass

def parse_appinfo(file_path):
    """Parse appinfo.vdf and extract basic info about apps."""
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    
    print(f"📂 Parsing: {file_path}")
    print(f"   Size: {os.path.getsize(file_path) / 1024 / 1024:.1f} MB\n")
    
    apps = []
    
    try:
        with open(file_path, 'rb') as f:
            # Read first bytes to analyze format
            first_bytes = f.read(32)
            print(f"First 32 bytes (hex): {first_bytes.hex()}")
            print(f"First 32 bytes (repr): {repr(first_bytes)}")
            
            # Try different magic numbers
            f.seek(0)
            magic = f.read(4)
            magic_int = struct.unpack('<I', magic)[0]
            print(f"\nMagic as hex: {magic.hex()}")
            print(f"Magic as int: {magic_int}")
            print(f"Magic as text: {repr(magic)}")
            
            f.seek(0)
            # Check for V27 or V28 format (reading as little-endian uint32)
            magic_num = read_int32(f)
            if magic_num == 0x07564429:  # V28 format (little-endian)
                print("\n✓ Detected V28 format")
            elif magic_num == 0x07564427:  # V27 format (if it exists)
                print("\n✓ Detected V27 format")
            else:
                print(f"\n❌ Unknown format: 0x{magic_num:08x}")
                print("This might be a newer Steam format that needs investigation.")
                return None
            
            universe = read_int32(f)
            print(f"✓ Header valid (universe: {universe})")
            
            # Read apps
            count = 0
            while True:
                # Read AppID
                appid = read_int32(f)
                if appid is None or appid == 0:
                    break
                
                # Read size
                size = read_int32(f)
                if size is None:
                    break
                
                # Read state
                state = read_int32(f)
                
                # Read last_updated timestamp
                last_updated = read_int32(f)
                
                # Read access token
                access_token = read_uint64(f)
                
                # Read SHA1 hash
                sha1_hash = f.read(20)
                
                # Read change number
                change_number = read_int32(f)
                
                # Skip the actual data for now (we'd need full VDF parser for this)
                # For now, just collect basic metadata
                f.read(size - 48)  # Skip remaining data
                
                apps.append({
                    'appid': appid,
                    'size': size,
                    'state': state,
                    'last_updated': last_updated,
                    'change_number': change_number
                })
                
                count += 1
                if count % 1000 == 0:
                    print(f"  ... processed {count} apps")
            
            print(f"\n✓ Found {len(apps)} apps total")
            
            return apps
    
    except Exception as e:
        print(f"❌ Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # Try default Steam location
    appinfo_path = r"c:\jeux\Steam\appcache\appinfo.vdf"
    
    apps = parse_appinfo(appinfo_path)
    
    if apps:
        print("\n" + "="*60)
        print("Sample apps:")
        print("="*60)
        
        # Show first 10 apps
        for app in apps[:10]:
            from datetime import datetime
            timestamp_str = datetime.fromtimestamp(app['last_updated']).strftime('%Y-%m-%d %H:%M:%S') if app['last_updated'] > 0 else 'N/A'
            print(f"AppID {app['appid']:8} | Updated: {timestamp_str} | Change: {app['change_number']}")
        
        # Show some stats
        print("\n" + "="*60)
        print("Statistics:")
        print("="*60)
        
        # Apps with recent updates (last 30 days)
        import time
        thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
        recent = [a for a in apps if a['last_updated'] > thirty_days_ago]
        print(f"Apps updated in last 30 days: {len(recent)}")
        
        # Apps with timestamps
        with_timestamps = [a for a in apps if a['last_updated'] > 0]
        print(f"Apps with update timestamps: {len(with_timestamps)}")
