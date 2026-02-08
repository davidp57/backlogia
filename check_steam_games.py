import sqlite3

conn = sqlite3.connect('backlogia.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM games WHERE store='steam'")
count = cursor.fetchone()[0]
print(f'Steam games in library: {count}')

cursor.execute("SELECT store_id, title FROM games WHERE store='steam' ORDER BY store_id LIMIT 10")
print('\nFirst 10 Steam games:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()
