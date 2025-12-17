import os
import re
import sqlite3
import random
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), 'question_bank.db')
PDF_PATH_DEFAULT = os.path.join(os.path.dirname(__file__), 'question_bank.pdf')
TXT_PATH_DEFAULT = os.path.join(os.path.dirname(__file__), 'static', 'question_bank.txt')

SCHEMA_QUESTIONS = """
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
);
"""

SCHEMA_THEORY = """
CREATE TABLE IF NOT EXISTS theory_texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT,
    difficulty_level TEXT,
    section_order INTEGER,
    text_type TEXT,
    content TEXT
);
"""


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA_QUESTIONS)
        conn.execute(SCHEMA_THEORY)
        # Lightweight migration: ensure QuestionID column and unique index exist
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(QUESTIONS)")
        cols = {row[1] for row in cur.fetchall()}
        if 'QuestionID' not in cols:
            conn.execute("ALTER TABLE QUESTIONS ADD COLUMN QuestionID TEXT")
        # Create a unique index for QuestionID if not present (ignores error if exists)
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_questionid ON QUESTIONS(QuestionID)")
        except Exception:
            pass
        conn.commit()


def _row_to_mcq(row: sqlite3.Row) -> Dict:
    # Map DB row into the lesson question dict shape
    options = [row['Option1'], row['Option2'], row['Option3'], row['Option4']]
    correct_text = None
    # Correct may be a letter A/B/C/D or the full text
    if row['Correct'] and row['Correct'].strip().upper() in ['A', 'B', 'C', 'D']:
        idx = ord(row['Correct'].strip().upper()) - ord('A')
        if 0 <= idx < 4:
            correct_text = options[idx]
    else:
        correct_text = row['Correct']
    # Prefer provided QuestionID; fallback to internal row id
    qid = row['QuestionID'] if row['QuestionID'] else f"dbid:{row['id']}"
    return {
        'type': 'multiple_choice',
        'question_id': qid,
        'db_id': row['id'],
        'domain': row['Domain'],
        'skill': row['Skill'],
        'text': row['Text'],
        'question': row['Question'],
        'options': options,
        'answer': correct_text,
        'explanation': row['Explanation'],
        'difficulty': row['Difficulty'],
    }


def get_random_questions(limit: Optional[int] = None) -> List[Dict]:
    init_db()
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if limit is None:
            cur.execute("SELECT * FROM QUESTIONS ORDER BY RANDOM()")
        else:
            # Get half the limit to ensure we have enough unique questions
            half_limit = max(1, limit // 2)
            cur.execute("SELECT * FROM QUESTIONS ORDER BY RANDOM() LIMIT ?", (half_limit,))
        rows = cur.fetchall()
    
    # Convert to question dicts
    questions = [_row_to_mcq(r) for r in rows]
    
    # If limit was specified and we need to return more questions than we have unique ones,
    # duplicate the questions to reach the desired count
    if limit is not None and len(questions) * 2 <= limit:
        questions = questions * 2  # Duplicate all questions
        random.shuffle(questions)  # Shuffle so duplicates aren't adjacent
    
    return questions


def get_questions_by_ids(ids: List[str]) -> List[Dict]:
    if not ids:
        return []
    init_db()
    # Separate synthetic dbids (prefix 'dbid:') from normal QuestionIDs
    qid_list: List[str] = []
    dbid_list: List[int] = []
    for i in ids:
        if isinstance(i, str) and i.startswith('dbid:'):
            try:
                dbid_list.append(int(i.split(':', 1)[1]))
            except Exception:
                pass
        else:
            qid_list.append(i)
    by_key: Dict[str, Dict] = {}
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if qid_list:
            placeholders = ",".join(["?"] * len(qid_list))
            cur.execute(f"SELECT * FROM QUESTIONS WHERE QuestionID IN ({placeholders})", tuple(qid_list))
            rows = cur.fetchall()
            for r in rows:
                mcq = _row_to_mcq(r)
                by_key[mcq['question_id']] = mcq
        if dbid_list:
            placeholders = ",".join(["?"] * len(dbid_list))
            cur.execute(f"SELECT * FROM QUESTIONS WHERE id IN ({placeholders})", tuple(dbid_list))
            rows2 = cur.fetchall()
            for r in rows2:
                mcq = _row_to_mcq(r)
                by_key[mcq['question_id']] = mcq
    # Reconstruct list preserving input order
    return [by_key[i] for i in ids if i in by_key]


def count_questions() -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM QUESTIONS")
        (cnt,) = cur.fetchone()
        return int(cnt or 0)


def get_questions_filtered(
    difficulty: Optional[str] = None,
    domain: Optional[str] = None,
    skill: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict]:
    """Return questions filtered by difficulty, domain, and skill.

    This is used by SAT lesson lane to ensure that each skill block only
    pulls questions that match the currently selected difficulty tier,
    domain, and skill.
    """
    init_db()
    clauses = []
    params: List[str] = []

    if difficulty:
        clauses.append("Difficulty = ?")
        params.append(difficulty)
    if domain:
        clauses.append("Domain = ?")
        params.append(domain)
    if skill:
        clauses.append("Skill = ?")
        params.append(skill)

    where_sql = ""
    if clauses:
        where_sql = " WHERE " + " AND ".join(clauses)

    sql = "SELECT * FROM QUESTIONS" + where_sql + " ORDER BY RANDOM()"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

    return [_row_to_mcq(r) for r in rows]


def get_theory_sections(skill_id: str, difficulty_level: str) -> List[Dict]:
    init_db()
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT section_order, text_type, content FROM theory_texts "
            "WHERE skill_id=? AND difficulty_level=? ORDER BY section_order",
            (skill_id, difficulty_level),
        )
        rows = cur.fetchall()
    return [dict(section_order=row['section_order'], text_type=row['text_type'], content=row['content']) for row in rows]


# ---------------- PDF Parsing ----------------
# Very lightweight parser tailored to the provided example layout.
# If the PDF has variations, you may need to expand these regexes.

BLOCK_SPLIT_RE = re.compile(r"\bID:\s*([\w-]+)\b", re.IGNORECASE)
QBLOCK_SPLIT_RE = re.compile(r"\bQuestion\s*ID\s*([\w-]+)\b", re.IGNORECASE)
# Accept multiple variants like "Correct Answer:", "Correct answer:", "Answer\nCorrect Answer:"
CORRECT_RE = re.compile(r"(?:Correct\s*Answer|Correct\s*answer)\s*:\s*([A-D])\b", re.IGNORECASE)
DIFF_RE = re.compile(r"\bQuestion\s*Difficulty\s*:\s*(\w+)", re.IGNORECASE)
DIFF_ALT_RE = re.compile(r"\bDifficulty\s*:?\s*(\w+)", re.IGNORECASE)
ANSWER_SECTION_RE = re.compile(r"\bAnswer\b.*?Correct\s*Answer\s*:\s*[A-D].*?Rationale", re.IGNORECASE | re.DOTALL)
RATIONALE_RE = re.compile(r"Rationale\s*(.*)$", re.IGNORECASE | re.DOTALL)
QID_LINE_RE = re.compile(r"Question\s*ID\s*([\w-]+)", re.IGNORECASE)

# Domain/Skill extraction: capture text between markers even if split across lines
# Example header section contains tokens like 'Domain', 'Skill', with values possibly spanning multiple lines
DOMAIN_SECTION_RE = re.compile(r"\bDomain\b\s*(.*?)\bSkill\b", re.IGNORECASE | re.DOTALL)
SKILL_SECTION_RE = re.compile(r"\bSkill\b\s*(.*?)(?:\bDifficulty\b|\bID:\b)", re.IGNORECASE | re.DOTALL)

# Options patterns
# Single-run-on-line pattern: "A. ... B. ... C. ... D. ..."
OPTIONS_RE = re.compile(r"\bA\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)(?:\n|$)", re.IGNORECASE | re.DOTALL)
# Multi-line pattern where each option is on its own line
OPTIONS_LINES_RE = re.compile(r"^\s*A\.\s*(.*?)\s*$\s*^\s*B\.\s*(.*?)\s*$\s*^\s*C\.\s*(.*?)\s*$\s*^\s*D\.\s*(.*?)\s*$", re.IGNORECASE | re.DOTALL | re.MULTILINE)

# Leading ID marker remover and question stem detector
LEADING_ID_RE = re.compile(r"^(?:Question\s*ID|ID:)\s*[\w-]+\s*", re.IGNORECASE)
QUESTION_STEM_RE = re.compile(
    r"(Which|What|In the context|According to|The author|The passage|As used in the passage|The main purpose|The primary purpose|The central claim|The best evidence|Which choice)\b.*$",
    re.IGNORECASE | re.DOTALL,
)


def _extract_blocks(text: str) -> List[str]:
    # Prefer splitting on 'Question ID ...' so we retain the header (Domain/Skill) with the question block.
    positions = [m.start() for m in QBLOCK_SPLIT_RE.finditer(text)]
    if not positions:
        # Fallback: split on bare 'ID: ...' occurrences
        positions = [m.start() for m in BLOCK_SPLIT_RE.finditer(text)]
    if not positions:
        return []
    blocks = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        blocks.append(text[pos:end].strip())
    return blocks


def _parse_block(block: str) -> Optional[Dict]:
    # Extract difficulty
    diff_match = DIFF_RE.search(block) or DIFF_ALT_RE.search(block)
    difficulty = diff_match.group(1).strip() if diff_match else ''

    # Extract domain and skill from the header region between 'Domain' and 'Difficulty'.
    # The export places values for Domain (may span multiple lines, e.g., 'Information and' + 'Ideas')
    # and then the Skill value as the last line before 'Difficulty'. Interleaved meta like 'SAT' and 'Reading and Writing'
    # should be ignored.
    domain = ''
    skill = ''
    dom_lab = re.search(r"\bDomain\b", block, re.IGNORECASE)
    diff_lab = re.search(r"\b(Question\s*Difficulty|Difficulty)\b", block, re.IGNORECASE)
    if dom_lab and diff_lab and diff_lab.start() > dom_lab.end():
        header_seg = block[dom_lab.end():diff_lab.start()]
        seg_lines = [ln.strip() for ln in header_seg.splitlines()]
        seg_lines = [ln for ln in seg_lines if ln]
        # Remove known meta tokens that commonly appear in this segment
        ignore_set = {"SAT", "Reading and Writing", "Test", "Assessment"}
        filtered = [ln for ln in seg_lines if ln not in ignore_set]
        if filtered:
            # Last line is Skill, preceding lines are Domain (can be 1 or 2 lines like 'Information and' + 'Ideas')
            skill = filtered[-1]
            dom_lines = filtered[:-1]
            if dom_lines:
                domain = "\n".join(dom_lines)

    # Split pre-answer and answer rationale
    ans_section = ANSWER_SECTION_RE.search(block)
    pre_ans_text = block
    if ans_section:
        pre_ans_text = block[:ans_section.start()]

    # Find options
    opt_match = OPTIONS_RE.search(pre_ans_text)
    if not opt_match:
        opt_match = OPTIONS_LINES_RE.search(pre_ans_text)
    if not opt_match:
        return None
    optA, optB, optC, optD = [opt.strip() for opt in opt_match.groups()]

    # Text up to the options is the passage+question stem container
    pre_options_raw = pre_ans_text[:opt_match.start()]
    # Start passage after the last ID marker in the block to avoid header bleed-through
    last_id_end = None
    for m in re.finditer(r"(?:^|\n)\s*(?:Question\s*ID|ID:)\s*[\w-]+\s*", pre_options_raw, re.IGNORECASE):
        last_id_end = m.end()
    if last_id_end is not None:
        pre_options = pre_options_raw[last_id_end:].strip()
    else:
        pre_options = pre_options_raw.strip()
        # Remove any leading ID markers like 'ID: <id>' or 'Question ID <id>' as a fallback
        pre_options = LEADING_ID_RE.sub('', pre_options, count=1).strip()

    # Heuristic: The last sentence before options is the actual question; the preceding text is passage/context
    # First try to detect a question stem, even if '?' is missing
    qs_matches = list(QUESTION_STEM_RE.finditer(pre_options))
    if qs_matches:
        s = qs_matches[-1].start()
        passage = pre_options[:s].strip()
        question = pre_options[s:].strip()
    else:
        # Fallback: split by last punctuation
        split_idx = max(pre_options.rfind('?'), pre_options.rfind(':'), pre_options.rfind('.'))
        if split_idx != -1:
            passage = pre_options[:split_idx].strip()
            question = pre_options[split_idx + 1:].strip()
        else:
            passage = pre_options
            question = ''

    # Correct answer letter
    corr_match = CORRECT_RE.search(block)
    correct_letter = corr_match.group(1).upper() if corr_match else ''

    # Rationale / explanation
    rationale_match = RATIONALE_RE.search(block)
    explanation = rationale_match.group(1).strip() if rationale_match else ''

    # QuestionID (try explicit 'Question ID ...' first, else fallback to first ID: ... marker)
    qid_match = QID_LINE_RE.search(block)
    if qid_match:
        question_id = qid_match.group(1).strip()
    else:
        id_match = BLOCK_SPLIT_RE.search(block)
        question_id = id_match.group(1).strip() if id_match else ''

    # Fill DB row
    return {
        'QuestionID': question_id,
        'Domain': domain or 'Reading',
        'Skill': skill or '',
        'Text': passage,
        'Question': question,
        'Option1': optA,
        'Option2': optB,
        'Option3': optC,
        'Option4': optD,
        'Correct': correct_letter,
        'Explanation': explanation,
        'Difficulty': difficulty,
    }


def parse_pdf_to_text(pdf_path: str) -> str:
    # Try PyPDF2 first; then fallback to pdfminer.six; finally naive bytes decode
    text = ''
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        pieces = []
        for page in reader.pages:
            pieces.append(page.extract_text() or '')
        text = "\n".join(pieces)
    except Exception:
        text = ''

    if text and text.strip():
        return text

    # Fallback: pdfminer.six
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        text = extract_text(pdf_path) or ''
    except Exception:
        text = ''

    if text and text.strip():
        return text

    # Last resort: naive bytes decode (often ineffective for PDFs)
    try:
        with open(pdf_path, 'rb') as f:
            data = f.read()
        return data.decode(errors='ignore')
    except Exception:
        return ''


def populate_from_pdf(pdf_path: Optional[str] = None) -> int:
    pdf_path = pdf_path or PDF_PATH_DEFAULT
    if not os.path.isfile(pdf_path):
        return 0

    init_db()
    text = parse_pdf_to_text(pdf_path)
    if not text:
        return 0

    blocks = _extract_blocks(text)
    parsed = []
    for blk in blocks:
        row = _parse_block(blk)
        if row:
            parsed.append(row)

    if not parsed:
        return 0

    with get_conn() as conn:
        upsert_sql = (
            "INSERT INTO QUESTIONS (QuestionID, Domain, Skill, Text, Question, Option1, Option2, Option3, Option4, Correct, Explanation, Difficulty) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(QuestionID) DO UPDATE SET "
            "Domain=excluded.Domain, Skill=excluded.Skill, Text=excluded.Text, Question=excluded.Question, "
            "Option1=excluded.Option1, Option2=excluded.Option2, Option3=excluded.Option3, Option4=excluded.Option4, "
            "Correct=excluded.Correct, Explanation=excluded.Explanation, Difficulty=excluded.Difficulty"
        )
        for r in parsed:
            conn.execute(upsert_sql, (
                r.get('QuestionID', None), r['Domain'], r['Skill'], r['Text'], r['Question'], r['Option1'], r['Option2'], r['Option3'], r['Option4'], r['Correct'], r['Explanation'], r['Difficulty']
            ))
        conn.commit()
    return len(parsed)


def populate_from_txt(txt_path: Optional[str] = None) -> int:
    """Parse a large exported text file of questions and populate the DB.
    Expected format matches the examples in static/question_bank.txt (with 'Question ID', 'ID:', options A-D, 'Correct Answer', 'Rationale', and 'Question Difficulty').
    """
    txt_path = txt_path or TXT_PATH_DEFAULT
    if not os.path.isfile(txt_path):
        return 0

    init_db()
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception:
        return 0

    if not text:
        return 0

    blocks = _extract_blocks(text)
    parsed = []
    for blk in blocks:
        row = _parse_block(blk)
        if row:
            parsed.append(row)

    if not parsed:
        return 0

    with get_conn() as conn:
        upsert_sql = (
            "INSERT INTO QUESTIONS (QuestionID, Domain, Skill, Text, Question, Option1, Option2, Option3, Option4, Correct, Explanation, Difficulty) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(QuestionID) DO UPDATE SET "
            "Domain=excluded.Domain, Skill=excluded.Skill, Text=excluded.Text, Question=excluded.Question, "
            "Option1=excluded.Option1, Option2=excluded.Option2, Option3=excluded.Option3, Option4=excluded.Option4, "
            "Correct=excluded.Correct, Explanation=excluded.Explanation, Difficulty=excluded.Difficulty"
        )
        for r in parsed:
            conn.execute(upsert_sql, (
                r.get('QuestionID', None), r['Domain'], r['Skill'], r['Text'], r['Question'], r['Option1'], r['Option2'], r['Option3'], r['Option4'], r['Correct'], r['Explanation'], r['Difficulty']
            ))
        conn.commit()
    return len(parsed)


def ensure_ready(pdf_path: Optional[str] = None, txt_path: Optional[str] = None) -> int:
    """Ensure DB exists and has rows. If empty, try to populate from TXT first, then fallback to PDF. Returns count after ensure."""
    init_db()
    cnt = count_questions()
    if cnt == 0:
        # Try TXT
        try:
            populate_from_txt(txt_path)
        except Exception:
            pass
        cnt = count_questions()
    if cnt == 0:
        # Fallback to PDF
        try:
            populate_from_pdf(pdf_path)
        except Exception:
            pass
        cnt = count_questions()
    return cnt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Populate question_bank.db from question_bank.pdf')
    parser.add_argument('--pdf', type=str, default=None, help='Path to question_bank.pdf (defaults to project root)')
    parser.add_argument('--rebuild', action='store_true', help='Drop and rebuild the QUESTIONS table before populating')
    parser.add_argument('--limit', type=int, default=None, help='Stop after inserting N parsed questions (debug)')
    args = parser.parse_args()

    init_db()
    if args.rebuild:
        with get_conn() as conn:
            conn.execute('DROP TABLE IF EXISTS QUESTIONS')
        init_db()

    inserted = populate_from_pdf(args.pdf)
    total = count_questions()
    if args.limit is not None and inserted > args.limit:
        inserted = args.limit
    print(f'Inserted: {inserted} | Total in DB: {total}')
