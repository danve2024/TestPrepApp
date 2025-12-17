import sqlite3
import os
from typing import List, Dict, Any

def duplicate_questions():
    """Duplicate all questions in the database with new unique QuestionIDs."""
    db_path = os.path.join(os.path.dirname(__file__), 'question_bank.db')
    
    if not os.path.exists(db_path):
        print("Error: question_bank.db not found.")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # First, clean up any existing duplicates (those with '_dup' or 'd' at the end)
        cursor.execute("DELETE FROM QUESTIONS WHERE QuestionID LIKE '%_dup' OR QuestionID LIKE '%_dupd'")
        
        # Get all original questions (those without 'd' at the end of QuestionID)
        cursor.execute("""
            SELECT * FROM QUESTIONS 
            WHERE (QuestionID NOT LIKE '%d' OR QuestionID IS NULL)
            AND (QuestionID NOT LIKE '%_dup')
        """)
        questions = cursor.fetchall()
        
        if not questions:
            print("No original questions found in the database.")
            return
        
        print(f"Found {len(questions)} original questions. Creating clean duplicates with 'd' suffix...")
        
        # For each question, create a duplicate with a new QuestionID
        for question in questions:
            # Create a copy of the question with a new ID
            new_question = dict(question)
            original_id = new_question['QuestionID'] or f"dbid:{new_question['id']}"
            new_question['QuestionID'] = f"{original_id}d"
            
            # Check if a duplicate with this ID already exists
            cursor.execute("SELECT 1 FROM QUESTIONS WHERE QuestionID = ?", (new_question['QuestionID'],))
            if not cursor.fetchone():
                # Insert the duplicate only if it doesn't exist
                cursor.execute("""
                    INSERT INTO QUESTIONS 
                    (QuestionID, Domain, Skill, Text, Question, 
                     Option1, Option2, Option3, Option4, 
                     Correct, Explanation, Difficulty)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_question['QuestionID'],
                    new_question['Domain'],
                    new_question['Skill'],
                    new_question['Text'],
                    new_question['Question'],
                    new_question['Option1'],
                    new_question['Option2'],
                    new_question['Option3'],
                    new_question['Option4'],
                    new_question['Correct'],
                    new_question['Explanation'],
                    new_question['Difficulty']
                ))
        
        # Commit the changes
        conn.commit()
        
        # Get the final count
        cursor.execute("SELECT COUNT(*) as count FROM QUESTIONS")
        total = cursor.fetchone()['count']
        print(f"Successfully processed {len(questions)} questions. Total questions now: {total}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    duplicate_questions()
