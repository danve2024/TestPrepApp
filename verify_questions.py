"""Verify question count in database."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'question_bank.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM QUESTIONS')
total = cur.fetchone()[0]
print(f'Total questions: {total}')

cur.execute('SELECT COUNT(*) FROM QUESTIONS WHERE Domain LIKE "%Math%"')
math = cur.fetchone()[0]
print(f'Math questions: {math}')

cur.execute('SELECT COUNT(*) FROM QUESTIONS WHERE Domain NOT LIKE "%Math%" OR Domain IS NULL')
english = cur.fetchone()[0]
print(f'English questions: {english}')

# Check difficulty distribution
cur.execute('SELECT Difficulty, COUNT(*) FROM QUESTIONS GROUP BY Difficulty')
print('\nDifficulty distribution:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Check domain distribution
cur.execute('SELECT Domain, COUNT(*) FROM QUESTIONS WHERE Domain NOT LIKE "%Math%" GROUP BY Domain')
print('\nEnglish Domain distribution:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()

