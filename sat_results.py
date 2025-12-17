import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class SATResultsDB:
    def __init__(self, db_path: str = 'instance/sat_results.db'):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create official SAT results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS official_sat_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    test_date DATE NOT NULL,
                    ebrw_score INTEGER NOT NULL CHECK (ebrw_score BETWEEN 200 AND 800 AND ebrw_score % 10 = 0),
                    math_score INTEGER NOT NULL CHECK (math_score BETWEEN 200 AND 800 AND math_score % 10 = 0),
                    total_score INTEGER GENERATED ALWAYS AS (ebrw_score + math_score) STORED,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, test_date)
                )
            ''')

            # Create practice test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS practice_test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    test_date DATE NOT NULL,
                    test_name TEXT NOT NULL,
                    ebrw_score INTEGER NOT NULL CHECK (ebrw_score BETWEEN 200 AND 800 AND ebrw_score % 10 = 0),
                    math_score INTEGER NOT NULL CHECK (math_score BETWEEN 200 AND 800 AND math_score % 10 = 0),
                    total_score INTEGER GENERATED ALWAYS AS (ebrw_score + math_score) STORED,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create index for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_official_user ON official_sat_results(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_practice_user ON practice_test_results(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_official_date ON official_sat_results(test_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_practice_date ON practice_test_results(test_date)')

    def add_official_result(self, user_id: int, test_date: str, ebrw_score: int, math_score: int) -> int:
        """Add an official SAT test result for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO official_sat_results (user_id, test_date, ebrw_score, math_score)
                VALUES (?, ?, ?, ?)
            ''', (user_id, test_date, ebrw_score, math_score))
            return cursor.lastrowid

    def add_practice_result(self, user_id: int, test_date: str, test_name: str, ebrw_score: int, math_score: int) -> int:
        """Add a practice test result for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO practice_test_results (user_id, test_date, test_name, ebrw_score, math_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, test_date, test_name, ebrw_score, math_score))
            return cursor.lastrowid

    def get_official_results(self, user_id: int, sort_by: str = 'date', order: str = 'desc') -> List[Dict]:
        """Get all official SAT results for a user, sorted by the specified column."""
        valid_sort_columns = {'date': 'test_date', 'ebrw': 'ebrw_score', 'math': 'math_score', 'total': 'total_score'}
        sort_column = valid_sort_columns.get(sort_by, 'test_date')
        order = 'DESC' if order.lower() == 'desc' else 'ASC'
        
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, test_date, ebrw_score, math_score, total_score
                FROM official_sat_results
                WHERE user_id = ?
                ORDER BY {sort_column} {order}
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_practice_results(self, user_id: int, sort_by: str = 'date', order: str = 'desc') -> List[Dict]:
        """Get all practice test results for a user, sorted by the specified column."""
        valid_sort_columns = {
            'date': 'test_date', 
            'name': 'test_name',
            'ebrw': 'ebrw_score', 
            'math': 'math_score', 
            'total': 'total_score'
        }
        sort_column = valid_sort_columns.get(sort_by, 'test_date')
        order = 'DESC' if order.lower() == 'desc' else 'ASC'
        
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, test_date, test_name, ebrw_score, math_score, total_score
                FROM practice_test_results
                WHERE user_id = ?
                ORDER BY {sort_column} {order}
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_superscore(self, user_id: int) -> Dict[str, int]:
        """Calculate the superscore for a user based on their best section scores."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get best EBRW and Math scores from official tests
            cursor.execute('''
                SELECT 
                    COALESCE(MAX(ebrw_score), 0) as best_ebrw,
                    COALESCE(MAX(math_score), 0) as best_math
                FROM official_sat_results
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return {'ebrw': 0, 'math': 0, 'total': 0}
                
            best_ebrw = result[0] or 0
            best_math = result[1] or 0
            
            return {
                'ebrw': best_ebrw,
                'math': best_math,
                'total': best_ebrw + best_math
            }

# Create a global instance
sat_db = SATResultsDB()
