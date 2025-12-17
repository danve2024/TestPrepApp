import sqlite3
import os

def apply_migration():
    # Path to the progress database
    db_path = os.path.join(os.path.dirname(__file__), 'progress_data.db')
    
    # Read the migration SQL
    with open('migrations/002_add_ebrw_math_to_practice_results.sql', 'r') as f:
        migration_sql = f.read()
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute the migration
        cursor.executescript(migration_sql)
        conn.commit()
        
        print("Migration completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(practice_results);")
        columns = cursor.fetchall()
        print("\nUpdated table columns:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
    except sqlite3.Error as e:
        print(f"Error running migration: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    apply_migration()
