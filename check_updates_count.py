"""Check how many update entries exist in the database."""
import sqlite3

DB_PATH = "game_library.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Count total updates
cursor.execute("SELECT COUNT(*) FROM game_depot_updates")
total = cursor.fetchone()[0]

print(f"\n✓ Total update entries: {total}")

if total > 0:
    # Show breakdown by type
    cursor.execute("""
        SELECT manifest_id, COUNT(*) as count
        FROM game_depot_updates
        GROUP BY manifest_id
        ORDER BY count DESC
    """)
    
    print("\nBreakdown by type:")
    for row in cursor.fetchall():
        update_type = row[0]
        count = row[1]
        print(f"  - {update_type}: {count}")
    
    # Show most recent updates
    cursor.execute("""
        SELECT g.name, gdu.manifest_id, gdu.update_timestamp
        FROM game_depot_updates gdu
        JOIN games g ON g.id = gdu.game_id
        ORDER BY gdu.fetched_at DESC
        LIMIT 5
    """)
    
    print("\nMost recent updates:")
    for row in cursor.fetchall():
        name = row[0]
        update_type = row[1]
        timestamp = row[2][:10] if row[2] else "N/A"
        print(f"  - {name} ({update_type}) - {timestamp}")

conn.close()
