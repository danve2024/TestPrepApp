"""
Duplicate English questions to reach 3000 total English questions in the database.
"""
import sqlite3
import random
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'question_bank.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def main():
    with get_conn() as conn:
        # Count current English questions
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM QUESTIONS 
            WHERE Domain LIKE '%Reading%' OR Domain LIKE '%Writing%' 
            OR (Domain NOT LIKE '%Math%' AND Domain IS NOT NULL AND Domain != '')
        """)
        current_count = cur.fetchone()[0]
        
        print(f"Current English questions: {current_count}")
        
        if current_count >= 3000:
            print(f"Already have {current_count} questions, which is >= 3000. Done!")
            return
        
        needed = 3000 - current_count
        print(f"Need {needed} more questions")
        
        # Get all English questions
        cur.execute("""
            SELECT QuestionID, Domain, Skill, Text, Question, Option1, Option2, Option3, Option4, Correct, Explanation, Difficulty
            FROM QUESTIONS 
            WHERE Domain LIKE '%Reading%' OR Domain LIKE '%Writing%' 
            OR (Domain NOT LIKE '%Math%' AND Domain IS NOT NULL AND Domain != '')
            ORDER BY RANDOM()
        """)
        all_questions = cur.fetchall()
        
        if not all_questions:
            print("No English questions found to duplicate!")
            return
        
        print(f"Found {len(all_questions)} English questions to duplicate from")
        
        # Duplicate questions with new IDs
        inserted = 0
        upsert_sql = """
            INSERT INTO QUESTIONS (QuestionID, Domain, Skill, Text, Question, Option1, Option2, Option3, Option4, Correct, Explanation, Difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(QuestionID) DO UPDATE SET
            Domain=excluded.Domain, Skill=excluded.Skill, Text=excluded.Text, Question=excluded.Question,
            Option1=excluded.Option1, Option2=excluded.Option2, Option3=excluded.Option3, Option4=excluded.Option4,
            Correct=excluded.Correct, Explanation=excluded.Explanation, Difficulty=excluded.Difficulty
        """
        
        # Create unique IDs by appending a suffix
        import hashlib
        for _ in range(needed):
            # Pick a random question
            q = random.choice(all_questions)
            qid, domain, skill, text, question, opt1, opt2, opt3, opt4, correct, explanation, difficulty = q
            
            # Create new unique ID
            new_id = f"{qid}_dup_{random.randint(10000, 99999)}"
            
            # Check if this ID already exists
            cur.execute("SELECT COUNT(*) FROM QUESTIONS WHERE QuestionID = ?", (new_id,))
            if cur.fetchone()[0] > 0:
                continue  # Skip if already exists
            
            try:
                cur.execute(upsert_sql, (
                    new_id, domain, skill, text, question, opt1, opt2, opt3, opt4, correct, explanation, difficulty
                ))
                inserted += 1
                
                if inserted % 100 == 0:
                    print(f"Inserted {inserted} duplicate questions...")
                    conn.commit()
            except Exception as e:
                print(f"Error inserting duplicate: {e}")
        
        conn.commit()
        print(f"\nInserted {inserted} duplicate questions")
        
        # Final count
        cur.execute("""
            SELECT COUNT(*) FROM QUESTIONS 
            WHERE Domain LIKE '%Reading%' OR Domain LIKE '%Writing%' 
            OR (Domain NOT LIKE '%Math%' AND Domain IS NOT NULL AND Domain != '')
        """)
        final_count = cur.fetchone()[0]
        print(f"Final count: {final_count} English questions")

if __name__ == '__main__':
    main()

