import sqlite3
import os

def check_practice_results():
    db_path = os.path.join(os.path.dirname(__file__), 'progress_data.db')
    
    if not os.path.exists(db_path):
        print("Database file not found at:", db_path)
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practice_results';")
        if not cursor.fetchone():
            print("The 'practice_results' table does not exist in the database.")
            return
        
        # Get column information
        cursor.execute("PRAGMA table_info(practice_results);")
        columns = cursor.fetchall()
        print("\nTable columns:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        # Get all practice results
        cursor.execute("SELECT * FROM practice_results;")
        results = cursor.fetchall()
        
        if not results:
            print("\nNo practice results found in the database.")
        else:
            print("\nPractice Results:")
            for row in results:
                print(row)
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_practice_results()
