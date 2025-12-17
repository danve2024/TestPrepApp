import sqlite3
import os

def run_migration():
    # Path to the progress database
    db_path = os.path.join(os.path.dirname(__file__), 'progress_data.db')
    
    # Read the migration SQL
    with open('migrations/001_add_ebrw_math_to_practice_results.sql', 'r') as f:
        migration_sql = f.read()
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute the migration
        cursor.executescript(migration_sql)
        conn.commit()
        
        print("Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Error running migration: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
