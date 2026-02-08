"""
Detect which version of appinfo.vdf format we have.
"""
import struct

appinfo_path = r"c:\jeux\Steam\appcache\appinfo.vdf"

with open(appinfo_path, 'rb') as f:
    # Read first 16 bytes
    data = f.read(16)
    
    magic = struct.unpack('<I', data[0:4])[0]
    universe = struct.unpack('<I', data[4:8])[0]
    next_8_bytes = struct.unpack('<Q', data[8:16])[0]
    
    print(f"Magic: 0x{magic:08X}")
    print(f"Universe: {universe}")
    print(f"Next 8 bytes (as uint64): {next_8_bytes}")
    print(f"Next 8 bytes (hex): {data[8:16].hex()}")
    
    # If next 8 bytes look like a string table offset, it's V41
    # If next 4 bytes look like an AppID, it's V40 or earlier
    next_4_bytes = struct.unpack('<I', data[8:12])[0]
    print(f"Next 4 bytes (as uint32): {next_4_bytes}")
    
    print("\n" + "=" * 60)
    
    if magic == 0x07564429:
        print("Magic indicates: V41 (June 2024)")
        
        # Check if this looks like a string table offset or an AppID
        if next_8_bytes > 1000000 and next_8_bytes < 100000000:
            print("Next 8 bytes look like: String Table Offset (V41)")
            print(f"  → String table at byte {next_8_bytes}")
        else:
            print("Next 8 bytes DON'T look like an offset")
            
        if next_4_bytes < 10000000:  # Typical AppID range
            print("Next 4 bytes look like: AppID (V40 format)")
            print(f"  → First AppID: {next_4_bytes}")
    elif magic == 0x07564428:
        print("Magic indicates: V40 (Dec 2022)")
        print(f"First AppID should be at offset 8: {next_4_bytes}")
    else:
        print(f"Unknown magic: 0x{magic:08X}")
    
    print("\n" + "=" * 60)
    print("Reading as V40 format (no string table offset):")
    
    f.seek(8)  # Skip just magic + universe
    
    # Read first 3 apps
    for i in range(3):
        appid = struct.unpack('<I', f.read(4))[0]
        if appid == 0:
            break
        
        size = struct.unpack('<I', f.read(4))[0]
        info_state = struct.unpack('<I', f.read(4))[0]
        last_updated = struct.unpack('<I', f.read(4))[0]
        pics_token = struct.unpack('<Q', f.read(8))[0]
        sha1_hash = f.read(20)
        change_number = struct.unpack('<I', f.read(4))[0]
        binary_sha1 = f.read(20)
        
        from datetime import datetime
        if last_updated > 0 and last_updated < 2147483647:
            date_str = datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_str = "Invalid"
        
        print(f"\nApp #{i+1}:")
        print(f"  AppID: {appid}")
        print(f"  Size: {size} bytes")
        print(f"  Info State: {info_state}")
        print(f"  Last Updated: {date_str}")
        print(f"  Change Number: {change_number}")
        
        # Skip VDF data
        vdf_size = size - 48
        if vdf_size > 0:
            f.read(vdf_size)
