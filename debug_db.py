import sqlite3
import os

# Find the database file
db_paths = ['instance/progress_data.db', 'progress_data.db', 'users_data.db']
db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print('No database found')
    exit()

print(f'Checking database: {db_path}')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if official_test_scores table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='official_test_scores'")
table_exists = cursor.fetchone()
print(f'official_test_scores table exists: {bool(table_exists)}')

if table_exists:
    # Show table schema
    cursor.execute('PRAGMA table_info(official_test_scores)')
    columns = cursor.fetchall()
    print('Table schema:')
    for col in columns:
        print(f'  {col}')
    
    # Show recent entries
    cursor.execute('SELECT * FROM official_test_scores ORDER BY TestID DESC LIMIT 5')
    rows = cursor.fetchall()
    print(f'Recent entries ({len(rows)}):')
    for row in rows:
        print(f'  {row}')

conn.close()
