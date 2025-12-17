"""
Extract all unique questions from question_bank.txt, ensuring no duplicates.
"""
import os
import re
import sqlite3
from typing import List, Dict, Optional, Set

DB_PATH = os.path.join(os.path.dirname(__file__), 'question_bank.db')
TXT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'question_bank.txt')

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS QUESTIONS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                QuestionID TEXT,
                Domain TEXT,
                Skill TEXT,
                Text TEXT,
                Question TEXT,
                Option1 TEXT,
                Option2 TEXT,
                Option3 TEXT,
                Option4 TEXT,
                Correct TEXT,
                Explanation TEXT,
                Difficulty TEXT
            )
        """)
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_questionid ON QUESTIONS(QuestionID)")
        except Exception:
            pass
        conn.commit()

def parse_question_block(block: str) -> Optional[Dict]:
    """Parse a question block - improved version from manual_parse_questions.py"""
    if not block or len(block.strip()) < 50:
        return None
    
    # Extract Question ID
    qid_match = re.search(r'Question\s+ID\s+([a-f0-9]+)', block, re.IGNORECASE)
    if not qid_match:
        qid_match = re.search(r'ID:\s*([a-f0-9]+)', block, re.IGNORECASE)
    question_id = qid_match.group(1) if qid_match else None
    
    # Skip Math questions
    if 'Math' in block and 'Reading and Writing' not in block:
        domain_match = re.search(r'Domain\s+(.*?)(?:\n|Skill|Difficulty)', block, re.IGNORECASE | re.DOTALL)
        if domain_match:
            domain_text = domain_match.group(1).strip()
            if 'Math' in domain_text and 'Reading' not in domain_text and 'Writing' not in domain_text:
                return None
    
    # Extract Domain
    domain = ''
    domain_match = re.search(r'Domain\s+(.*?)(?:\n|Skill|Difficulty)', block, re.IGNORECASE | re.DOTALL)
    if domain_match:
        domain_lines = [line.strip() for line in domain_match.group(1).strip().split('\n') if line.strip()]
        filtered = [line for line in domain_lines if line not in ['SAT', 'Reading and Writing', 'Test', 'Assessment']]
        if filtered:
            domain = ' '.join(filtered)
    
    # Extract Skill
    skill = ''
    skill_match = re.search(r'Skill\s+(.*?)(?:\n|Difficulty|ID:)', block, re.IGNORECASE | re.DOTALL)
    if skill_match:
        skill_lines = [line.strip() for line in skill_match.group(1).strip().split('\n') if line.strip()]
        filtered = [line for line in skill_lines if line not in ['SAT', 'Reading and Writing', 'Test', 'Assessment']]
        if filtered:
            skill = filtered[-1]
    
    # Extract Difficulty
    difficulty = 'Medium'
    diff_match = re.search(r'Question\s+Difficulty\s*:\s*(\w+)', block, re.IGNORECASE)
    if not diff_match:
        diff_match = re.search(r'Difficulty\s*:\s*(\w+)', block, re.IGNORECASE)
    if diff_match:
        difficulty = diff_match.group(1).strip()
    
    # Extract Correct Answer
    correct_letter = None
    correct_match = re.search(r'Correct\s+Answer\s*:\s*([A-D])', block, re.IGNORECASE)
    if correct_match:
        correct_letter = correct_match.group(1).upper()
    
    # Extract Options
    options = ['', '', '', '']
    opt_match = re.search(r'A\.\s*(.*?)\s+B\.\s*(.*?)\s+C\.\s*(.*?)\s+D\.\s*(.*?)(?:\n|$)', block, re.IGNORECASE | re.DOTALL)
    if opt_match:
        options = [opt.strip() for opt in opt_match.groups()]
    else:
        opt_pattern = r'^\s*A\.\s*(.*?)\s*^\s*B\.\s*(.*?)\s*^\s*C\.\s*(.*?)\s*^\s*D\.\s*(.*?)\s*$'
        opt_match = re.search(opt_pattern, block, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        if opt_match:
            options = [opt.strip() for opt in opt_match.groups()]
    
    # Extract Explanation
    explanation = ''
    rationale_match = re.search(r'Rationale\s+(.*?)(?:\n\s*Choice\s+[A-D]|Question\s+Difficulty|$)', block, re.IGNORECASE | re.DOTALL)
    if rationale_match:
        explanation = rationale_match.group(1).strip()
        explanation = re.sub(r'\s+', ' ', explanation)
        if len(explanation) > 2000:
            explanation = explanation[:2000]
    
    # Extract question text and passage
    text_clean = re.sub(r'^(?:Question\s+ID|ID:)\s*[a-f0-9]+\s*', '', block, flags=re.IGNORECASE | re.MULTILINE)
    text_clean = re.sub(r'ID:.*?Answer.*?Correct\s+Answer.*?Rationale.*?Question\s+Difficulty.*', '', text_clean, flags=re.IGNORECASE | re.DOTALL)
    
    opt_start = None
    for pattern in [r'\bA\.\s+', r'^\s*A\.\s+']:
        match = re.search(pattern, text_clean, re.IGNORECASE | re.MULTILINE)
        if match:
            opt_start = match.start()
            break
    
    if opt_start:
        pre_options = text_clean[:opt_start].strip()
    else:
        pre_options = text_clean.strip()
    
    # Handle Text 1/Text 2 questions
    has_multiple_texts = 'Text 1' in pre_options and 'Text 2' in pre_options
    
    question_markers = [
        r'Based\s+on\s+the\s+texts',
        r'Which\s+choice',
        r'What\s+',
        r'According\s+to',
        r'Based\s+on',
        r'Which\s+statement',
        r'It\s+can\s+most\s+reasonably',
        r'Which\s+quotation',
        r'Which\s+choice\s+best',
        r'How\s+would',
    ]
    
    question_start = None
    for marker in question_markers:
        match = re.search(marker, pre_options, re.IGNORECASE)
        if match:
            question_start = match.start()
            if has_multiple_texts and 'Based on the texts' in pre_options[question_start:question_start+50]:
                question_end = pre_options.find('?', question_start)
                if question_end == -1:
                    question_end = len(pre_options)
                temp_question = pre_options[question_start:question_end+1].strip()
                if len(temp_question) > 20:
                    break
            else:
                break
    
    if question_start:
        passage = pre_options[:question_start].strip()
        question = pre_options[question_start:].strip()
        if has_multiple_texts and 'Based on the texts' not in question:
            based_on_match = re.search(r'Based\s+on\s+the\s+texts.*?\?', pre_options, re.IGNORECASE | re.DOTALL)
            if based_on_match:
                question_start = based_on_match.start()
                passage = pre_options[:question_start].strip()
                question = based_on_match.group(0).strip()
    else:
        if has_multiple_texts:
            based_on_match = re.search(r'Based\s+on\s+the\s+texts.*?\?', pre_options, re.IGNORECASE | re.DOTALL)
            if based_on_match:
                question_start = based_on_match.start()
                passage = pre_options[:question_start].strip()
                question = based_on_match.group(0).strip()
            else:
                last_question = pre_options.rfind('?')
                last_colon = pre_options.rfind(':')
                split_idx = max(last_question, last_colon)
                if split_idx > len(pre_options) * 0.5:
                    passage = pre_options[:split_idx + 1].strip()
                    question = pre_options[split_idx + 1:].strip()
                else:
                    passage = pre_options
                    question = ''
        else:
            last_period = pre_options.rfind('.')
            last_question = pre_options.rfind('?')
            last_colon = pre_options.rfind(':')
            split_idx = max(last_period, last_question, last_colon)
            if split_idx > len(pre_options) * 0.5:
                passage = pre_options[:split_idx + 1].strip()
                question = pre_options[split_idx + 1:].strip()
            else:
                passage = pre_options
                question = ''
    
    if not question_id or not correct_letter or not all(options):
        return None
    
    return {
        'QuestionID': question_id,
        'Domain': domain or 'Reading and Writing',
        'Skill': skill or '',
        'Text': passage,
        'Question': question,
        'Option1': options[0],
        'Option2': options[1],
        'Option3': options[2],
        'Option4': options[3],
        'Correct': correct_letter,
        'Explanation': explanation,
        'Difficulty': difficulty
    }

def extract_question_blocks(text: str) -> List[str]:
    """Extract individual question blocks from the text."""
    blocks = []
    positions = [m.start() for m in re.finditer(r'Question\s+ID\s+[a-f0-9]+', text, re.IGNORECASE)]
    if not positions:
        positions = [m.start() for m in re.finditer(r'ID:\s*[a-f0-9]+', text, re.IGNORECASE)]
    
    if not positions:
        return []
    
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        block = text[pos:end].strip()
        if len(block) > 100:
            blocks.append(block)
    
    return blocks

def main():
    print("Initializing database...")
    init_db()
    
    # Clear existing questions
    with get_conn() as conn:
        conn.execute("DELETE FROM QUESTIONS")
        conn.commit()
    print("Cleared existing questions")
    
    print(f"Reading {TXT_PATH}...")
    try:
        with open(TXT_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    print("Extracting question blocks...")
    blocks = extract_question_blocks(text)
    print(f"Found {len(blocks)} question blocks")
    
    print("Parsing questions (English only, unique only)...")
    parsed_questions = []
    seen_question_ids = set()
    seen_question_texts = set()  # Track by question text to avoid duplicates
    
    for i, block in enumerate(blocks):
        parsed = parse_question_block(block)
        if parsed:
            # Skip Math
            domain_lower = parsed['Domain'].lower()
            if 'math' in domain_lower and 'reading' not in domain_lower and 'writing' not in domain_lower:
                continue
            
            # Check for duplicates by ID
            if parsed['QuestionID'] in seen_question_ids:
                continue
            seen_question_ids.add(parsed['QuestionID'])
            
            # Check for duplicates by question text (normalized)
            question_text_key = parsed['Question'].strip().lower()[:100]  # First 100 chars
            if question_text_key in seen_question_texts:
                continue
            seen_question_texts.add(question_text_key)
            
            parsed_questions.append(parsed)
        
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} blocks, parsed {len(parsed_questions)} unique questions so far...")
    
    print(f"\nParsed {len(parsed_questions)} unique English questions")
    
    if not parsed_questions:
        print("No questions to insert!")
        return
    
    print("Inserting questions into database...")
    with get_conn() as conn:
        upsert_sql = (
            "INSERT INTO QUESTIONS (QuestionID, Domain, Skill, Text, Question, Option1, Option2, Option3, Option4, Correct, Explanation, Difficulty) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(QuestionID) DO UPDATE SET "
            "Domain=excluded.Domain, Skill=excluded.Skill, Text=excluded.Text, Question=excluded.Question, "
            "Option1=excluded.Option1, Option2=excluded.Option2, Option3=excluded.Option3, Option4=excluded.Option4, "
            "Correct=excluded.Correct, Explanation=excluded.Explanation, Difficulty=excluded.Difficulty"
        )
        
        inserted = 0
        for q in parsed_questions:
            try:
                conn.execute(upsert_sql, (
                    q['QuestionID'], q['Domain'], q['Skill'], q['Text'], q['Question'],
                    q['Option1'], q['Option2'], q['Option3'], q['Option4'],
                    q['Correct'], q['Explanation'], q['Difficulty']
                ))
                inserted += 1
            except Exception as e:
                print(f"Error inserting question {q['QuestionID']}: {e}")
        
        conn.commit()
    
    print(f"\nSuccessfully inserted {inserted} unique questions!")
    
    # Count total questions
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM QUESTIONS")
        total = cur.fetchone()[0]
        print(f"Total questions in database: {total}")

if __name__ == '__main__':
    main()

