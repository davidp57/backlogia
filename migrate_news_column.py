#!/usr/bin/env python3
# migrate_news_column.py
# Force migration of news_last_checked column

import sqlite3
from web.config import DATABASE_PATH
from web.database import ensure_news_and_status_tables

def check_and_migrate():
    """Check if news_last_checked column exists and migrate if needed."""
    print(f"Checking database: {DATABASE_PATH}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(games)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    print(f"\nCurrent columns in 'games' table:")
    for col, col_type in columns.items():
        print(f"  - {col}: {col_type}")
    
    # Check if migration needed
    if "news_last_checked" not in columns:
        print("\n❌ Column 'news_last_checked' is MISSING")
        print("\nRunning migration...")
        conn.close()
        
        # Run migration
        ensure_news_and_status_tables()
        
        # Verify
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(games)")
        columns_after = {row[1] for row in cursor.fetchall()}
        
        if "news_last_checked" in columns_after:
            print("✅ Migration successful! Column added.")
        else:
            print("❌ Migration failed. Column still missing.")
    else:
        print("\n✅ Column 'news_last_checked' already exists")
    
    # Show some stats
    cursor.execute("SELECT COUNT(*) FROM games WHERE news_last_checked IS NOT NULL")
    checked_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total_count = cursor.fetchone()[0]
    
    print(f"\nGames with news checked: {checked_count}/{total_count}")
    
    if checked_count > 0:
        cursor.execute("""
            SELECT name, news_last_checked 
            FROM games 
            WHERE news_last_checked IS NOT NULL 
            ORDER BY news_last_checked DESC 
            LIMIT 5
        """)
        print("\nMost recently checked games:")
        for name, checked_at in cursor.fetchall():
            print(f"  - {name}: {checked_at}")
    
    conn.close()
    print("\n✅ Database check complete!")

if __name__ == "__main__":
    check_and_migrate()
