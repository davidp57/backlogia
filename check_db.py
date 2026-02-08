"""Quick script to check database for update data."""
import sqlite3

conn = sqlite3.connect('game_library.db')
cursor = conn.cursor()

# Check games with last_modified
cursor.execute('SELECT COUNT(*) FROM games WHERE last_modified IS NOT NULL')
count_modified = cursor.fetchone()[0]
print(f'Games with last_modified: {count_modified}')

# Check game_depot_updates table
try:
    cursor.execute('SELECT COUNT(*) FROM game_depot_updates')
    count_updates = cursor.fetchone()[0]
    print(f'Total game_depot_updates records: {count_updates}')
except sqlite3.OperationalError:
    print('game_depot_updates table does not exist')

# Sample games with last_modified
cursor.execute('SELECT name, store, last_modified FROM games WHERE last_modified IS NOT NULL ORDER BY last_modified DESC LIMIT 10')
print('\nTop 10 most recently updated games:')
for i, row in enumerate(cursor.fetchall(), 1):
    print(f'  {i}. {row[0]} ({row[1]}): {row[2]}')

# Check which stores have last_modified data
cursor.execute('''
    SELECT store, COUNT(*) 
    FROM games 
    WHERE last_modified IS NOT NULL 
    GROUP BY store
''')
print('\nGames with last_modified by store:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} games')

# Check recent updates
try:
    cursor.execute('''
        SELECT g.name, gdu.update_timestamp, g.store 
        FROM game_depot_updates gdu 
        JOIN games g ON gdu.game_id = g.id 
        ORDER BY gdu.detected_at DESC 
        LIMIT 5
    ''')
    print('\nRecent game updates:')
    for row in cursor.fetchall():
        print(f'  {row[0]} ({row[2]}): {row[1]}')
except sqlite3.OperationalError as e:
    print(f'\nCould not query updates: {e}')

conn.close()
