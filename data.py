import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from typing import Tuple, List, Any, Optional, Dict
from datetime import datetime, date


class BaseDB:
    """
    Base class for managing multiple SQLite databases.
    It centralizes connection logic and SQL execution across different database files.
    """

    def __init__(self, db_configs: Dict[str, Dict[str, str]]):
        """
        Initializes the base database manager with a configuration dictionary.

        :param db_configs: A dictionary where keys are logical names (e.g., 'users_data')
                           and values are dictionaries containing 'file' (DB filename)
                           and 'schema' (SQL for table creation).
        """
        self.db_configs = db_configs
        print("Initializing base databases...")
        self._initialize_all_dbs()

    def _get_connection(self, db_key: str) -> sqlite3.Connection:
        """Internal helper to get a connection to a specific database."""
        db_file = self.db_configs[db_key]['file']
        return sqlite3.connect(db_file)

    def _initialize_all_dbs(self):
        """Initializes all configured database files."""
        for db_key, config in self.db_configs.items():
            conn = None
            try:
                conn = sqlite3.connect(config['file'])
                cursor = conn.cursor()
                cursor.executescript(config['schema'])
                conn.commit()
                print(f"✅ Initialized database: {db_key} ({config['file']})")
            except sqlite3.Error as e:
                print(f"❌ Error initializing database {db_key}: {e}")
            finally:
                if conn:
                    conn.close()

    def execute_sql(self, db_key: str, sql_query: str, params: Tuple[Any, ...] = ()) -> Tuple[
        Optional[List[str]], Optional[List[Tuple]]]:
        """
        Executes arbitrary SQL requests on a specified database.

        :param db_key: The logical name of the database (e.g., 'users_data').
        :param sql_query: The SQL query to execute.
        :param params: Parameters for the SQL query.
        :returns: (columns, results) tuple. Results is None for non-SELECT queries.
        """
        if db_key not in self.db_configs:
            return [f"❌ Error: Database key '{db_key}' not found in configuration."], None

        conn = self._get_connection(db_key)
        cursor = conn.cursor()

        try:
            cursor.execute(sql_query, params)
            if sql_query.strip().upper().startswith('SELECT'):
                # Return column names and fetched data
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                return columns, results
            else:
                conn.commit()
                # Non-SELECT queries return a success message and None for results
                return [f"✅ SQL executed successfully on {db_key}. Rows affected: {cursor.rowcount}"], None
        except sqlite3.Error as e:
            conn.rollback()
            return [f"❌ SQL Error on {db_key}: {e}"], None
        finally:
            conn.close()

    def cleanup_all(self):
        """Deletes all configured database files."""
        for db_key, config in self.db_configs.items():
            if os.path.exists(config['file']):
                os.remove(config['file'])
                print(f"Database file '{config['file']}' cleaned up.")


class UsersDB(BaseDB):
    """
    Manages USERS_DATA and LOGIN_INFORMATION, inheriting multi-DB functionality
    from BaseDB and providing domain-specific methods.
    """

    USERS_KEY = 'users_data'
    LOGIN_KEY = 'login_info'
    PROGRESS_KEY = 'progress_data'

    DB_CONFIGS = {
        USERS_KEY: {
            'file': 'users_data.db',
            'schema': """
                CREATE TABLE IF NOT EXISTS users (
                    UserID INTEGER PRIMARY KEY,
                    Email TEXT NOT NULL UNIQUE,
                    FirstName TEXT,
                    LastName TEXT,
                    Nickname TEXT,
                    BirthDate DATE,
                    AccountType TEXT DEFAULT 'private',
                    Avatar TEXT
                );
            """
        },
        LOGIN_KEY: {
            'file': 'login_info.db',
            'schema': """
                CREATE TABLE IF NOT EXISTS logins (
                    UserID INTEGER PRIMARY KEY,
                    Username TEXT NOT NULL UNIQUE,
                    PasswordHash TEXT NOT NULL
                );
            """
        },
        PROGRESS_KEY: {
            'file': 'progress_data.db',
            'schema': """
                CREATE TABLE IF NOT EXISTS user_progress (
                    ProgressID INTEGER PRIMARY KEY,
                    UserID INTEGER NOT NULL,
                    TotalScore INTEGER DEFAULT 1600,
                    EBRWScore INTEGER DEFAULT 800,
                    MathScore INTEGER DEFAULT 800,
                    CurrentStreak INTEGER DEFAULT 1,
                    LastActiveDate DATE DEFAULT CURRENT_DATE,
                    StreakGoal INTEGER DEFAULT 7,
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                );

                CREATE TABLE IF NOT EXISTS official_test_scores (
                    TestID INTEGER PRIMARY KEY,
                    UserID INTEGER NOT NULL,
                    TestDate DATE,
                    TotalScore INTEGER,
                    EBRWScore INTEGER,
                    MathScore INTEGER,
                    TestType TEXT DEFAULT 'official',
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                );

                CREATE TABLE IF NOT EXISTS practice_results (
                    PracticeID INTEGER PRIMARY KEY,
                    UserID INTEGER NOT NULL,
                    PracticeName TEXT,
                    PracticeDate DATE DEFAULT CURRENT_DATE,
                    Score INTEGER,
                    MaxScore INTEGER,
                    PracticeType TEXT,
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                );

                CREATE TABLE IF NOT EXISTS daily_quests (
                    QuestID INTEGER PRIMARY KEY,
                    UserID INTEGER NOT NULL,
                    QuestName TEXT,
                    TargetValue INTEGER,
                    CurrentValue INTEGER DEFAULT 0,
                    QuestDate DATE DEFAULT CURRENT_DATE,
                    Completed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                );

                CREATE TABLE IF NOT EXISTS user_settings (
                    SettingID INTEGER PRIMARY KEY,
                    UserID INTEGER NOT NULL,
                    DarkMode BOOLEAN DEFAULT FALSE,
                    Sounds BOOLEAN DEFAULT TRUE,
                    Haptics BOOLEAN DEFAULT TRUE,
                    Friends BOOLEAN DEFAULT TRUE,
                    Notifications BOOLEAN DEFAULT TRUE,
                    Emails BOOLEAN DEFAULT TRUE,
                    ProductivityMode BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                );

                CREATE TABLE IF NOT EXISTS vocabulary_progress (
                    VocabID INTEGER PRIMARY KEY,
                    UserID INTEGER NOT NULL,
                    Word TEXT,
                    MasteryLevel INTEGER DEFAULT 0,
                    LastPracticed DATE,
                    TimesCorrect INTEGER DEFAULT 0,
                    TimesIncorrect INTEGER DEFAULT 0,
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                );
            """
        }
    }

    def __init__(self):
        """Initializes the multi-database manager with user configurations."""
        super().__init__(self.DB_CONFIGS)
        print("User-specific database logic ready.")

    # --- Core Data Modification (CRUD) ---

    def create_user(self, email: str, first_name: str, username: str, password: str) -> Optional[int]:
        """
        Creates a new user entry across both databases.
        It attempts to perform a transaction across the two files.
        Returns the new UserID or None on failure.
        """

        # 1. Insert into USERS_DATA to get the new UserID
        result_u, _ = self.execute_sql(
            self.USERS_KEY,
            "INSERT INTO users (Email, FirstName) VALUES (?, ?)",
            (email, first_name)
        )

        if result_u and "SQL executed successfully" in result_u[0]:
            # Retrieve the newly inserted UserID
            _, id_row = self.execute_sql(self.USERS_KEY, "SELECT MAX(UserID) FROM users")
            user_id = id_row[0][0] if id_row and id_row[0] else None

            if user_id is None:
                print("Could not retrieve new UserID after insert.")
                return None

            # 2. Hash the password
            password_hash = generate_password_hash(password)

            # 3. Insert into LOGIN_INFORMATION using the retrieved UserID
            result_l, _ = self.execute_sql(
                self.LOGIN_KEY,
                "INSERT INTO logins (UserID, Username, PasswordHash) VALUES (?, ?, ?)",
                (user_id, username, password_hash)
            )

            if result_l and "SQL executed successfully" in result_l[0]:
                # 4. Initialize user progress and settings
                self.initialize_user_data(user_id)
                return user_id
            else:
                # Rollback/Cleanup: If login insertion fails (e.g., username not unique),
                # delete the user row from the USERS_DATA table to prevent orphaned data.
                print("Login data insertion failed (potential duplicate username). Attempting cleanup of Users row.")
                self.execute_sql(self.USERS_KEY, "DELETE FROM users WHERE UserID = ?", (user_id,))
                return None

        print(f"User data insertion failed. Details: {result_u}")
        return None

    def initialize_user_data(self, user_id: int):
        """Initialize progress data and settings for a new user."""
        # Initialize progress
        self.execute_sql(
            self.PROGRESS_KEY,
            "INSERT INTO user_progress (UserID) VALUES (?)",
            (user_id,)
        )

        # Initialize settings
        self.execute_sql(
            self.PROGRESS_KEY,
            "INSERT INTO user_settings (UserID) VALUES (?)",
            (user_id,)
        )

        # Initialize default quests
        default_quests = [
            ("Complete 3 Lessons", 3),
            ("Practice for 15 minutes", 15),
            ("Learn 10 new words", 10)
        ]

        for quest_name, target in default_quests:
            self.execute_sql(
                self.PROGRESS_KEY,
                "INSERT INTO daily_quests (UserID, QuestName, TargetValue) VALUES (?, ?, ?)",
                (user_id, quest_name, target)
            )

        # Initialize some official test scores
        test_scores = [
            ("2025-05-28", 1480, 700, 780),
            ("2025-07-20", 1560, 760, 800)
        ]

        for test_date, total, ebrw, math in test_scores:
            self.execute_sql(
                self.PROGRESS_KEY,
                "INSERT INTO official_test_scores (UserID, TestDate, TotalScore, EBRWScore, MathScore) VALUES (?, ?, ?, ?, ?)",
                (user_id, test_date, total, ebrw, math)
            )

    # --- User Profile Methods ---
    def update_user_profile(self, user_id: int, first_name: str, last_name: str, nickname: str, birth_date: str,
                            account_type: str):
        """Update user profile information."""
        self.execute_sql(
            self.USERS_KEY,
            "UPDATE users SET FirstName = ?, LastName = ?, Nickname = ?, BirthDate = ?, AccountType = ? WHERE UserID = ?",
            (first_name, last_name, nickname, birth_date, account_type, user_id)
        )

    def get_user_profile(self, user_id: int) -> Optional[dict]:
        """Get complete user profile data."""
        cols, rows = self.execute_sql(
            self.USERS_KEY,
            "SELECT FirstName, LastName, Nickname, BirthDate, AccountType FROM users WHERE UserID = ?",
            (user_id,)
        )
        if rows and rows[0]:
            return {
                'first_name': rows[0][0],
                'last_name': rows[0][1],
                'nickname': rows[0][2],
                'birth_date': rows[0][3],
                'account_type': rows[0][4]
            }
        return None

    # --- Progress and Score Methods ---
    def get_user_progress(self, user_id: int) -> Optional[dict]:
        """Get user progress data including scores and streak."""
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT TotalScore, EBRWScore, MathScore, CurrentStreak, StreakGoal FROM user_progress WHERE UserID = ?",
            (user_id,)
        )
        if rows and rows[0]:
            return {
                'total_score': rows[0][0],
                'ebrw_score': rows[0][1],
                'math_score': rows[0][2],
                'current_streak': rows[0][3],
                'streak_goal': rows[0][4]
            }
        return None

    def update_user_score(self, user_id: int, score_type: str, score: int):
        """Update user scores."""
        if score_type == 'total':
            self.execute_sql(
                self.PROGRESS_KEY,
                "UPDATE user_progress SET TotalScore = ? WHERE UserID = ?",
                (score, user_id)
            )
        elif score_type == 'ebrw':
            self.execute_sql(
                self.PROGRESS_KEY,
                "UPDATE user_progress SET EBRWScore = ? WHERE UserID = ?",
                (score, user_id)
            )
        elif score_type == 'math':
            self.execute_sql(
                self.PROGRESS_KEY,
                "UPDATE user_progress SET MathScore = ? WHERE UserID = ?",
                (score, user_id)
            )

    def update_streak(self, user_id: int, streak: int):
        """Update user streak."""
        self.execute_sql(
            self.PROGRESS_KEY,
            "UPDATE user_progress SET CurrentStreak = ?, LastActiveDate = CURRENT_DATE WHERE UserID = ?",
            (streak, user_id)
        )

    def set_streak_goal(self, user_id: int, goal: int):
        """Set user streak goal."""
        self.execute_sql(
            self.PROGRESS_KEY,
            "UPDATE user_progress SET StreakGoal = ? WHERE UserID = ?",
            (goal, user_id)
        )

    # --- Test Scores Methods ---
    def get_official_test_scores(self, user_id: int) -> List[dict]:
        """Get all official test scores for a user."""
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT TestDate, TotalScore, EBRWScore, MathScore FROM official_test_scores WHERE UserID = ? ORDER BY TestDate DESC",
            (user_id,)
        )
        if rows:
            return [
                {
                    'date': row[0],
                    'total_score': row[1],
                    'ebrw_score': row[2],
                    'math_score': row[3]
                }
                for row in rows
            ]
        return []

    def get_practice_results(self, user_id: int) -> List[dict]:
        """Get all practice results for a user."""
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT PracticeName, PracticeDate, Score, MaxScore, PracticeType FROM practice_results WHERE UserID = ? ORDER BY PracticeDate DESC",
            (user_id,)
        )
        if rows:
            return [
                {
                    'name': row[0],
                    'date': row[1],
                    'score': row[2],
                    'max_score': row[3],
                    'type': row[4]
                }
                for row in rows
            ]
        return []

    # --- Quest Methods ---
    def get_daily_quests(self, user_id: int) -> List[dict]:
        """Get daily quests for a user."""
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT QuestName, TargetValue, CurrentValue, Completed FROM daily_quests WHERE UserID = ? AND QuestDate = CURRENT_DATE",
            (user_id,)
        )
        if rows:
            return [
                {
                    'name': row[0],
                    'target': row[1],
                    'current': row[2],
                    'completed': bool(row[3])
                }
                for row in rows
            ]
        return []

    def update_quest_progress(self, user_id: int, quest_name: str, current_value: int):
        """Update quest progress."""
        completed = False
        # Get target value to check if completed
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT TargetValue FROM daily_quests WHERE UserID = ? AND QuestName = ? AND QuestDate = CURRENT_DATE",
            (user_id, quest_name)
        )
        if rows and current_value >= rows[0][0]:
            completed = True

        self.execute_sql(
            self.PROGRESS_KEY,
            "UPDATE daily_quests SET CurrentValue = ?, Completed = ? WHERE UserID = ? AND QuestName = ? AND QuestDate = CURRENT_DATE",
            (current_value, completed, user_id, quest_name)
        )

    # --- Settings Methods ---
    def get_user_settings(self, user_id: int) -> Optional[dict]:
        """Get user settings."""
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT DarkMode, Sounds, Haptics, Friends, Notifications, Emails, ProductivityMode FROM user_settings WHERE UserID = ?",
            (user_id,)
        )
        if rows and rows[0]:
            return {
                'dark_mode': bool(rows[0][0]),
                'sounds': bool(rows[0][1]),
                'haptics': bool(rows[0][2]),
                'friends': bool(rows[0][3]),
                'notifications': bool(rows[0][4]),
                'emails': bool(rows[0][5]),
                'productivity_mode': bool(rows[0][6])
            }
        return None

    def update_user_settings(self, user_id: int, setting_name: str, value: bool):
        """Update user settings."""
        self.execute_sql(
            self.PROGRESS_KEY,
            f"UPDATE user_settings SET {setting_name} = ? WHERE UserID = ?",
            (value, user_id)
        )

    # --- Vocabulary Progress Methods ---
    def update_vocabulary_progress(self, user_id: int, word: str, is_correct: bool):
        """Update vocabulary progress for a word."""
        # Check if word exists for user
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT VocabID, TimesCorrect, TimesIncorrect FROM vocabulary_progress WHERE UserID = ? AND Word = ?",
            (user_id, word)
        )

        if rows and rows[0]:
            # Update existing word
            vocab_id, times_correct, times_incorrect = rows[0]
            if is_correct:
                times_correct += 1
            else:
                times_incorrect += 1

            mastery_level = min(5, times_correct // 2)  # Simple mastery calculation

            self.execute_sql(
                self.PROGRESS_KEY,
                "UPDATE vocabulary_progress SET TimesCorrect = ?, TimesIncorrect = ?, MasteryLevel = ?, LastPracticed = CURRENT_DATE WHERE VocabID = ?",
                (times_correct, times_incorrect, mastery_level, vocab_id)
            )
        else:
            # Insert new word
            times_correct = 1 if is_correct else 0
            times_incorrect = 0 if is_correct else 1
            mastery_level = 1 if is_correct else 0

            self.execute_sql(
                self.PROGRESS_KEY,
                "INSERT INTO vocabulary_progress (UserID, Word, MasteryLevel, LastPracticed, TimesCorrect, TimesIncorrect) VALUES (?, ?, ?, CURRENT_DATE, ?, ?)",
                (user_id, word, mastery_level, times_correct, times_incorrect)
            )

    def get_vocabulary_stats(self, user_id: int) -> dict:
        """Get vocabulary statistics for user."""
        cols, rows = self.execute_sql(
            self.PROGRESS_KEY,
            "SELECT COUNT(*), AVG(MasteryLevel), SUM(TimesCorrect), SUM(TimesIncorrect) FROM vocabulary_progress WHERE UserID = ?",
            (user_id,)
        )
        if rows and rows[0]:
            total_words, avg_mastery, total_correct, total_incorrect = rows[0]
            return {
                'total_words': total_words or 0,
                'avg_mastery': round(avg_mastery or 0, 1),
                'total_correct': total_correct or 0,
                'total_incorrect': total_incorrect or 0
            }
        return {'total_words': 0, 'avg_mastery': 0, 'total_correct': 0, 'total_incorrect': 0}


users = UsersDB()