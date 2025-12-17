 
from flask import Flask, render_template, redirect, request, flash, url_for, session, jsonify, make_response
import json
import random
import math
from datetime import datetime, timedelta
from data import users
from email_verify_pg import EmailVerifyServicePG
from streaks_pg import StreakServicePG
from authentication import *
from werkzeug.security import check_password_hash
from datetime import datetime, date, timedelta
import question_bank as qb
import os
import hmac
import hashlib as _hashlib
import imaplib
import email as _email
from typing import List

app = Flask(__name__)
app.secret_key = 'LI$cb3ds!gwgy2027'

# Add template filters for debug
@app.template_filter('type')
def get_type(value):
    return type(value).__name__

@app.template_filter('tojson')
def to_json(value):
    try:
        return json.dumps(value, indent=2, default=str)
    except:
        return str(value)

# Initialize PostgreSQL streak service (Phase 1)
try:
    streaks = StreakServicePG()
    streaks.init_schema()
except Exception as e:
    streaks = None
    print(f"[streaks] PostgreSQL not initialized: {e}")

# Initialize PostgreSQL email verification service
try:
    email_verifier = EmailVerifyServicePG()
    email_verifier.init_schema()
except Exception as e:
    email_verifier = None
    print(f"[email] PostgreSQL not initialized for email verification: {e}")

# SMTP helper
import smtplib, ssl, os
from email.message import EmailMessage
from app.routes.settings import create_settings_blueprint
from app.context_processors import inject_settings_factory
from app.data.questions import LESSON1_QUESTIONS, VOCABULARY_QUESTIONS
try:
    from app.services.email_service import send_email_plain as send_email_plain_service
except Exception:
    send_email_plain_service = None

def send_email_plain(to_email: str, subject: str, body: str) -> bool:
    if send_email_plain_service:
        return send_email_plain_service(to_email, subject, body)
    # Fallback to local simple SMTP if the service is unavailable
    try:
        with smtplib.SMTP('localhost', 1025, timeout=5) as s:
            from_addr = os.getenv('MAIL_FROM', 'no-reply@example.com')
            msg = f"From: {from_addr}\nTo: {to_email}\nSubject: {subject}\n\n{body}"
            s.sendmail(from_addr, [to_email], msg)
            return True
    except Exception as e:
        print(f"[email] fallback send failed: {e}")
        return False

def calculate_ebrw_score(user_id):
    """Calculate EBRW score based on question history.
    - Initial score: 800 (English)
    - Each hard question wrong: -10 points (English only)
    - Each easy/medium question wrong: -20 points (English only)
    - Only counts last 54 English questions
    """
    try:
        # Get last 54 English questions from lesson_history
        # English questions are identified by Domain containing "Reading" or "Writing" or not being Math
        # Note: Column name is UserID (uppercase) not user_id
        results = users.execute_sql(
            users.PROGRESS_KEY,
            """
            SELECT Difficulty, IsCorrect, Domain
            FROM lesson_history
            WHERE UserID = ? 
            AND (
                Domain LIKE '%Reading%' OR Domain LIKE '%Writing%' 
                OR (Domain IS NULL OR Domain = '' OR Domain NOT LIKE '%Math%')
            )
            ORDER BY Timestamp DESC
            LIMIT 54
            """,
            (user_id,)
        )
        
        easy_wrong = 0
        medium_wrong = 0
        hard_wrong = 0
        
        if results and results[1]:
            for row in results[1]:
                if len(row) >= 3:
                    difficulty = (row[0] or 'medium').lower().strip()
                    is_correct = row[1]
                    domain = (row[2] or '').lower()
                    
                    # Skip Math questions
                    if 'math' in domain and 'reading' not in domain and 'writing' not in domain:
                        continue
                    
                    # Only count wrong answers
                    if is_correct == 0 or is_correct == False:
                        if difficulty == 'easy':
                            easy_wrong += 1
                        elif difficulty == 'hard':
                            hard_wrong += 1
                        else:  # medium or unknown
                            medium_wrong += 1
        
        # Calculate deductions
        # Hard: -10 points, Easy/Medium: -20 points
        deductions = (hard_wrong * 10) + ((easy_wrong + medium_wrong) * 20)
        
        # Start from 800 (English score), max 800, min 200
        ebrw_score = max(200, min(800, 800 - deductions))
        
        # Total score is EBRW + Math (default Math is 800)
        total_score = ebrw_score + 800
        
        print(f"[DEBUG] calculate_ebrw_score: easy_wrong={easy_wrong}, medium_wrong={medium_wrong}, hard_wrong={hard_wrong}, deductions={deductions}, ebrw_score={ebrw_score}")
        
        return {
            'score': ebrw_score,
            'easy_wrong': easy_wrong,
            'medium_wrong': medium_wrong,
            'hard_wrong': hard_wrong,
            'max_score': 800,
            'total_questions': 54,
            'questions_remaining': max(0, 54 - (easy_wrong + medium_wrong + hard_wrong))
        }
    except Exception as e:
        print(f"[ERROR] Error calculating EBRW score: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return default score on error
        return {
            'score': 800,
            'easy_wrong': 0,
            'medium_wrong': 0,
            'hard_wrong': 0,
            'max_score': 800,
            'total_questions': 54,
            'questions_remaining': 54
    }

# --- Helpers for lessons ---
def _stable_shuffled_options(question: dict) -> list:
    """Return a deterministically shuffled copy of options based on question_id.
    This avoids storing large shuffle maps in the session and keeps order stable between GET and POST.
    """
    opts = (question.get('options') or [])[:]
    qid = question.get('question_id') or ''
    try:
        seed_bytes = _hashlib.md5(qid.encode('utf-8', errors='ignore')).digest()[:8]
        seed = int.from_bytes(seed_bytes, 'big', signed=False)
    except Exception:
        seed = 0
    rnd = random.Random(seed)
    rnd.shuffle(opts)
    return opts

# Provide settings to all templates and enable server-rendered theme/no-flash via factory
app.context_processor(inject_settings_factory(users, is_logged_in, calculate_ebrw_score))

# ---------- Initial EBRW Diagnostic (placed after app init) ----------
@app.route('/initial/ebrw/start')
def initial_ebrw_start():
    if not is_logged_in(session):
        return redirect('/login')
    user_id = session['user_id']
    # If user already has official scores, skip diagnostic
    try:
        official_scores = users.get_official_test_scores(user_id)
        if official_scores and len(official_scores) > 0:
            return redirect(url_for('welcome'))
    except Exception as e:
        print(f"[initial_ebrw_start] Error checking official scores: {e}")
    # Redirect to the actual diagnostic test
    return redirect(url_for('initial_ebrw'))


@app.route('/initial/ebrw')
def initial_ebrw():
    if not is_logged_in(session):
        return redirect('/login')
    user_id = session['user_id']
    # Skip if official exists
    if users.get_official_test_scores(user_id):
        return redirect(url_for('welcome'))

    # Build an EBRW-only set. Aim for ~54 questions
    qb.ensure_ready()
    all_qs = qb.get_random_questions(limit=200)
    ebrw_qs = [q for q in all_qs if 'math' not in (q.get('domain','') + ' ' + q.get('skill','')).lower()]
    questions = ebrw_qs[:54] if len(ebrw_qs) >= 54 else ebrw_qs
    # Persist order in session
    session['initial_ebrw_qids'] = [q['question_id'] for q in questions]
    return render_template('initial_ebrw_start.html', questions=questions)


@app.route('/initial/ebrw/submit', methods=['POST'])
def initial_ebrw_submit():
    if not is_logged_in(session):
        return redirect('/login')
    user_id = session['user_id']
    if users.get_official_test_scores(user_id):
        return redirect(url_for('welcome'))

    qids = session.get('initial_ebrw_qids') or []
    if not qids:
        return redirect(url_for('initial_ebrw'))
    # Re-fetch to grade
    qs = qb.get_questions_by_ids(qids)
    total = len(qs)
    correct = 0
    for idx, q in enumerate(qs):
        chosen = request.form.get(f'q_{idx}')  # option index 0..3
        try:
            chosen_idx = int(chosen) if chosen is not None else -1
        except Exception:
            chosen_idx = -1
        options = q.get('options', [])
        correct_text = q.get('answer')
        chosen_text = options[chosen_idx] if 0 <= chosen_idx < len(options) else None
        if correct_text and chosen_text and correct_text.strip() == chosen_text.strip():
            correct += 1

    # Linear scale to 200-800 for EBRW; total 400-1600 (EBRW + Math)
    ebrw_scaled = 200 + round((max(0, correct) / max(1, total)) * 600)
    ebrw_scaled = max(200, min(800, ebrw_scaled))
    math_score = 800  # Default math score
    total_scaled = ebrw_scaled + math_score  # Total = EBRW + Math

    # Save to practice_results as diagnostic
    try:
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            CREATE TABLE IF NOT EXISTS practice_results (
                PracticeID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER NOT NULL,
                PracticeName TEXT,
                PracticeDate TEXT,
                Score INTEGER,
                EBRWScore INTEGER,
                MathScore INTEGER,
                MaxScore INTEGER,
                PracticeType TEXT,
                FOREIGN KEY (UserID) REFERENCES users(UserID)
            )
            """
        )
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            INSERT INTO practice_results (UserID, PracticeName, PracticeDate, Score, EBRWScore, MathScore, MaxScore, PracticeType)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, 'Initial EBRW Diagnostic', date.today().isoformat(), total_scaled, ebrw_scaled, math_score, 1600, 'diagnostic')
        )
    except Exception:
        pass

    # Seed initial estimated score (will be refined by lessons)
    try:
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            INSERT INTO user_progress (UserID, EBRWScore, MathScore, TotalScore)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(UserID) DO UPDATE SET
                EBRWScore=excluded.EBRWScore,
                MathScore=excluded.MathScore,
                TotalScore=excluded.TotalScore
            """,
            (user_id, ebrw_scaled, math_score, total_scaled)  # Math score is 800, total = EBRW + Math
        )
        
        # Update session with new scores
        session['total_score'] = total_scaled
        session['ebrw_score'] = ebrw_scaled
        session['math_score'] = math_score
        session['estimated_total'] = total_scaled
        session['estimated_ebrw'] = ebrw_scaled
        session['estimated_math'] = math_score
        session.modified = True
    except Exception as e:
        print(f"[initial_ebrw_submit] Failed to update user_progress: {e}")
        # Set session defaults on error (realistic values)
        session['total_score'] = 0
        session['ebrw_score'] = 0
        session['math_score'] = 0

    session.pop('initial_ebrw_qids', None)
    return redirect(url_for('score'))

def require_verified(view_func):
    # Decorator to block access until email_verified_at is set
    from functools import wraps
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_logged_in(session):
            # If not logged in, redirect to login page
            return redirect('/login')
        
        # User is logged in, check if they need to do initial diagnostic
        try:
            uid = session.get('user_id')
            if uid:
                # Removed diagnostic requirement - users can go directly to welcome
                pass
        except Exception as e:
            print(f"[ERROR] Error checking official scores: {e}")
            # Continue to welcome page if check fails
        
        return view_func(*args, **kwargs)
    return wrapper


# Email verification routes (must be after app init and helpers)
@app.route('/verify/pending')
def verify_pending():
    if not is_logged_in(session):
        return redirect('/login')
    just_registered = request.args.get('registered') == '1'
    # Pull latest pending info to show unique recipient (if available)
    inbound_recipient = None
    code_plain = session.get('verify_code_plain')
    if email_verifier and is_logged_in(session):
        try:
            pending = email_verifier.get_pending_for_user(session['user_id']) or {}
            inbound_recipient = pending.get('inbound_recipient')
        except Exception as e:
            inbound_recipient = None
    return render_template(
        'verify_pending.html',
        email=session.get('email') or '',
        hide_chrome=True,
        just_registered=just_registered,
        inbound_recipient=inbound_recipient,
        code_plain=code_plain
    )

@app.route('/verify')
def verify():
    token = request.args.get('token')
    if not token or not email_verifier:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('login'))
    row = email_verifier.verify_by_token(token)
    if not row:
        flash('Verification link is invalid or expired.', 'error')
        return redirect(url_for('verify_pending'))
    # Mark user verified in SQLite users table
    try:
        users.execute_sql(users.USERS_KEY, "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE UserID = ?", (row['user_id'],))
    except Exception as e:
        print(f"[email] failed to set verified: {e}")
    flash('Email verified! Welcome to Examlet.', 'success')
    return redirect(url_for('welcome'))

@app.route('/verify/code', methods=['POST'])
def verify_code():
    if not is_logged_in(session) or not email_verifier:
        return jsonify({'ok': False}), 400
    code = (request.get_json(silent=True) or {}).get('code') or request.form.get('code')
    if not code:
        return jsonify({'ok': False, 'error': 'missing code'}), 400
    uid = session['user_id']
    ok = email_verifier.verify_by_code(uid, code)
    if ok:
        users.execute_sql(users.USERS_KEY, "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE UserID = ?", (uid,))
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'invalid or expired'}), 400

@app.route('/verify/resend', methods=['POST'])
def verify_resend():
    if not is_logged_in(session) or not email_verifier:
        return jsonify({'ok': False}), 400
    uid = session['user_id']
    email = session.get('email')
    try:
        token, code, exp, inbound_recipient = email_verifier.resend(uid, email)
        link = url_for('verify', token=token, _external=True)
        body = (
            f"Hi {session.get('first_name') or ''},\n\n"
            f"Verify your email to continue using Examlet.\n\n"
            f"Click this link: {link}\n"
            f"Or enter this code: {code} (valid for 15 minutes)\n\n"
            f"If you didn't sign up, ignore this email.\n"
        )
        sent = send_email_plain(email, 'Verify your Examlet email', body)
        session['verify_code_plain'] = code
        session['verify_recipient'] = inbound_recipient
        return jsonify({'ok': True, 'sent': sent, 'recipient': inbound_recipient})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/verify/status')
def verify_status():
    if not is_logged_in(session):
        return jsonify({'ok': True, 'verified': False})
    # Check users table
    uid = session['user_id']
    cols, rows = users.execute_sql(users.USERS_KEY, "SELECT email_verified_at FROM users WHERE UserID = ?", (uid,))
    verified = bool(rows and rows[0] and rows[0][0])
    if not verified:
        # Try IMAP fallback if configured
        if _try_imap_verify_for_user(uid):
            cols, rows = users.execute_sql(users.USERS_KEY, "SELECT email_verified_at FROM users WHERE UserID = ?", (uid,))
            verified = bool(rows and rows[0] and rows[0][0])
    return jsonify({'ok': True, 'verified': verified})

# --- Inbound mail handling ---
@app.route('/webhooks/inbound/mailgun', methods=['POST'])
def mailgun_inbound():
    # Signature validation (optional if key not set)
    signing_key = os.getenv('MAILGUN_SIGNING_KEY')
    if signing_key:
        ts = request.form.get('timestamp')
        token = request.form.get('token')
        sig = request.form.get('signature')
        if not (ts and token and sig):
            return 'missing signature fields', 400
        digest = hmac.new(signing_key.encode('utf-8'), (ts + token).encode('utf-8'), _hashlib.sha256).hexdigest()
        if digest != sig:
            return 'invalid signature', 403
    recipient = request.form.get('recipient') or request.form.get('To') or ''
    sender = request.form.get('sender') or request.form.get('from') or ''
    subject = request.form.get('subject') or ''
    body = request.form.get('body-plain') or request.form.get('stripped-text') or ''
    if email_verifier and recipient and sender:
        try:
            uid = email_verifier.verify_from_inbound(recipient.strip().lower(), sender.strip().lower(), f"{subject}\n{body}")
            if uid:
                try:
                    users.execute_sql(users.USERS_KEY, "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE UserID = ?", (uid,))
                except Exception as e:
                    print(f"[email] sqlite verify set failed: {e}")
        except Exception as e:
            print(f"[email] inbound error: {e}")
    # Always 200 to avoid provider retries if we don't need them
    return 'ok', 200


def _try_imap_verify_for_user(user_id: int) -> bool:
    if (os.getenv('INBOUND_PROVIDER') or '').lower() != 'imap':
        return False
    host = os.getenv('IMAP_HOST')
    port = int(os.getenv('IMAP_PORT', '993'))
    user = os.getenv('IMAP_USER')
    pwd = os.getenv('IMAP_PASS')
    use_ssl = (os.getenv('IMAP_USE_SSL', 'true').lower() == 'true')
    if not (host and user and pwd):
        return False
    if not email_verifier:
        return False
    try:
        pending = email_verifier.get_pending_for_user(user_id) or {}
        recip = (pending.get('inbound_recipient') or '').strip().lower()
        if not recip:
            return False
        conn = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
        conn.login(user, pwd)
        conn.select('INBOX')
        typ, data = conn.search(None, 'UNSEEN')
        ids = []
        if typ == 'OK' and data and len(data) > 0:
            ids = data[0].split()
        # Check recent (limit 50)
        for mid in reversed(ids[-50:]):
            t, msgdata = conn.fetch(mid, '(RFC822)')
            if t != 'OK' or not msgdata or not msgdata[0]:
                continue
            raw = msgdata[0][1]
            msg = _email.message_from_bytes(raw)
            to_hdr = (msg.get('Delivered-To') or msg.get('To') or '').lower()
            from_hdr = (msg.get('From') or '').lower()
            if recip not in to_hdr:
                continue
            # Extract text content
            parts = []
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == 'text/plain':
                        try:
                            payload = part.get_payload(decode=True) or b''
                            parts.append(payload.decode(errors='ignore'))
                        except Exception:
                            pass
            else:
                try:
                    parts.append((msg.get_payload(decode=True) or b'').decode(errors='ignore'))
                except Exception:
                    pass
            content = (msg.get('Subject') or '') + "\n" + "\n".join(parts)
            uid = email_verifier.verify_from_inbound(recip, from_hdr, content)
            if uid:
                try:
                    users.execute_sql(users.USERS_KEY, "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE UserID = ?", (uid,))
                except Exception as e:
                    print(f"[email] sqlite verify set failed: {e}")
                try:
                    conn.store(mid, '+FLAGS', '\\Seen')
                except Exception:
                    pass
                conn.logout()
                return True
        conn.logout()
    except Exception as e:
        print(f"[email] IMAP check failed: {e}")
    return False

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in(session):
        flash('You are already logged in.', 'info')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        first_name = request.form.get('first_name').strip()
        last_name = (request.form.get('last_name') or '').strip()
        email = request.form.get('email').strip()
        username = request.form.get('username').strip()
        password = request.form.get('password')
        birth_date = (request.form.get('birth_date') or '').strip()

        if not all([first_name, email, username, password]):
            flash('All fields are required.', 'error')
            return render_template('register.html', hide_chrome=True)

        # Attempt to create user using the UsersDB method
        try:
            user_id = users.create_user(email, first_name, username, password)
        except Exception as e:
            print(f"[register] Error in create_user: {e}")
            import traceback
            traceback.print_exc()
            user_id = None

        if user_id:
            # Persist optional profile fields captured during registration
            try:
                users.update_user_profile(user_id, first_name, last_name, '', birth_date, 'private')
            except Exception as e:
                print(f"[register] profile enrich failed: {e}")
            
            # Process official SAT scores if provided
            has_taken_sat = request.form.get('has_taken_sat')
            if has_taken_sat == 'yes':
                try:
                    # Handle both single and multiple SAT score formats
                    sat_dates = request.form.getlist('sat_test_date[]')
                    sat_ebrw_scores = request.form.getlist('sat_ebrw_score[]')
                    sat_math_scores = request.form.getlist('sat_math_score[]')
                    
                    # If no array format, try single format
                    if not sat_dates:
                        sat_dates = [request.form.get('sat_test_date')]
                        sat_ebrw_scores = [request.form.get('sat_ebrw_score')]
                        sat_math_scores = [request.form.get('sat_math_score')]
                    
                    print(f"[REGISTER] Processing SAT scores: dates={sat_dates}, ebrw={sat_ebrw_scores}, math={sat_math_scores}")
                    
                    # Add each SAT score to the database
                    for i, test_date in enumerate(sat_dates):
                        if test_date and i < len(sat_ebrw_scores) and i < len(sat_math_scores):
                            ebrw_score_str = sat_ebrw_scores[i]
                            math_score_str = sat_math_scores[i]
                            
                            # Only add if scores are provided
                            if ebrw_score_str and math_score_str:
                                ebrw_score = int(ebrw_score_str) if ebrw_score_str else 0
                                math_score = int(math_score_str) if math_score_str else 0
                                total_score = ebrw_score + math_score
                                
                                # Use the same logic as the progress page
                                users.execute_sql(
                                    users.PROGRESS_KEY,
                                    """
                                    INSERT INTO official_test_scores 
                                    (UserID, TestDate, EBRWScore, MathScore, TotalScore, TestType)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (user_id, test_date, ebrw_score, math_score, total_score, 'official')
                                )
                                
                                print(f"[REGISTER] Added SAT score: {test_date}, EBRW={ebrw_score}, Math={math_score}, Total={total_score}")
                            
                except Exception as e:
                    print(f"[register] Error processing SAT scores: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Process practice test results if provided
            has_practice_tests = request.form.get('has_practice_tests')
            if has_practice_tests == 'yes':
                try:
                    # Get practice test arrays from form
                    practice_names = request.form.getlist('practice_test_name[]')
                    practice_dates = request.form.getlist('practice_test_date[]')
                    practice_ebrw_scores = request.form.getlist('practice_ebrw_score[]')
                    practice_math_scores = request.form.getlist('practice_math_score[]')
                    
                    print(f"[REGISTER] Processing practice tests: names={practice_names}, dates={practice_dates}, ebrw={practice_ebrw_scores}, math={practice_math_scores}")
                    
                    # Add each practice test to the database
                    for i, practice_name in enumerate(practice_names):
                        if practice_name and i < len(practice_dates) and i < len(practice_ebrw_scores) and i < len(practice_math_scores):
                            test_date = practice_dates[i]
                            ebrw_score_str = practice_ebrw_scores[i]
                            math_score_str = practice_math_scores[i]
                            
                            # Only add if scores are provided
                            if ebrw_score_str and math_score_str:
                                ebrw_score = int(ebrw_score_str) if ebrw_score_str else 0
                                math_score = int(math_score_str) if math_score_str else 0
                                total_score = ebrw_score + math_score
                                
                                # Use the same logic as the progress page
                                users.execute_sql(
                                    users.PROGRESS_KEY,
                                    """
                                    INSERT INTO practice_results 
                                    (UserID, PracticeName, PracticeDate, Score, EBRWScore, MathScore, MaxScore, PracticeType)
                                    VALUES (?, ?, ?, ?, ?, ?, 1600, 'practice')
                                    """,
                                    (user_id, practice_name, test_date, total_score, ebrw_score, math_score)
                                )
                                
                                print(f"[REGISTER] Added practice test: {practice_name}, {test_date}, EBRW={ebrw_score}, Math={math_score}, Total={total_score}")
                            
                except Exception as e:
                    print(f"[register] Error processing practice tests: {e}")
                    import traceback
                    traceback.print_exc()
                
            # TEMPORARILY DISABLED: Email verification
            # To re-enable, uncomment the following block and remove the direct login code below
            '''
            # Issue email verification and redirect to pending page
            if email_verifier:
                try:
                    token, code, exp, inbound_recipient = email_verifier.issue(user_id, email)
                    link = url_for('verify', token=token, _external=True)
                    body = (
                        f"Hi {first_name},\n\n"
                        f"Please verify your email to start using Examlet.\n\n"
                        f"Click this link: {link}\n"
                        f"Or enter this code: {code} (valid for 15 minutes)\n\n"
                        f"If you didn't sign up, ignore this email.\n"
                    )
                    send_email_plain(email, 'Verify your Examlet email', body)
                    # Save for UI display (code not stored in DB; ephemeral in session)
                    session['verify_code_plain'] = code
                    session['verify_recipient'] = inbound_recipient
                except Exception as e:
                    print(f"[email] issue failed: {e}")
            # Indicate to the pending page that this came from a fresh registration
            session['user_id'] = user_id
            session['first_name'] = first_name if first_name else username
            session['email'] = email or ''
            return redirect(url_for('verify_pending', registered=1))
            '''
            
            # TEMPORARY: Direct login without email verification
            # Mark email as verified in the database
            try:
                users.execute_sql(
                    users.USERS_KEY,
                    "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE UserID = ?",
                    (user_id,)
                )
            except Exception as e:
                print(f"[register] Failed to mark email as verified: {e}")
            
            # CRITICAL: Clear all large session data before setting new session variables
            # This prevents cookie size issues (browsers limit cookies to ~4093 bytes)
            large_session_keys = [
                'ebrw_test_question_data',  # Stores full question objects - very large!
                'ebrw_test_questions',
                'ebrw_test_answers',
                'ebrw_test_marked',
                'ebrw_test_results',
                'ebrw_part1_results',
                'ebrw_test_part',
                'ebrw_test_start_time',
                'ebrw_test_paused',
                'ebrw_test_elapsed',
                'ebrw_part1_performance',
                'lesson_qids',
                'lesson_option_orders'
            ]
            
            # Set essential session variables for NEW user
            session['user_id'] = user_id
            session['username'] = username
            session['first_name'] = first_name if first_name else username
            session['email'] = email or ''
            session['verified'] = True
            
            # Debug: Log what user we just registered
            print(f"[REGISTER] New user registered with FRESH session: user_id={user_id}, username={username}")
            print(f"[REGISTER] Session after setup: {dict(session)}")
            
            # Load user progress data into session for quick access
            try:
                progress_data = users.get_user_progress(user_id)
                if progress_data:
                    session['total_score'] = progress_data.get('total_score', 0)
                    session['ebrw_score'] = progress_data.get('ebrw_score', 0)
                    session['math_score'] = progress_data.get('math_score', 0)
                    session['current_streak'] = progress_data.get('current_streak', 0)
                else:
                    # Set realistic defaults if no progress data (new user)
                    session['total_score'] = 0
                    session['ebrw_score'] = 0
                    session['math_score'] = 0
                    session['current_streak'] = 0
            except Exception as e:
                print(f"[register] Failed to load progress data: {e}")
                # Set realistic defaults on error (new user)
                session['total_score'] = 0
                session['ebrw_score'] = 0
                session['math_score'] = 0
                session['current_streak'] = 0
            
            # CRITICAL: Mark session as modified so Flask saves it
            session.modified = True
            
            flash('Registration successful!', 'success')
            
            # Check if user has official test scores - if not, redirect to welcome page
            try:
                official_scores = users.get_official_test_scores(user_id)
                print(f"[REGISTER] Checking official scores for new user {user_id}: {official_scores}")
                # Always redirect to welcome for new users - they can add scores later
                print(f"[REGISTER] Redirecting new user {user_id} to welcome page")
                return redirect(url_for('welcome'))
            except Exception as e:
                print(f"[register] Error checking official scores: {e}")
                # If check fails, still redirect to welcome
                return redirect(url_for('welcome'))
            
            # User has official scores, go to profile
            return redirect(url_for('profile'))
        else:
            # This handles duplicate email (users table) or duplicate username (logins table)
            flash('Registration failed. Username or Email might already be taken.', 'error')
            return render_template('register.html', hide_chrome=True)

    return render_template('register.html', hide_chrome=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in(session):
        flash('You are already logged in.', 'info')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        username_raw = request.form.get('username', '')
        username = username_raw.strip() if username_raw else ''
        password = request.form.get('password', '')

        if not all([username, password]):
            flash('Username and password are required.', 'error')
            return render_template('login.html', hide_chrome=True)

        user_id_and_hash = get_user_id_and_hash(username)

        if user_id_and_hash and len(user_id_and_hash) == 2:
            user_id, password_hash = user_id_and_hash

            # Guard against missing/None hashes to avoid AttributeError
            if not password_hash:
                flash('This account has no password set. Please reset your password or contact support.', 'error')
                return render_template('login.html', hide_chrome=True)

            # Use check_password_hash for secure password comparison
            if check_password_hash(password_hash, password):
                # CRITICAL: Clear all large session data before setting new session variables
                # This prevents cookie size issues (browsers limit cookies to ~4093 bytes)
                large_session_keys = [
                    'ebrw_test_question_data',  # Stores full question objects - very large!
                    'ebrw_test_questions',
                    'ebrw_test_answers',
                    'ebrw_test_marked',
                    'ebrw_test_results',
                    'ebrw_part1_results',
                    'ebrw_test_part',
                    'ebrw_test_start_time',
                    'ebrw_test_paused',
                    'ebrw_test_elapsed',
                    'ebrw_part1_performance',
                    'lesson_qids',
                    'lesson_option_orders',
                    'lesson_current_question',
                    'lesson_quiz_score',
                    'initial_ebrw_qids',
                    'lesson_answered',
                    'lesson_selected_option',
                    'lesson_selected_pairs'
                ]
                for key in large_session_keys:
                    session.pop(key, None)
                
                # Set essential session variables
                session['user_id'] = user_id
                session['username'] = username  # Store username in session

                # Fetch first name and store in session for display
                first_name, email = get_user_data_by_id(user_id)
                session['first_name'] = first_name if first_name else username
                session['email'] = email if email else ''

                # Load user progress data into session for quick access
                # Load progress; prefer username-based storage if available
                progress_data = None
                try:
                    if username and hasattr(users, 'get_progress_by_username'):
                        progress_data = users.get_progress_by_username(username)
                    else:
                        progress_data = users.get_user_progress(user_id)
                    if progress_data:
                        session['total_score'] = progress_data.get('total_score', 1600)
                        session['ebrw_score'] = progress_data.get('ebrw_score', 800)
                        session['math_score'] = progress_data.get('math_score', 800)
                        session['current_streak'] = progress_data.get('current_streak', 0)
                    else:
                        # Set defaults if no progress data
                        session['total_score'] = 1600
                        session['ebrw_score'] = 800
                        session['math_score'] = 800
                        session['current_streak'] = 0
                except Exception as e:
                    print(f"[ERROR] Failed to load progress data: {e}")
                    # Set defaults on error
                    session['total_score'] = 1600
                    session['ebrw_score'] = 800
                    session['math_score'] = 800
                    session['current_streak'] = 0

                # CRITICAL: Mark session as modified so Flask saves it
                session.modified = True

                # Skip email verification check for now
                flash(f'Welcome back, {session["first_name"]}!', 'success')
                return redirect(url_for('welcome'))
            else:
                flash('Invalid username or password.', 'error')
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html', hide_chrome=True)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('first_name', None)
    session.pop('email', None)
    session.pop('total_score', None)
    session.pop('ebrw_score', None)
    session.pop('math_score', None)
    session.pop('current_streak', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))




def extract_word_from_question(question):
    """Extract the main vocabulary word from a question for progress tracking."""
    if 'word' in question:
        return question['word']
    elif question['type'] == 'pairs_matching':
        return "Vocabulary Matching"
    else:
        # Try to extract word from question text
        question_text = question['question']
        if "definition of '" in question_text:
            start = question_text.find("'") + 1
            end = question_text.find("'", start)
            return question_text[start:end] if end > start else None
        elif "synonym for '" in question_text:
            start = question_text.find("'") + 1
            end = question_text.find("'", start)
            return question_text[start:end] if end > start else None
        elif "antonym for '" in question_text:
            start = question_text.find("'") + 1
            end = question_text.find("'", start)
            return question_text[start:end] if end > start else None
    return None


@app.route('/vocabulary_practice')
def vocabulary_practice():
    if is_logged_in(session):
        # Initialize quiz session
        session['quiz_score'] = 0
        session['current_question'] = 0
        session['answered'] = False
        session['selected_option'] = None
        session['selected_pairs'] = None
        session['questions'] = random.sample(LESSON1_QUESTIONS, len(LESSON1_QUESTIONS))
        session['option_orders'] = {}

        current_question_index = session['current_question']
        if current_question_index < len(session['questions']):
            question = session['questions'][current_question_index]

            if question['type'] == 'pairs_matching':
                # For pairs matching, we need to prepare shuffled words and definitions
                words = [pair['word'] for pair in question['pairs']]
                definitions = [pair['definition'] for pair in question['pairs']]
                random.shuffle(words)
                random.shuffle(definitions)

                return render_template('vocabulary_practice.html',
                                       question=question,
                                       words=words,
                                       definitions=definitions,
                                       current_index=current_question_index,
                                       total_questions=len(session['questions']),
                                       score=session['quiz_score'],
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None,
                                       show_leave=True,
                                       leave_url=url_for('vocabulary'))
            else:
                # Shuffle options only once per question index and persist to session
                option_orders = session.get('option_orders') or {}
                key = str(current_question_index)
                if key not in option_orders:
                    order = question['options'][:]
                    random.shuffle(order)
                    option_orders[key] = order
                    session['option_orders'] = option_orders
                return render_template('vocabulary_practice.html',
                                       question=question,
                                       options=session['option_orders'][key],
                                       current_index=current_question_index,
                                       total_questions=len(session['questions']),
                                       score=session['quiz_score'],
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None,
                                       show_leave=True,
                                       leave_url=url_for('vocabulary'))

        return render_template('vocabulary_practice.html', show_leave=True, leave_url=url_for('vocabulary'))
    return redirect('/login')


@app.route('/vocabulary_answer', methods=['POST'])
def vocabulary_answer():
    if is_logged_in(session):
        user_id = session['user_id']
        # Guard against missing session state
        if 'current_question' not in session or 'questions' not in session or not session['questions']:
            return redirect(url_for('vocabulary'))
        current_question_index = session.get('current_question', 0)
        questions = session.get('questions', [])

        if current_question_index >= len(questions):
            return redirect('/vocabulary_results')

        current_question = questions[current_question_index]

        if current_question['type'] == 'pairs_matching':
            # Handle pairs matching submission
            selected_pairs = {}
            correct_count = 0
            total_pairs = len(current_question['pairs'])

            for pair in current_question['pairs']:
                word = pair['word']
                selected_definition = request.form.get(f'pair_{word}')
                selected_pairs[word] = selected_definition

                # Check if the selected definition matches the correct one
                if selected_definition == pair['definition']:
                    correct_count += 1
                    users.update_quest_progress(user_id, "Learn 5 new words", 1)

            # Allow one mistake for successful completion
            is_correct = correct_count >= total_pairs - 1

            if is_correct:
                session['quiz_score'] += 1

            session['answered'] = True
            session['selected_pairs'] = selected_pairs

            # If auto_skip requested (too many mistakes), move to next question immediately
            if (request.form.get('auto_skip') == '1') and (not is_correct):
                session['answered'] = False
                session['selected_pairs'] = None
                return redirect(url_for('vocabulary_next'))

            # Create detailed feedback message
            if is_correct:
                if correct_count == total_pairs:
                    explanation_msg = f"Perfect! All {total_pairs} pairs matched correctly."
                else:
                    explanation_msg = f"Good job! You got {correct_count} out of {total_pairs} pairs correct. One mistake is allowed."
            else:
                explanation_msg = f"Try again! You got {correct_count} out of {total_pairs} pairs correct. Only one mistake is allowed."

            feedback = {
                'is_correct': is_correct,
                'explanation': explanation_msg,
                'selected_pairs': selected_pairs,
                'correct_count': correct_count,
                'total_pairs': total_pairs
            }

            # Build lists for rendering
            words_ans = [p['word'] for p in current_question['pairs']]
            definitions_ans = [p['definition'] for p in current_question['pairs']]

            return render_template('vocabulary_practice.html',
                                   question=current_question,
                                   pairs=current_question['pairs'],
                                   words=words_ans,
                                   definitions=definitions_ans,
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=True,
                                   feedback=feedback,
                                   correct_answer=None,
                                   selected_option=None,
                                   show_leave=True,
                                   leave_url=url_for('vocabulary'))
        else:
            # Handle regular question types
            selected_option = request.form.get('selected_option')
            is_correct = selected_option == current_question['answer']

            if is_correct:
                session['quiz_score'] += 1
                users.update_quest_progress(user_id, "Learn 5 new words", 1)

            session['answered'] = True
            session['selected_option'] = selected_option

            feedback = {
                'is_correct': is_correct,
                'correct_answer': current_question['answer'],
                'explanation': current_question['explanation'],
                'selected_option': selected_option
            }

            # Update vocabulary progress in database
            word = extract_word_from_question(current_question)
            if word:
                users.update_vocabulary_progress(user_id, word, is_correct)

            return render_template('vocabulary_practice.html',
                                   question=current_question,
                                   options=(session.get('option_orders') or {}).get(str(current_question_index), current_question['options']),
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=True,
                                   feedback=feedback,
                                   correct_answer=current_question['answer'],
                                   selected_option=selected_option,
                                   show_leave=True,
                                   leave_url=url_for('vocabulary'))
    return redirect('/login')


@app.route('/vocabulary_next', methods=['GET', 'POST'])
def vocabulary_next():
    if is_logged_in(session):
        # Initialize session state if missing
        if 'current_question' not in session:
            session['current_question'] = 0
        if 'questions' not in session or not session['questions']:
            return redirect(url_for('vocabulary'))
        session['current_question'] += 1
        session['answered'] = False
        session['selected_option'] = None
        session['selected_pairs'] = None

        current_question_index = session.get('current_question', 0)
        questions = session.get('questions', [])

        if current_question_index >= len(questions):
            return redirect('/vocabulary_results')

        question = questions[current_question_index]

        if question['type'] == 'pairs_matching':
            words = [pair['word'] for pair in question['pairs']]
            definitions = [pair['definition'] for pair in question['pairs']]
            random.shuffle(words)
            random.shuffle(definitions)

            return render_template('vocabulary_practice.html',
                                   question=question,
                                   words=words,
                                   definitions=definitions,
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=False,
                                   feedback=None,
                                   correct_answer=None,
                                   selected_option=None,
                                   show_leave=True,
                                   leave_url=url_for('vocabulary'))
        else:
            # Reuse persisted shuffle or create it for this index
            option_orders = session.get('option_orders') or {}
            key = str(current_question_index)
            if key not in option_orders:
                order = question['options'][:]
                random.shuffle(order)
                option_orders[key] = order
                session['option_orders'] = option_orders
            return render_template('vocabulary_practice.html',
                                   question=question,
                                   options=session['option_orders'][key],
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=False,
                                   feedback=None,
                                   correct_answer=None,
                                   selected_option=None,
                                   show_leave=True,
                                   leave_url=url_for('vocabulary'))
    return redirect('/login')


@app.route('/vocabulary_results')
def vocabulary_results():
    if is_logged_in(session):
        user_id = session['user_id']
        score = session.get('quiz_score', 0)
        total_questions = len(session.get('questions', []))
        percentage = round((score / total_questions) * 100) if total_questions > 0 else 0

        if percentage >= 90:
            performance_msg = "Excellent work! 🎉"
        elif percentage >= 70:
            performance_msg = "Good job! 👍"
        elif percentage >= 50:
            performance_msg = "Not bad! Keep practicing. 💪"
        else:
            performance_msg = "Keep studying! You'll get better. 📚"
        # Qualifying action: mark daily activity for streaks (Phase 2 wiring)
        try:
            if 'streaks' in globals() and streaks:
                streaks.mark_daily_activity(user_id, date.today(), 'practice')
        except Exception as e:
            print(f"[streaks] mark_daily_activity failed: {e}")

        session.pop('quiz_score', None)
        session.pop('current_question', None)
        session.pop('answered', None)
        session.pop('selected_option', None)
        session.pop('selected_pairs', None)
        session.pop('questions', None)

        return render_template('vocabulary_practice.html',
                               quiz_complete=True,
                               score=score,
                               total_questions=total_questions,
                               percentage=percentage,
                               performance_msg=performance_msg,
                               show_leave=True,
                               leave_url=url_for('vocabulary'))
    return redirect('/login')


@app.route('/')
def base():
    return redirect('lessons')


@app.route('/welcome')
@require_verified
def welcome():
    if is_logged_in(session):
        name = session.get('first_name') or 'there'
        return render_template('welcome.html', name=name)
    return redirect('/login')


@app.route('/lessons')
@require_verified
def lessons():
    if is_logged_in(session):
        user_id = session.get('user_id')
        # Live update estimated score in session for header display
        try:
            est = users.calculate_estimated_score(user_id)
            session['estimated_total'] = est.get('total')
            session['estimated_ebrw'] = est.get('ebrw')
            session['estimated_math'] = est.get('math')
        except Exception as e:
            print(f"Error updating estimated score: {e}")
        
        # Define the domain and skill structure
        domains = [
            {
                'id': 'info_ideas',
                'name': 'Information and Ideas',
                'skills': [
                    {'id': 'central_ideas', 'name': 'Central Ideas and Details', 'description': 'Identify main ideas and supporting details'},
                    {'id': 'inferences', 'name': 'Inferences', 'description': 'Make logical inferences from the text'},
                    {'id': 'command_evidence', 'name': 'Command of Evidence', 'description': 'Use evidence to support claims'}
                ]
            },
            {
                'id': 'craft_structure',
                'name': 'Craft and Structure',
                'skills': [
                    {'id': 'words_context', 'name': 'Words in Context', 'description': 'Understand words in various contexts'},
                    {'id': 'text_structure', 'name': 'Text Structure and Purpose', 'description': 'Analyze text structure and author\'s purpose'},
                    {'id': 'cross_text', 'name': 'Cross-Text Connections', 'description': 'Make connections between different texts'}
                ]
            },
            {
                'id': 'expression_ideas',
                'name': 'Expression of Ideas',
                'skills': [
                    {'id': 'rhetorical', 'name': 'Rhetorical Synthesis', 'description': 'Combine information from multiple sources'},
                    {'id': 'transitions', 'name': 'Transitions', 'description': 'Use appropriate transitions between ideas'}
                ]
            },
            {
                'id': 'conventions',
                'name': 'Standard English Conventions',
                'skills': [
                    {'id': 'boundaries', 'name': 'Boundaries', 'description': 'Recognize and correct boundary issues'},
                    {'id': 'form_structure', 'name': 'Form, Structure, and Sense', 'description': 'Ensure proper form and structure in writing'}
                ]
            }
        ]
        
        # Add progress data to each skill (placeholder - in a real app, this would come from the database)
        for domain in domains:
            for skill in domain['skills']:
                # TODO: Replace with actual progress calculation from user's data
                skill['progress'] = random.randint(0, 100)
        
        # Define difficulty levels
        difficulties = [
            {'id': 'easy', 'name': 'Easy'},
            {'id': 'medium', 'name': 'Medium'},
            {'id': 'hard', 'name': 'Hard'}
        ]
        
        return render_template(
            'lessons.html',
            difficulties=difficulties,
            domains=domains,
            score_data=session.get('score_data', {})
        )
    return redirect('/login')


@app.route('/debug/db_check')
@login_required
def debug_db_check():
    """Debug route to check database structure and content."""
    if not is_logged_in(session):
        return "Please log in first", 401
        
    try:
        user_id = session['user_id']
        output = ["<h1>Database Debug Information</h1>"]
        
        # Check if table exists
        tables = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        
        output.append("<h2>Tables in database:</h2>")
        output.append("<ul>")
        for table in tables[1]:
            output.append(f"<li>{table[0]}</li>")
        output.append("</ul>")
        
        # Check official_test_scores table structure
        if any('official_test_scores' in table[0].lower() for table in tables[1] if table[0]):
            output.append("<h2>official_test_scores structure:</h2>")
            table_info = users.execute_sql(
                users.PROGRESS_KEY,
                "PRAGMA table_info(official_test_scores);"
            )
            output.append("<table border='1'><tr><th>ID</th><th>Name</th><th>Type</th><th>Not Null</th><th>Default</th><th>PK</th></tr>")
            for col in table_info[1]:
                output.append(f"<tr><td>{col[0]}</td><td>{col[1]}</td><td>{col[2]}</td><td>{col[3]}</td><td>{col[4]}</td><td>{col[5]}</td></tr>")
            output.append("</table>")
            
            # Show data for current user
            user_scores = users.execute_sql(
                users.PROGRESS_KEY,
                "SELECT * FROM official_test_scores WHERE UserID = ?",
                (user_id,)
            )
            
            if user_scores and user_scores[1]:
                output.append("<h2>Your test scores:</h2>")
                output.append("<table border='1'><tr>")
                
                # Add headers
                if table_info and table_info[1]:
                    for col in table_info[1]:
                        output.append(f"<th>{col[1]}</th>")
                output.append("</tr>")
                
                # Add data rows
                for row in user_scores[1]:
                    output.append("<tr>")
                    for val in row:
                        output.append(f"<td>{val}</td>")
                    output.append("</tr>")
                output.append("</table>")
            else:
                output.append("<p>No test scores found for your account.</p>")
        else:
            output.append("<p>official_test_scores table does not exist.</p>")
            
        output.append("<p><a href='/progress'>Back to Progress</a></p>")
        return "\n".join(output)
        
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/debug/add_test_score_directly')
@login_required
def add_test_score_directly():
    """Debug route to add a test score directly."""
    if not is_logged_in(session):
        return "Please log in first", 401
        
    try:
        user_id = session['user_id']
        test_date = datetime.now().strftime('%Y-%m-%d')
        ebrw_score = 700
        math_score = 750
        total_score = ebrw_score + math_score
        
        # Add test score directly
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            INSERT OR IGNORE INTO official_test_scores 
            (UserID, TestDate, EBRWScore, MathScore, TotalScore)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, test_date, ebrw_score, math_score, total_score)
        )
        
        # Get the ID of the inserted row
        result = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT last_insert_rowid();"
        )
        
        row_id = result[1][0][0] if result and result[1] else "unknown"
        
        return f"""
            <h1>Test Score Added</h1>
            <p>Added test score with:</p>
            <ul>
                <li>UserID: {user_id}</li>
                <li>Date: {test_date}</li>
                <li>EBRW: {ebrw_score}</li>
                <li>Math: {math_score}</li>
                <li>Total: {total_score}</li>
                <li>Row ID: {row_id}</li>
            </ul>
            <p><a href='/progress'>View on Progress Page</a> | <a href='/debug/check_scores'>Check All Scores</a></p>
        """
        
    except Exception as e:
        import traceback
        return f"<pre>Error: {str(e)}\n\n{traceback.format_exc()}</pre>"

@app.route('/debug/check_scores')
@login_required
def debug_check_scores():
    """Debug route to check the state of test scores."""
    if not is_logged_in(session):
        return "Please log in first", 401
        
    try:
        user_id = session['user_id']
        output = ["<h1>Debug: Official Test Scores</h1>"]
        
        # 1. Check if table exists
        table_check = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT name FROM sqlite_master WHERE type='table' AND name='official_test_scores';"
        )
        
        if not table_check or not table_check[1]:
            return "official_test_scores table does not exist. <a href='/debug/create_table'>Create table</a>"
            
        # 2. Get table structure
        table_info = users.execute_sql(
            users.PROGRESS_KEY,
            "PRAGMA table_info(official_test_scores);"
        )
        
        output.append("<h2>Table Structure:</h2><pre>")
        if table_info and table_info[1]:
            for col in table_info[1]:
                output.append(f"{col[1]} ({col[2]})")
        output.append("</pre>")
        
        # 3. Get count of records
        count = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT COUNT(*) FROM official_test_scores WHERE UserID = ?;",
            (user_id,)
        )
        
        output.append(f"<h2>Records for user {user_id}: {count[1][0][0] if count and count[1] else 0}</h2>")
        
        # 4. Get sample data
        data = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT * FROM official_test_scores WHERE UserID = ?;",
            (user_id,)
        )
        
        if data and data[1]:
            output.append("<h3>Your Test Scores:</h3><table border='1'><tr>")
            # Add headers
            for col in data[0]:
                output.append(f"<th>{col[0]}</th>")
            output.append("</tr>")
            
            # Add rows
            for row in data[1]:
                output.append("<tr>")
                for val in row:
                    output.append(f"<td>{val}</td>")
                output.append("</tr>")
            output.append("</table>")
        else:
            output.append("<p>No test scores found for this user. <a href='/debug/add_test_score'>Add test score</a></p>")
            
        # Add link to add test score
        output.append("<p><a href='/debug/add_test_score'>Add Test Score</a> | <a href='/progress'>Back to Progress</a></p>")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/debug/create_table')
@login_required
def debug_create_table():
    """Debug route to create the official_test_scores table if it doesn't exist."""
    if not is_logged_in(session):
        return "Please log in first", 401
        
    try:
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            CREATE TABLE IF NOT EXISTS official_test_scores (
                TestID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER NOT NULL,
                TestDate TEXT NOT NULL,
                EBRWScore INTEGER NOT NULL,
                MathScore INTEGER NOT NULL,
                TotalScore INTEGER NOT NULL,
                FOREIGN KEY (UserID) REFERENCES users(UserID)
            )
            """
        )
        return "Table 'official_test_scores' created or already exists. <a href='/progress'>Go to Progress</a>"
    except Exception as e:
        return f"Error creating table: {str(e)}", 500

@app.route('/debug/add_test_score')
@login_required
def debug_add_test_score():
    """Debug route to add a test score."""
    if not is_logged_in(session):
        return "Please log in first", 401
        
    try:
        user_id = session['user_id']
        test_date = datetime.now().strftime('%Y-%m-%d')
        ebrw_score = 700
        math_score = 750
        total_score = ebrw_score + math_score
        
        # Ensure table exists
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            CREATE TABLE IF NOT EXISTS official_test_scores (
                TestID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER NOT NULL,
                TestDate TEXT NOT NULL,
                EBRWScore INTEGER NOT NULL,
                MathScore INTEGER NOT NULL,
                TotalScore INTEGER NOT NULL,
                FOREIGN KEY (UserID) REFERENCES users(UserID)
            )
            """
        )
        
        # Add test score
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            INSERT INTO official_test_scores (UserID, TestDate, EBRWScore, MathScore, TotalScore)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, test_date, ebrw_score, math_score, total_score)
        )
        
        return """
            <h1>Test Score Added</h1>
            <p>Added test score with:</p>
            <ul>
                <li>EBRW: 700</li>
                <li>Math: 750</li>
                <li>Total: 1450</li>
            </ul>
            <p><a href='/debug/check_scores'>View All Scores</a> | <a href='/progress'>Back to Progress</a></p>
        """
        
    except Exception as e:
        return f"Error adding test score: {str(e)}"

@app.route('/progress')
def score():
    if is_logged_in(session):
        user_id = session['user_id']
        print(f"\n[DEBUG] ===== Progress Page Load =====")
        print(f"[DEBUG] User ID: {user_id}")
        
        # Check if official_test_scores table exists
        table_check = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT name FROM sqlite_master WHERE type='table' AND name='official_test_scores';"
        )
        print(f"[DEBUG] Table exists check: {table_check}")
        
        # Get table structure if it exists
        if table_check and table_check[1]:
            table_info = users.execute_sql(
                users.PROGRESS_KEY,
                "PRAGMA table_info(official_test_scores);"
            )
            print(f"[DEBUG] Table structure: {table_info}")
            
            # Get all data from the table
            all_data = users.execute_sql(
                users.PROGRESS_KEY,
                "SELECT * FROM official_test_scores;"
            )
            print(f"[DEBUG] All data in official_test_scores: {all_data}")
        
        # Prefer username-based logical tables if available
        username = users.get_username_by_user_id(user_id)
        print(f"[DEBUG] Username: {username}")
        
        # Force using user_id based retrieval for now
        print("[DEBUG] Forcing user_id based data retrieval")
        # Get fresh progress data from database (not cached)
        progress_data = users.get_user_progress(user_id)
        print(f"[DEBUG] Progress data: {progress_data}")
        
        # If progress_data still has old values, reset them
        if progress_data and (progress_data.get('total_score', 0) > 0 or progress_data.get('ebrw_score', 0) > 0):
            print("[DEBUG] Detected old inflated scores, resetting to zero")
            progress_data = {
                'total_score': 0,
                'ebrw_score': 0,
                'math_score': 0,
                'current_streak': progress_data.get('current_streak', 0),
                'streak_goal': progress_data.get('streak_goal', 7)
            }
            # Update the database
            users.execute_sql(
                users.PROGRESS_KEY,
                "UPDATE user_progress SET TotalScore = 0, EBRWScore = 0, MathScore = 0 WHERE UserID = ?",
                (user_id,)
            )
        print(f"[DEBUG] Final progress data: {progress_data}")
        
        # Get official scores with debug info
        print("[DEBUG] Fetching official test scores...")
        official_scores = users.get_official_test_scores(user_id)
        print(f"[DEBUG] Official scores (raw): {official_scores}")
        
        # Get practice results
        print("[DEBUG] Fetching practice results...")
        practice_results = users.get_practice_results(user_id)
        print(f"[DEBUG] Practice results: {practice_results}")
        
        # Get EBRW score from user_progress first (from official tests or practice tests)
        # If not available, calculate from lesson history
        progress_data = users.get_user_progress(user_id)
        if progress_data and progress_data.get('ebrw_score'):
            ebrw_score = progress_data.get('ebrw_score')
            print(f"[DEBUG] Using EBRW score from user_progress: {ebrw_score}")
        else:
            # Calculate EBRW score based on lesson history (last 54 English questions)
            score_data = calculate_ebrw_score(user_id)
            print(f"[DEBUG] EBRW score data: {score_data}")
            ebrw_score = score_data['score']
        
        math_score = 800  # Default math score
        total_score = ebrw_score + math_score
        
        # Only update user_progress if we calculated from lessons (not if it already has a test score)
        if not (progress_data and progress_data.get('ebrw_score')):
            try:
                users.execute_sql(
                    users.PROGRESS_KEY,
                    """
                    INSERT INTO user_progress (UserID, EBRWScore, MathScore, TotalScore)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(UserID) DO UPDATE SET
                        EBRWScore=excluded.EBRWScore,
                        MathScore=excluded.MathScore,
                        TotalScore=excluded.TotalScore
                    """,
                    (user_id, ebrw_score, math_score, total_score)
                )
            except Exception as e:
                print(f"[ERROR] Failed to update user_progress: {e}")
        
        # Refresh progress data
        progress_data = users.get_user_progress(user_id)
        
        # Calculate estimated scores based on lesson performance (for display)
        print("[DEBUG] Calculating estimated scores...")
        estimated_scores = users.calculate_estimated_score(user_id)
        print(f"[DEBUG] Estimated scores: {estimated_scores}")
        
        # Update the progress data with estimated scores
        if progress_data:
            progress_data['estimated_ebrw'] = estimated_scores['ebrw']
            progress_data['estimated_math'] = estimated_scores['math']
            progress_data['estimated_total'] = estimated_scores['total']
            # Ensure EBRW score is from calculate_ebrw_score
            progress_data['ebrw_score'] = ebrw_score
            progress_data['total_score'] = total_score
        
        # Debug: No longer auto-creating test scores
        if not official_scores:
            print("[DEBUG] No official scores found for user - showing empty state")
        
        # Ensure we have a list, even if empty
        if not isinstance(official_scores, list):
            print("[WARNING] official_scores is not a list, converting to empty list")
            official_scores = []
            
        print(f"[DEBUG] Final official_scores: {official_scores}")
        
        # Calculate superscore (best EBRW + best Math from all tests)
        # Handle both old and new data formats
        ebrw_scores = []
        math_scores = []
        
        for score in official_scores:
            # Handle both formats: new (e/m) and old (ebrw_score/math_score)
            ebrw = score.get('e', score.get('ebrw_score', 0))
            math = score.get('m', score.get('math_score', 0))
            
            # Convert to integers if they're strings
            try:
                ebrw = int(ebrw) if ebrw not in [None, ''] else 0
                math = int(math) if math not in [None, ''] else 0
                
                ebrw_scores.append(ebrw)
                math_scores.append(math)
                
            except (ValueError, TypeError) as e:
                print(f"[WARNING] Error parsing scores for superscore: {score}")
        
        # Calculate max scores, defaulting to 0 if no valid scores found
        max_ebrw = max(ebrw_scores) if ebrw_scores else 0
        max_math = max(math_scores) if math_scores else 0
        
        superscore = {
            'ebrw': max_ebrw,
            'math': max_math,
            'total': max_ebrw + max_math
        }
        print(f"[DEBUG] Calculated superscore: {superscore}")
        
        if username and hasattr(users, 'get_progress_by_username'):
            print("[DEBUG] Using username-based data retrieval")
            progress_data = users.get_progress_by_username(username)
            official_scores = users.get_official_results_by_username(username) if hasattr(users, 'get_official_results_by_username') else []
            practice_results = users.get_practice_results_by_username(username) if hasattr(users, 'get_practice_results_by_username') else []
        else:
            print("[DEBUG] Using user_id-based data retrieval")
            progress_data = users.get_user_progress(user_id)
            print(f"[DEBUG] Progress data: {progress_data}")
            
            # Get official scores with debug info
            print("[DEBUG] Fetching official test scores...")
            official_scores = users.get_official_test_scores(user_id)
            print(f"[DEBUG] Official scores: {official_scores}")
            
            # Get practice results
            print("[DEBUG] Fetching practice results...")
            practice_results = users.get_practice_results(user_id)
            print(f"[DEBUG] Practice results: {practice_results}")
            
            # Debug: Check if official_test_scores table exists and has data
            print("\n[DEBUG] Checking official_test_scores table directly...")
            try:
                # Check if table exists
                table_check = users.execute_sql(
                    users.PROGRESS_KEY,
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='official_test_scores';"
                )
                print(f"[DEBUG] Table check: {table_check}")
                
                if table_check and table_check[1]:
                    # Table exists, get count of records for this user
                    count = users.execute_sql(
                        users.PROGRESS_KEY,
                        "SELECT COUNT(*) FROM official_test_scores WHERE UserID = ?;",
                        (user_id,)
                    )
                    print(f"[DEBUG] Number of records for user {user_id}: {count}")
                    
                    # Get sample data
                    sample = users.execute_sql(
                        users.PROGRESS_KEY,
                        "SELECT * FROM official_test_scores WHERE UserID = ? LIMIT 5;",
                        (user_id,)
                    )
                    print(f"[DEBUG] Sample data: {sample}")
                else:
                    print("[DEBUG] official_test_scores table does not exist")
                    
            except Exception as e:
                print(f"[ERROR] Error checking official_test_scores table: {str(e)}")
                import traceback
                traceback.print_exc()

        # Calculate EBRW score from lessons and update progress_data
        score_data = calculate_ebrw_score(user_id)
        ebrw_score = score_data['score']
        math_score = 800  # Always 800 for now
        total_score = ebrw_score + math_score
        
        # Update progress_data with calculated scores
        if not progress_data:
            progress_data = {}
        progress_data['ebrw_score'] = ebrw_score
        progress_data['math_score'] = math_score
        progress_data['total_score'] = total_score
        
        # Update session with latest scores
        session['total_score'] = total_score
        session['ebrw_score'] = ebrw_score
        session['math_score'] = math_score
        
        if 'current_streak' in progress_data:
            session['current_streak'] = progress_data['current_streak']

        # Sort official scores
        sort_official = request.args.get('sort_official', 'date')
        sort_dir_official = request.args.get('sort_dir_official', 'desc')
        
        print(f"[DEBUG] Before sorting - official_scores: {official_scores}")
        
        if official_scores:
            # Convert date strings to date objects for proper sorting
            for score in official_scores:
                if 'date' in score and score['date']:
                    try:
                        score['sort_date'] = datetime.strptime(score['date'], '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        print(f"[WARNING] Error parsing date {score.get('date')}: {str(e)}")
                        score['sort_date'] = date.min
                else:
                    print(f"[WARNING] Missing or invalid date in score: {score}")
                    score['sort_date'] = date.min
            
            # Sort based on the selected column and direction
            reverse_sort = (sort_dir_official == 'desc')
            if sort_official == 'date':
                official_scores.sort(key=lambda x: x.get('sort_date', date.min), reverse=reverse_sort)
            elif sort_official == 'total':
                official_scores.sort(key=lambda x: x.get('total_score', 0), reverse=reverse_sort)
                
            print(f"[DEBUG] After sorting - official_scores: {official_scores}")
        else:
            print("[WARNING] No official scores to sort")

        # Sort practice results
        sort_practice = request.args.get('sort_practice', 'date')
        sort_dir_practice = request.args.get('sort_dir_practice', 'desc')
        
        if practice_results:
            # Convert date strings to date objects for proper sorting
            for result in practice_results:
                if 'date' in result and result['date']:
                    try:
                        result['sort_date'] = datetime.strptime(result['date'], '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        print(f"[WARNING] Error parsing date {result.get('date')}: {str(e)}")
                        result['sort_date'] = date.min
                else:
                    result['sort_date'] = date.min
            
            # Sort based on the selected column and direction
            reverse_sort = (sort_dir_practice == 'desc')
            if sort_practice == 'date':
                practice_results.sort(key=lambda x: x.get('sort_date', date.min), reverse=reverse_sort)
            elif sort_practice == 'score':
                practice_results.sort(key=lambda x: x.get('total_score', 0), reverse=reverse_sort)

        # Debug: Print what we're passing to the template
        print("\n[DEBUG] ===== Data being passed to template =====")
        print(f"Progress data: {progress_data}")
        print(f"Official scores: {official_scores}")
        print(f"Practice results: {practice_results[:2]}... (showing first 2)")
        print("========================================\n")

        # progress_data already has calculated scores from above

        # Ensure we're passing the data correctly to the template
        # Prepare template data with proper error handling
        template_data = {
            'progress': progress_data,
            'official_scores': official_scores or [],
            'practice_results': practice_results or [],
            'sort_official': sort_official,
            'sort_dir_official': sort_dir_official,
            'sort_practice': sort_practice,
            'sort_dir_practice': sort_dir_practice,
            'superscore': superscore,  # Add the calculated superscore
            'debug_info': {
                'official_scores_type': type(official_scores).__name__,
                'official_scores_length': len(official_scores) if hasattr(official_scores, '__len__') else 'N/A',
                'official_scores_sample': official_scores[:2] if official_scores else []
            }
        }
        # Handle legacy POST for goal (kept for compatibility)
        if request.method == 'POST':
            goal = request.form.get('goal')
            if goal:
                if streaks:
                    # Effective from tomorrow
                    streaks.set_streak_goal(user_id, int(goal))
                else:
                    if username and hasattr(users, 'set_streak_goal_by_username'):
                        users.set_streak_goal_by_username(username, int(goal))
                    else:
                        users.set_streak_goal(user_id, int(goal))
                flash('Streak goal updated!', 'success')
                return redirect(url_for('streak'))

        # Phase 2: Provide server-backed data to streak page
        progress_data = users.get_user_progress(user_id)
        today = date.today()
        # month navigation
        try:
            y = int(request.args.get('year', today.year))
            m = int(request.args.get('month', today.month))
        except Exception:
            y, m = today.year, today.month

        month_start, month_end = (today.replace(day=1), (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1))
        if streaks:
            month_start, month_end = streaks.month_bounds(y, m)
            completed_days = streaks.get_month_streak_days(user_id, month_start, month_end)
            state = streaks.get_streak_state(user_id)
            goal = streaks.get_streak_goal(user_id)
        else:
            completed_days = []
            state = {'current_streak': session.get('current_streak', 0), 'longest_streak': 0, 'last_active_date': None, 'missed_days': 0, 'last_reset_date': None}
            goal_days = None
            if progress_data and isinstance(progress_data, dict):
                goal_days = progress_data.get('streak_goal')
            goal = {'goal_days': (goal_days if goal_days is not None else 7), 'effective_from': today.isoformat()}

        # Render the progress template with the prepared data
        return render_template('progress.html', **template_data)
    return redirect('/login')


@app.route('/streak')
@login_required
def streak():
    """Main streak page showing the user's current streak and calendar."""
    if not is_logged_in(session):
        return redirect('/login')
        
    user_id = session['user_id']
    username = users.get_username_by_user_id(user_id)
    
    # Get user's progress data
    progress_data = users.get_user_progress(user_id)
    
    # Get today's date for the calendar
    today = date.today()
    
    # Get month bounds
    try:
        y = int(request.args.get('year', today.year))
        m = int(request.args.get('month', today.month))
    except Exception:
        y, m = today.year, today.month
    
    # Get streak data
    if hasattr(users, 'get_streak_data'):
        # If using the new streak system
        streak_data = users.get_streak_data(user_id, y, m)
    else:
        # Fallback to basic streak data
        month_start = date(y, m, 1)
        next_month = month_start.replace(day=28) + timedelta(days=4)
        month_end = (next_month - timedelta(days=next_month.day)).replace(day=1) - timedelta(days=1)
        
        # Get completed days (simplified)
        completed_days = []
        if hasattr(users, 'get_completed_days'):
            completed_days = users.get_completed_days(user_id, month_start, month_end)
        
        # Get streak state
        streak_state = {
            'current_streak': progress_data.get('current_streak', 0) if progress_data else 0,
            'longest_streak': progress_data.get('longest_streak', 0) if progress_data else 0,
            'last_active_date': progress_data.get('last_active_date') if progress_data else None
        }
        
        # Get goal
        goal = {
            'goal_days': progress_data.get('streak_goal', 7) if progress_data else 7,
            'effective_from': today.isoformat()
        }
        
        streak_data = {
            'today_iso': today.isoformat(),
            'year': y,
            'month': m,
            'month_start': month_start.isoformat(),
            'month_end': month_end.isoformat(),
            'completed_days': completed_days,
            'state': streak_state,
            'goal': goal
        }
    
    return render_template(
        'streak.html',
        progress=progress_data,
        streak_data=streak_data
    )

@app.route('/streak/goal', methods=['POST'])
def save_streak_goal():
    if not is_logged_in(session):
        return redirect('/login')
    user_id = session['user_id']
    try:
        data = request.get_json(silent=True) or {}
        raw = data.get('goal_days') or request.form.get('goal_days') or request.form.get('goal')
        goal = int(raw)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid goal'}), 400
    if 'streaks' in globals() and streaks:
        streaks.set_streak_goal(user_id, goal)
        return jsonify({'ok': True, 'effective_from': (date.today() + timedelta(days=1)).isoformat()})
    else:
        # Legacy fallback if PG is not configured
        # Prefer username-based logical tables if available
        username = users.get_username_by_user_id(user_id)
        try:
            if username and hasattr(users, 'set_streak_goal_by_username'):
                users.set_streak_goal_by_username(username, goal)
            else:
                users.set_streak_goal(user_id, goal)
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        return jsonify({'ok': True, 'effective_from': (date.today() + timedelta(days=1)).isoformat(), 'note': 'legacy store'})


@app.route('/streak/month', methods=['GET'])
def streak_month():
    if not is_logged_in(session):
        return jsonify({'ok': False, 'error': 'auth'}), 401
    if 'streaks' not in globals() or not streaks:
        return jsonify({'ok': True, 'completed_days': []})
    user_id = session['user_id']
    try:
        y = int(request.args.get('year'))
        m = int(request.args.get('month'))
    except Exception:
        return jsonify({'ok': False, 'error': 'bad params'}), 400
    start, end = streaks.month_bounds(y, m)
    days = streaks.get_month_streak_days(user_id, start, end)
    return jsonify({'ok': True, 'completed_days': days, 'month_start': start.isoformat(), 'month_end': end.isoformat()})


@app.route('/timed')
@require_verified
def timed():
    if is_logged_in(session):
        return render_template('timed.html')
    return redirect('/login')


@app.route('/quests')
@require_verified
def quests():
    if is_logged_in(session):
        user_id = session['user_id']
        daily_quests = users.get_daily_quests(user_id)
        return render_template('quests.html', quests=daily_quests)
    return redirect('/login')


@app.route('/reset_quests', methods=['POST'])

@require_verified
def reset_quests():
    if is_logged_in(session):
        user_id = session['user_id']
        try:
            users.reset_daily_quests(user_id)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': 'Not logged in'})

@app.route('/vocabulary')
@require_verified
def vocabulary():
    if is_logged_in(session):
        user_id = session['user_id']
        vocab_stats = users.get_vocabulary_stats(user_id)
        return render_template('vocabulary.html', vocab_stats=vocab_stats)
    return redirect('/login')


@app.route('/vocabulary_review')
@require_verified
def vocabulary_review():
    if is_logged_in(session):
        user_id = session['user_id']
        review_list = users.get_vocabulary_review_list(user_id)
        return render_template('vocabulary_review.html', review_list=review_list)
    return redirect('/login')


@app.route('/profile', methods=['GET', 'POST'])
@require_verified
def profile():
    if is_logged_in(session):
        user_id = session['user_id']

        if request.method == 'POST':
            # Update profile
            first_name = request.form.get('firstName')
            last_name = request.form.get('lastName')
            nickname = request.form.get('nickname')
            birth_date = request.form.get('birthDate')
            account_type = request.form.get('accountType', 'private')

            users.update_user_profile(user_id, first_name, last_name, nickname, birth_date, account_type)

            # Update session data
            session['first_name'] = first_name

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))

        # Get user profile data
        profile_data = users.get_user_profile(user_id)
        progress_data = users.get_user_progress(user_id)

        return render_template('profile.html',
                               profile=profile_data,
                               progress=progress_data,
                               today=get_today_date())
    return redirect('/login')


# Register settings blueprint (decomposed from inline routes)
settings_bp = create_settings_blueprint(users, is_logged_in)
app.register_blueprint(settings_bp)


@app.route('/ebrw_info')
def ebrw_info():
    if is_logged_in(session):
        return render_template('ebrw_info.html')
    return redirect('/login')


def get_questions_by_criteria(skill=None, domain=None, difficulty=None, limit=None, exclude_ids=None):
    """Get questions from database matching specific criteria."""
    import sqlite3
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), 'question_bank.db')
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        query = "SELECT * FROM QUESTIONS WHERE Domain NOT LIKE '%Math%'"
        params = []
        
        if skill:
            query += " AND Skill = ?"
            params.append(skill)
        if domain:
            query += " AND Domain = ?"
            params.append(domain)
        if difficulty:
            if isinstance(difficulty, list):
                placeholders = ','.join(['?'] * len(difficulty))
                query += f" AND Difficulty IN ({placeholders})"
                params.extend(difficulty)
            else:
                query += " AND Difficulty = ?"
                params.append(difficulty)
        if exclude_ids:
            # Convert dbid:123 format to just 123 for database query
            db_exclude_ids = []
            for eid in exclude_ids:
                if eid.startswith('dbid:'):
                    db_exclude_ids.append(eid[5:])  # Remove 'dbid:' prefix
                else:
                    db_exclude_ids.append(eid)
            
            placeholders = ','.join(['?'] * len(db_exclude_ids))
            query += f" AND id NOT IN ({placeholders})"
            params.extend(db_exclude_ids)
        
        query += " ORDER BY id"  # Use deterministic ordering instead of RANDOM()
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Convert to question dict format
        questions = []
        for row in rows:
            options = [row['Option1'], row['Option2'], row['Option3'], row['Option4']]
            correct_text = None
            if row['Correct'] and row['Correct'].strip().upper() in ['A', 'B', 'C', 'D']:
                idx = ord(row['Correct'].strip().upper()) - ord('A')
                if 0 <= idx < 4:
                    correct_text = options[idx]
            else:
                correct_text = row['Correct']
            
            qid = f"dbid:{row['id']}"  # Always use database ID for consistency
            questions.append({
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
            })
        
        return questions


def build_ebrw_test_questions(part=1, part1_performance=None, seed=None):
    """Build a set of 27 questions for EBRW test according to specifications.
    
    Part 1: Easy and Medium questions
    Part 2: Medium and Hard (or Easy if Part 1 was bad)
    
    Structure:
    - Questions 1-5: Vocabulary (from LESSON1_QUESTIONS)
    - Question 6: Word in Context
    - Question 7: Function of Sentence
    - Questions 8-15: Other types (various)
    - Questions 16-22: Standard English Conventions
    - Questions 23-26: Transitions or Student Notes (Rhetorical Synthesis)
    """
    # Use deterministic random if seed provided
    if seed is not None:
        random.seed(seed)
    
    questions = []
    used_vocab_ids = []
    used_db_ids = []
    
    # Questions 1-5: Vocabulary
    vocab_questions = random.sample(LESSON1_QUESTIONS, min(5, len(LESSON1_QUESTIONS)))
    for vq in vocab_questions:
        vq_copy = vq.copy()
        vq_copy['question_id'] = f"vocab_{len(questions) + 1}"
        questions.append(vq_copy)
        used_vocab_ids.append(vq_copy['question_id'])
    
    # Question 6: Word in Context
    word_in_context = get_questions_by_criteria(
        skill='Words in Context',
        difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
        limit=1,
        exclude_ids=used_db_ids
    )
    if word_in_context:
        questions.append(word_in_context[0])
        used_db_ids.append(word_in_context[0]['question_id'])
    else:
        # Fallback to any Words in Context
        word_in_context = get_questions_by_criteria(skill='Words in Context', limit=1)
        if word_in_context:
            questions.append(word_in_context[0])
            used_db_ids.append(word_in_context[0]['question_id'])
    
    # Question 7: Function of Sentence (Text Structure and Purpose)
    function_q = get_questions_by_criteria(
        skill='Text Structure and Purpose',
        difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
        limit=1,
        exclude_ids=used_db_ids
    )
    if function_q:
        questions.append(function_q[0])
        used_db_ids.append(function_q[0]['question_id'])
    else:
        # Fallback
        function_q = get_questions_by_criteria(skill='Text Structure and Purpose', limit=1)
        if function_q:
            questions.append(function_q[0])
            used_db_ids.append(function_q[0]['question_id'])
    
    # Questions 8-15: Other types (various)
    other_types = ['Inferences', 'Central Ideas and Details', 'Command of Evidence', 'Cross-Text Connections']
    needed = 8
    for skill_type in other_types:
        if needed <= 0:
            break
        qs = get_questions_by_criteria(
            skill=skill_type,
            difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
            limit=min(2, needed),
            exclude_ids=used_db_ids
        )
        for q in qs:
            questions.append(q)
            used_db_ids.append(q['question_id'])
            needed -= 1
    
    # Fill remaining with any available questions
    if needed > 0:
        remaining = get_questions_by_criteria(
            difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
            limit=needed,
            exclude_ids=used_db_ids
        )
        questions.extend(remaining)
        used_db_ids.extend([q['question_id'] for q in remaining])
    
    # Questions 16-22: Standard English Conventions
    sec_questions = get_questions_by_criteria(
        domain='Standard English Conventions',
        difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
        limit=7,
        exclude_ids=used_db_ids
    )
    questions.extend(sec_questions)
    used_db_ids.extend([q['question_id'] for q in sec_questions])
    
    # Questions 23-26: Transitions or Rhetorical Synthesis
    transition_qs = get_questions_by_criteria(
        skill='Transitions',
        difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
        limit=2,
        exclude_ids=used_db_ids
    )
    questions.extend(transition_qs)
    used_db_ids.extend([q['question_id'] for q in transition_qs])
    
    synthesis_qs = get_questions_by_criteria(
        skill='Rhetorical Synthesis',
        difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
        limit=2,
        exclude_ids=used_db_ids
    )
    questions.extend(synthesis_qs)
    used_db_ids.extend([q['question_id'] for q in synthesis_qs])
    
    # Ensure we have exactly 27 questions
    while len(questions) < 27:
        remaining = get_questions_by_criteria(
            difficulty=['Easy', 'Medium'] if part == 1 else ['Medium', 'Hard'],
            limit=27 - len(questions),
            exclude_ids=used_db_ids
        )
        if not remaining:
            break
        questions.extend(remaining)
        used_db_ids.extend([q['question_id'] for q in remaining])
    
    return questions[:27]  # Return exactly 27


@app.route('/ebrw_practice/start')
def ebrw_practice_start():
    """Initialize EBRW practice test."""
    if not is_logged_in(session):
        return redirect('/login')
    
    # Initialize test session
    session['ebrw_test_part'] = 1
    session['ebrw_test_questions'] = []  # Initialize as empty list, not None
    session['ebrw_test_answers'] = {}
    session['ebrw_test_marked'] = []  # Use list instead of set for JSON serialization
    session['ebrw_test_start_time'] = None
    session['ebrw_test_paused'] = False
    session['ebrw_test_elapsed'] = 0
    session['ebrw_part1_performance'] = None
    
    return redirect(url_for('ebrw_practice_part', part=1))


@app.route('/ebrw_practice/part<int:part>')
def ebrw_practice_part(part):
    """Display EBRW practice test part."""
    print(f"[DEBUG] ebrw_practice_part called with part={part}")
    
    if not is_logged_in(session):
        print("[DEBUG] User not logged in")
        return redirect('/login')
    
    if part not in [1, 2]:
        print(f"[DEBUG] Invalid part: {part}")
        return redirect(url_for('ebrw_info'))
    
    # Check session state
    questions = session.get('ebrw_test_questions', [])
    current_part = session.get('ebrw_test_part')
    print(f"[DEBUG] Session state - questions: {len(questions) if questions else 'None'}, part: {current_part}")
    
    # Initialize questions if not set
    if not questions or len(questions) == 0 or current_part != part:
        print(f"[DEBUG] Initializing questions - condition triggered")
        part1_perf = session.get('ebrw_part1_performance')
        
        # Create deterministic seed based on user session
        user_id = session.get('user_id', 'anonymous')
        seed = hash(f"{user_id}_ebrw_part{part}") % 1000000
        print(f"[DEBUG] Using seed: {seed}")
        
        questions = build_ebrw_test_questions(part=part, part1_performance=part1_perf, seed=seed)
        session['ebrw_test_questions'] = [q.get('question_id') for q in questions]
        print(f"[DEBUG] Built {len(session['ebrw_test_questions'])} questions")
        # CRITICAL: Don't store full question data in session - causes cookie size issues
        # session['ebrw_test_question_data'] = {q['question_id']: q for q in questions}
        session['ebrw_test_part'] = part
        session['ebrw_test_answers'] = {}
        session['ebrw_test_marked'] = []  # Use list instead of set for JSON serialization
        if not session.get('ebrw_test_start_time'):
            session['ebrw_test_start_time'] = datetime.now().isoformat()
        # Preserve elapsed time and pause state when switching parts
        if 'ebrw_test_elapsed' not in session:
            session['ebrw_test_elapsed'] = 0
        if 'ebrw_test_paused' not in session:
            session['ebrw_test_paused'] = False
    else:
        print(f"[DEBUG] Using existing session data")
    
    qids = session.get('ebrw_test_questions', [])
    print(f"[DEBUG] Final qids: {len(qids)} questions")
    
    # CRITICAL: Rebuild question data from IDs instead of storing in session
    # question_data = session.get('ebrw_test_question_data', {})
    part1_perf = session.get('ebrw_part1_performance')
    
    # Use the same seed for consistent question building
    user_id = session.get('user_id', 'anonymous')
    seed = hash(f"{user_id}_ebrw_part{part}") % 1000000
    all_questions = build_ebrw_test_questions(part=part, part1_performance=part1_perf, seed=seed)
    question_data = {q['question_id']: q for q in all_questions}
    
    # Get current question index
    current_q = int(request.args.get('q', 1))
    print(f"[DEBUG] Requested question: {current_q}")
    if current_q < 1:
        current_q = 1
    elif current_q > len(qids):
        current_q = len(qids)
    
    current_qid = qids[current_q - 1] if qids else None
    question = question_data.get(current_qid) if current_qid else None
    
    print(f"[DEBUG] Final check - qid: {current_qid}, question found: {question is not None}")
    
    if not question:
        print(f"[DEBUG] Question not found, creating fallback question")
        print(f"[DEBUG] Session qids: {qids[:5]}...{qids[-5:] if len(qids) > 5 else ''}")
        print(f"[DEBUG] Available question_data keys: {list(question_data.keys())[:5]}...{list(question_data.keys())[-5:] if len(question_data.keys()) > 5 else ''}")
        
        # Create a fallback question instead of redirecting
        question = {
            'question_id': current_qid or f'question_{current_q}',
            'question': f'Question {current_q}',
            'text': f'This is question {current_q}. The original question data could not be loaded.',
            'options': ['Option A', 'Option B', 'Option C', 'Option D'],
            'answer': 'Option A',
            'explanation': 'This is a fallback question.',
            'difficulty': 'Medium',
            'domain': 'General',
            'skill': 'General'
        }
        print(f"[DEBUG] Created fallback question for: {current_qid}")
    
    # Get stored answer if exists
    answers_dict = session.get('ebrw_test_answers', {})
    if not isinstance(answers_dict, dict):
        answers_dict = {}
        session['ebrw_test_answers'] = answers_dict
    selected_option = answers_dict.get(current_qid) if current_qid else None
    
    marked_list = session.get('ebrw_test_marked', [])
    if not isinstance(marked_list, list):
        marked_list = list(marked_list) if marked_list else []
        session['ebrw_test_marked'] = marked_list
    is_marked = current_qid in marked_list if current_qid else False
    
    # Prepare options (shuffle if needed)
    options = question.get('options', [])
    if question.get('shuffle_options', True):
        # Use deterministic shuffle based on question_id
        import hashlib
        seed = int(hashlib.md5(current_qid.encode()).hexdigest()[:8], 16)
        rnd = random.Random(seed)
        opts = options.copy()
        rnd.shuffle(opts)
        options = opts
    
    return render_template('ebrw_practice.html',
                         question=question,
                         options=options,
                         current_q=current_q,
                         total_q=len(qids),
                         part=part,
                         selected_option=selected_option,
                         is_marked=is_marked,
                         answers=session.get('ebrw_test_answers', {}),
                         show_leave=True,
                         leave_url=url_for('ebrw_info'),
                         hide_chrome=True)


@app.route('/ebrw_practice/answer', methods=['POST'])
def ebrw_practice_answer():
    """Handle answer submission for EBRW practice."""
    if not is_logged_in(session):
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    question_id = request.form.get('question_id')
    answer = request.form.get('answer')
    current_q = int(request.form.get('current_q', 1))
    
    if not question_id:
        return jsonify({'status': 'error', 'message': 'Missing question_id'})
    
    # Store answer
    if 'ebrw_test_answers' not in session:
        session['ebrw_test_answers'] = {}
    session['ebrw_test_answers'][question_id] = answer
    session.modified = True
    
    return jsonify({'status': 'success', 'current_q': current_q})


@app.route('/ebrw_practice/mark', methods=['POST'])
def ebrw_practice_mark():
    """Mark/unmark a question for review."""
    if not is_logged_in(session):
        return jsonify({'status': 'error'})
    
    question_id = request.form.get('question_id')
    marked = request.form.get('marked', 'false').lower() == 'true'
    
    if 'ebrw_test_marked' not in session:
        session['ebrw_test_marked'] = []
    
    # Ensure it's a list (handle case where it might be a set from old session)
    marked_list = session.get('ebrw_test_marked', [])
    if not isinstance(marked_list, list):
        marked_list = list(marked_list) if marked_list else []
        session['ebrw_test_marked'] = marked_list
    
    if marked:
        if question_id not in marked_list:
            marked_list.append(question_id)
    else:
        if question_id in marked_list:
            marked_list.remove(question_id)
    
    session['ebrw_test_marked'] = marked_list
    session.modified = True
    return jsonify({'status': 'success'})


@app.route('/ebrw_practice/save_time', methods=['POST'])
def ebrw_practice_save_time():
    """Save elapsed time and pause state for timer persistence."""
    if not is_logged_in(session):
        return jsonify({'status': 'error'})
    
    data = request.get_json() or {}
    elapsed = data.get('elapsed', session.get('ebrw_test_elapsed', 0))
    paused = data.get('paused', session.get('ebrw_test_paused', False))
    
    session['ebrw_test_elapsed'] = elapsed
    session['ebrw_test_paused'] = paused
    session.modified = True
    return jsonify({'status': 'success'})


@app.route('/ebrw_practice/submit', methods=['POST'])
def ebrw_practice_submit():
    """Submit EBRW practice test and calculate score."""
    if not is_logged_in(session):
        return redirect('/login')
    
    user_id = session.get('user_id')
    part = session.get('ebrw_test_part', 1)
    qids = session.get('ebrw_test_questions', [])
    # CRITICAL: Rebuild question data from IDs instead of storing in session
    # question_data = session.get('ebrw_test_question_data', {})
    part1_perf = session.get('ebrw_part1_performance')
    
    # Use the same seed for consistent question building
    user_id = session.get('user_id', 'anonymous')
    seed = hash(f"{user_id}_ebrw_part{part}") % 1000000
    all_questions = build_ebrw_test_questions(part=part, part1_performance=part1_perf, seed=seed)
    question_data = {q['question_id']: q for q in all_questions}
    answers = session.get('ebrw_test_answers', {})
    
    # Calculate score for this part
    correct = 0
    total = len(qids)
    errors = []
    
    for qid in qids:
        question = question_data.get(qid)
        if not question:
            continue
        
        user_answer = answers.get(qid)
        correct_answer = question.get('answer')
        
        is_correct = (user_answer == correct_answer) if user_answer and correct_answer else False
        
        if is_correct:
            correct += 1
        else:
            errors.append({
                'question_id': qid,
                'question': question.get('question', ''),
                'text': question.get('text', ''),
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'explanation': question.get('explanation', ''),
                'options': question.get('options', []),
                'domain': question.get('domain', ''),
                'skill': question.get('skill', ''),
                'difficulty': question.get('difficulty', '')
            })
    
    score = correct
    percentage = (correct / total * 100) if total > 0 else 0
    
    # Store part 1 performance for part 2 difficulty adjustment
    if part == 1:
        session['ebrw_part1_performance'] = percentage
        # Store results temporarily
        session['ebrw_part1_results'] = {
            'correct': correct,
            'total': total,
            'score': score,
            'percentage': percentage,
            'errors': errors
        }
        return redirect(url_for('ebrw_practice_part', part=2))
    else:
        # Part 2 complete - calculate final score
        part1_results = session.get('ebrw_part1_results', {})
        part1_correct = part1_results.get('correct', 0)
        part1_total = part1_results.get('total', 0)
        
        total_correct = part1_correct + correct
        total_questions = part1_total + total
        total_percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        # Calculate EBRW score (scale 200-800)
        # Rough conversion: 100% = 800, 0% = 200
        ebrw_score = max(200, min(800, 200 + int((total_percentage / 100) * 600)))
        
        # Store test results
        all_errors = part1_results.get('errors', []) + errors
        
        # Save to database
        try:
            from datetime import date
            test_date = date.today().isoformat()
            
            # Insert practice result
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                INSERT INTO practice_results (UserID, PracticeName, PracticeDate, Score, EBRWScore, MathScore, MaxScore, PracticeType)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, 'EBRW Full-Length Practice', test_date, total_correct, ebrw_score, math_score, total_questions, 'ebrw_practice')
            )
            
            # Update user_progress with test score
            total_score = ebrw_score + math_score  # Use actual math_score, not hardcoded 800
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                INSERT INTO user_progress (UserID, TotalScore, EBRWScore, MathScore)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(UserID) DO UPDATE SET
                    TotalScore=excluded.TotalScore,
                    EBRWScore=excluded.EBRWScore,
                    MathScore=excluded.MathScore
                """,
                (user_id, total_score, ebrw_score, math_score)
            )
            
            # Update session scores
            session['total_score'] = total_score
            session['ebrw_score'] = ebrw_score
            session['math_score'] = math_score
            
        except Exception as e:
            print(f"[ERROR] Failed to save EBRW test results: {e}")
            import traceback
            traceback.print_exc()
        
        # Store results in session for results page
        session['ebrw_test_results'] = {
            'part1_correct': part1_correct,
            'part1_total': part1_total,
            'part2_correct': correct,
            'part2_total': total,
            'total_correct': total_correct,
            'total_questions': total_questions,
            'percentage': total_percentage,
            'ebrw_score': ebrw_score,
            'errors': all_errors
        }
        
        # Clear test session
        session.pop('ebrw_test_questions', None)
        session.pop('ebrw_test_question_data', None)  # Clear this too
        session.pop('ebrw_test_answers', None)
        session.pop('ebrw_test_marked', None)
        session.pop('ebrw_test_part', None)
        session.pop('ebrw_part1_results', None)
        session.pop('ebrw_part1_performance', None)
        
        return redirect(url_for('ebrw_practice_results'))


@app.route('/ebrw_practice/results')
def ebrw_practice_results():
    """Display EBRW practice test results."""
    if not is_logged_in(session):
        return redirect('/login')
    
    results = session.get('ebrw_test_results')
    if not results:
        return redirect(url_for('ebrw_info'))
    
    return render_template('ebrw_results.html', results=results)


@app.route('/lesson')
def lesson():
    # Accept parameters from lessons.html but ignore them for legacy behavior
    difficulty = request.args.get('difficulty')
    domain = request.args.get('domain') 
    skill = request.args.get('skill')
    lesson_type = request.args.get('type')
    practice_index = request.args.get('practice_index')
    
    # Debug: Log the received parameters
    print(f"[DEBUG] lesson() called with params: difficulty={difficulty}, domain={domain}, skill={skill}, type={lesson_type}, practice_index={practice_index}")
    
    # Generate lesson title based on parameters
    lesson_title = "Practice"
    if lesson_type == 'theory':
        lesson_title = "Theory Lesson"
    elif lesson_type == 'mastery':
        lesson_title = "Mastery Test"
    elif lesson_type == 'practice' and practice_index:
        lesson_title = f"Practice {practice_index}"
    elif difficulty and domain and skill:
        # Fallback: construct from parameters
        lesson_title = f"{difficulty.title()} {domain.title()} - {skill.title()}"
    
    print(f"[DEBUG] Generated lesson title: {lesson_title}")
    
    # Store lesson title in session for persistence across requests
    session['lesson_title'] = lesson_title
    
    if not is_logged_in(session):
        return redirect('/login')
    
    # Handle theory lessons differently - they use their own template and logic
    if lesson_type == 'theory':
        user_id = session.get('user_id')
        score_data = calculate_ebrw_score(user_id)
        
        # Update session with latest scores for header display
        try:
            progress_data = users.get_user_progress(user_id)
            if progress_data:
                session['total_score'] = progress_data.get('total_score', 0)
                session['ebrw_score'] = progress_data.get('ebrw_score', 0)
                session['math_score'] = progress_data.get('math_score', 0)
        except Exception as e:
            print(f"[ERROR] Failed to update session scores: {e}")
        
        # Get practice examples for theory lesson
        practice_examples = []
        try:
            qb.ensure_ready()
            # Get 2 example questions for the theory lesson
            example_questions = qb.get_random_questions(limit=2)
            practice_examples = example_questions if example_questions else []
        except Exception as e:
            print(f"[ERROR] Failed to get practice examples: {e}")
        
        return render_template('theory_lesson.html',
                               difficulty=difficulty or 'medium',
                               domain=domain or 'Reading',
                               skill=skill or 'Main Idea',
                               practice_examples=practice_examples,
                               score_data=score_data,
                               lesson_title=lesson_title)
    
    # Continue with legacy lesson logic for practice and mastery lessons
    user_id = session.get('user_id')
    
    # Calculate user's EBRW score
    score_data = calculate_ebrw_score(user_id)
    
    # Update session with latest scores for header display
    try:
        progress_data = users.get_user_progress(user_id)
        if progress_data:
            session['total_score'] = progress_data.get('total_score', 1600)
            session['ebrw_score'] = progress_data.get('ebrw_score', 800)
            session['math_score'] = progress_data.get('math_score', 800)
    except Exception as e:
        print(f"[ERROR] Failed to update session scores: {e}")
    
    # Debug: Check question bank status
    print("[DEBUG] Question bank ensure_ready():")
    try:
        available = qb.ensure_ready()
        print(f"[DEBUG] Question bank reports {available} questions available")
        if available > 0:
            test_q = qb.get_random_questions(limit=1)
            print(f"[DEBUG] Test question fetch: {len(test_q) if test_q else 0} questions")
            if test_q:
                print(f"[DEBUG] Sample question keys: {test_q[0].keys()}")
    except Exception as e:
        print(f"[ERROR] Question bank check failed: {str(e)}")
        available = 0

    # Initialize question bank and session (store only IDs to keep session small)
    qb.ensure_ready()
    
    # Check if we should start a new lesson
    question_param = request.args.get('question')
    start_new = request.args.get('new', '').lower() == 'true'
    
    # If no question parameter in URL, treat as starting fresh (reset to question 1)
    # This ensures that navigating to /lesson always starts at question 1
    if not question_param or start_new:
        # Start a new lesson - get 10 random questions
        qs = qb.get_random_questions(limit=10) or []
        qids = [q.get('question_id') for q in qs if q.get('question_id')]
        session['lesson_qids'] = qids
        session['lesson_option_orders'] = {}
        session['lesson_current_question'] = 0
        session['lesson_quiz_score'] = 0
        session['lesson_answered'] = False
        session['lesson_selected_option'] = None
        session['lesson_selected_pairs'] = None
        # Clear any per-question answered flags
        for key in list(session.keys()):
            if key.startswith('lesson_q_') and key.endswith('_answered'):
                del session[key]
    elif not session.get('lesson_qids'):
        # If we have a question parameter but no lesson_qids, initialize
        qs = qb.get_random_questions(limit=10) or []
        qids = [q.get('question_id') for q in qs if q.get('question_id')]
        session['lesson_qids'] = qids
        session['lesson_option_orders'] = {}
        session['lesson_current_question'] = 0
        session['lesson_quiz_score'] = 0
        session['lesson_answered'] = False
        session['lesson_selected_option'] = None
        session['lesson_selected_pairs'] = None

    qids = session.get('lesson_qids', [])
    questions = qb.get_questions_by_ids(qids) if qids else []
    
    # Get the current question index from the URL if present, otherwise use session
    if question_param and question_param.isdigit():
        # URL parameter is 1-based, convert to 0-based index
        current_question_index = max(0, min(int(question_param) - 1, len(questions) - 1)) if questions else 0
        session['lesson_current_question'] = current_question_index
    else:
        # No question parameter - start at question 1 (index 0)
        current_question_index = 0
        session['lesson_current_question'] = 0
    
    question = questions[current_question_index] if questions else None

    if question:
        # Ensure we have the question text in the expected field
        if 'question' not in question and 'text' in question:
            question['question'] = question['text']
            
        if question.get('type') == 'pairs_matching':
            # For pairs matching, we need to prepare shuffled words and definitions
            words = [pair['word'] for pair in question['pairs']]
            definitions = [pair['definition'] for pair in question['pairs']]
            random.shuffle(words)
            random.shuffle(definitions)

            return render_template('lesson.html',
                               question=question,
                               quiz_complete=False,
                               score=session.get('lesson_quiz_score', 0),
                               total_questions=len(questions),
                               options=None,
                               answered=session.get('lesson_answered', False),
                               feedback=None,
                               correct_answer=None,
                               selected_option=None,
                               current_index=current_question_index,
                               questions=questions,
                               task_text=question.get('text', ''),
                               show_leave=True,
                               leave_url=url_for('lessons'),
                               words=words,
                               definitions=definitions,
                               score_data=score_data,  # Pass score data to template
                               lesson_title=lesson_title)  # Pass lesson title
        else:
            # For regular questions, ensure we have options
            options = question.get('options', [])
            if not options and 'options' in question and isinstance(question['options'], list):
                options = question['options']
            
            # Shuffle options if needed and store the order in session
            orders = session.get('lesson_option_orders') or {}
            key = str(current_question_index)
            if question.get('shuffle_options', True):
                if key not in orders:
                    # Shuffle and store the order
                    options = _stable_shuffled_options(question)
                    orders[key] = options
                    session['lesson_option_orders'] = orders
                else:
                    # Use the stored order
                    options = orders[key]
            else:
                options = question.get('options', [])
            
            return render_template('lesson.html',
                               question=question,
                               options=options,
                               current_index=current_question_index,
                               total_questions=len(questions),
                               score=session.get('lesson_quiz_score', 0),
                               answered=False,
                               feedback=None,
                               correct_answer=question.get('answer'),
                               selected_option=None,
                               show_leave=True,
                               leave_url=url_for('lessons'),
                               score_data=score_data,  # Pass score data to template
                               lesson_title=lesson_title)  # Pass lesson title

    # Debug output for empty questions
    print(f"[DEBUG] No questions found in route. Available: {available}, Cached: {len(questions) if questions else 0}")
    if not questions and available > 0:
        print("[DEBUG] Attempting direct question fetch...")
        try:
            _qs = qb.get_random_questions(limit=None) or []
            print(f"[DEBUG] Direct fetch returned {len(_qs)} questions")
            if _qs:
                # Enforce 10-question set (trim only)
                if len(_qs) > 10:
                    _qs = _qs[:10]
                questions = _qs
                session['lesson_qids'] = [q.get('question_id') for q in _qs if q.get('question_id')]
                qids = session.get('lesson_qids', [])
                questions = qb.get_questions_by_ids(qids) if qids else []
        except Exception as e:
            print(f"[ERROR] Direct fetch failed: {str(e)}")

    # If still no questions, use a default
    if not questions:
        questions = [{
            'type': 'multiple_choice',
            'question': 'No questions available in the question bank.',
            'options': ['Please add questions to the database.'],
            'answer': 0,
            'question_id': 'default_1'
        }]
        session['lesson_qids'] = [q.get('question_id') for q in questions if q.get('question_id')]

    # Ensure we have a valid current question (default to 0 if not set or out of bounds)
    current_question_index = max(0, min(session.get('lesson_current_question', 0), len(questions) - 1)) if questions else 0
    session['lesson_current_question'] = current_question_index
    question = questions[current_question_index] if questions else None
    
    # Calculate score data for the user
    user_id = session.get('user_id')
    score_data = calculate_ebrw_score(user_id)
    
    return render_template(
        'lesson.html',
        quiz_complete=False,
        score=session.get('lesson_quiz_score', 0),
        total_questions=len(questions),
        question=question,
        options=question.get('options', []) if question else [],
        answered=False,
        feedback=None,
        correct_answer=question.get('answer') if question else None,
        selected_option=None,
        current_index=current_question_index,
        questions=questions,  # Pass full list for debug
        task_text=f"Question {current_question_index + 1} of {len(questions)}",
        show_leave=True,
        leave_url=url_for('lessons'),
        score_data=score_data,  # Add score data to template context
        lesson_title=lesson_title  # Pass lesson title
    )


@app.route('/lesson_answer', methods=['POST'])
def lesson_answer():
    # Generate lesson title based on session or request parameters
    lesson_title = session.get('lesson_title', 'Practice')
    if not lesson_title or lesson_title == 'Practice':
        # Try to get from request parameters (for direct navigation)
        difficulty = request.args.get('difficulty') or request.form.get('difficulty')
        domain = request.args.get('domain') or request.form.get('domain')
        skill = request.args.get('skill') or request.form.get('skill')
        lesson_type = request.args.get('type') or request.form.get('type')
        practice_index = request.args.get('practice_index') or request.form.get('practice_index')
        
        if lesson_type == 'theory':
            lesson_title = "Theory Lesson"
        elif lesson_type == 'mastery':
            lesson_title = "Mastery Test"
        elif lesson_type == 'practice' and practice_index:
            lesson_title = f"Practice {practice_index}"
        elif difficulty and domain and skill:
            lesson_title = f"{difficulty.title()} {domain.title()} - {skill.title()}"
        
        # Store in session for future use
        session['lesson_title'] = lesson_title
    
    if is_logged_in(session):
        user_id = session.get('user_id')
        # Ensure session state exists
        if not session.get('lesson_qids'):
            return redirect(url_for('lesson'))
        qids = session.get('lesson_qids', [])
        questions = qb.get_questions_by_ids(qids) if qids else []
        # Respect posted index to evaluate the right question
        try:
            current_question_index = int(request.form.get('q_index', session.get('lesson_current_question', 0)))
        except Exception:
            current_question_index = session.get('lesson_current_question', 0)
        if current_question_index < 0 or current_question_index >= len(questions):
            current_question_index = 0
        session['lesson_current_question'] = current_question_index

        current_question = questions[current_question_index]

        if current_question.get('type') == 'pairs_matching':
            # Handle pairs matching
            selected_pairs = {}
            correct_count = 0
            total_pairs = len(current_question['pairs'])
            for pair in current_question['pairs']:
                w = pair['word']
                sel = request.form.get(f'pair_{w}')
                selected_pairs[w] = sel
                if sel == pair['definition']:
                    correct_count += 1
            is_correct = (correct_count >= total_pairs - 1)
            if is_correct:
                session['lesson_quiz_score'] += 1
            session['lesson_answered'] = True
            session['lesson_selected_pairs'] = selected_pairs
            
            # Store answer in database
            try:
                user_id = session.get('user_id')
                users.execute_sql(
                    users.PROGRESS_KEY,
                    """
                    INSERT INTO lesson_history (UserID, QuestionID, QuestionType, Domain, Difficulty, IsCorrect)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        current_question.get('question_id', ''),
                        'pairs_matching',
                        current_question.get('domain', ''),
                        current_question.get('difficulty', 'medium'),
                        1 if is_correct else 0
                    )
                )
                
                # Immediately update score if answer is wrong (English questions only)
                if not is_correct:
                    domain = current_question.get('domain', '').lower()
                    # Only update for English questions (exclude Math)
                    is_english = ('reading' in domain or 'writing' in domain or 
                                 (domain and 'math' not in domain) or not domain)
                    if is_english:
                        # Recalculate score
                        score_data = calculate_ebrw_score(user_id)
                        ebrw_score = score_data['score']
                        math_score = 800  # Keep math constant
                        total_score = ebrw_score + math_score
                        
                        # Update database
                        users.execute_sql(
                            users.PROGRESS_KEY,
                            """
                            INSERT INTO user_progress (UserID, EBRWScore, MathScore, TotalScore)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(UserID) DO UPDATE SET
                                EBRWScore=excluded.EBRWScore,
                                MathScore=excluded.MathScore,
                                TotalScore=excluded.TotalScore
                            """,
                            (user_id, ebrw_score, math_score, total_score)
                        )
                        
                        # Update session immediately
                        session['total_score'] = total_score
                        session['ebrw_score'] = ebrw_score
                        session['math_score'] = math_score
            except Exception as e:
                print(f"[ERROR] Failed to store lesson answer: {str(e)}")
            if is_correct:
                if correct_count == total_pairs:
                    explanation_msg = f"Perfect! All {total_pairs} pairs matched correctly."
                else:
                    explanation_msg = f"Good job! You got {correct_count} out of {total_pairs} pairs correct. One mistake is allowed."
            else:
                explanation_msg = f"Try again! You got {correct_count} out of {total_pairs} pairs correct. Only one mistake is allowed."
            feedback = {'is_correct': is_correct, 'explanation': explanation_msg, 'selected_pairs': selected_pairs}
            words = [p['word'] for p in current_question['pairs']]
            definitions = [p['definition'] for p in current_question['pairs']]
            shown_options = []
            correct_answer = None
            selected_option = None
        else:
            # Multiple choice
            selected_option = request.form.get('selected_option') or ''
            raw_correct = current_question.get('answer')
            correct_answer = raw_correct
            # Normalize whitespace and quotes for comparison
            def _n(s):
                return (s or '').strip().replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
            is_correct = (_n(selected_option).casefold() == _n(correct_answer).casefold()) if (selected_option and correct_answer) else False
            # Increment only once per question index
            q_flag = f'lesson_q_{current_question_index}_answered'
            if is_correct and not session.get(q_flag):
                session[q_flag] = True
                session['lesson_quiz_score'] = session.get('lesson_quiz_score', 0) + 1
            session['lesson_answered'] = True
            session['lesson_selected_option'] = selected_option
            
            # Store answer in database
            try:
                users.execute_sql(
                    users.PROGRESS_KEY,
                    """
                    INSERT INTO lesson_history (UserID, QuestionID, QuestionType, Domain, Difficulty, IsCorrect)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        current_question.get('question_id', ''),
                        current_question.get('type', 'multiple_choice'),
                        current_question.get('domain', ''),
                        current_question.get('difficulty', 'medium'),
                        1 if is_correct else 0
                    )
                )
                
                # Immediately update score if answer is wrong (English questions only)
                if not is_correct:
                    domain = current_question.get('domain', '').lower()
                    # Only update for English questions (exclude Math)
                    is_english = ('reading' in domain or 'writing' in domain or 
                                 (domain and 'math' not in domain) or not domain)
                    if is_english:
                        # Recalculate score
                        score_data = calculate_ebrw_score(user_id)
                        ebrw_score = score_data['score']
                        math_score = 800  # Keep math constant
                        total_score = ebrw_score + math_score
                        
                        # Update database
                        users.execute_sql(
                            users.PROGRESS_KEY,
                            """
                            INSERT INTO user_progress (UserID, EBRWScore, MathScore, TotalScore)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(UserID) DO UPDATE SET
                                EBRWScore=excluded.EBRWScore,
                                MathScore=excluded.MathScore,
                                TotalScore=excluded.TotalScore
                            """,
                            (user_id, ebrw_score, math_score, total_score)
                        )
                        
                        # Update session immediately
                        session['total_score'] = total_score
                        session['ebrw_score'] = ebrw_score
                        session['math_score'] = math_score
            except Exception as e:
                print(f"[ERROR] Failed to store lesson answer: {str(e)}")
            # Prepare options in the same order as initial display
            orders = session.get('lesson_option_orders') or {}
            key = str(current_question_index)
            shown_options = orders.get(key, current_question.get('options', []))
            feedback = {'is_correct': is_correct, 'explanation': current_question.get('explanation', '')}
            words = []
            definitions = []

        # Render evaluation (include score_data for header)
        user_id = session.get('user_id')
        score_data = calculate_ebrw_score(user_id)
        
        # Update session with latest scores for header display
        try:
            progress_data = users.get_user_progress(user_id)
            if progress_data:
                session['total_score'] = progress_data.get('total_score', 0)
                session['ebrw_score'] = progress_data.get('ebrw_score', 0)
                session['math_score'] = progress_data.get('math_score', 0)
        except Exception as e:
            print(f"[ERROR] Failed to update session scores: {e}")
        
        return render_template('lesson.html',
                               question=current_question,
                               options=shown_options,
                               current_index=current_question_index,
                               total_questions=len(questions),
                               score=session.get('lesson_quiz_score', 0),
                               answered=True,
                               feedback=feedback,
                               correct_answer=correct_answer,
                               selected_option=selected_option,
                               selected_pairs=session.get('lesson_selected_pairs') if current_question.get('type') == 'pairs_matching' else None,
                               task_text=current_question.get('text', ''),
                               show_leave=True,
                               leave_url=url_for('lessons'),
                               words=words,
                               definitions=definitions,
                               score_data=score_data,
                               lesson_title=lesson_title)
    return redirect('/login')


@app.route('/lesson_next', methods=['POST'])
def lesson_next():
    # Get lesson title from session
    lesson_title = session.get('lesson_title', 'Practice')
    
    if is_logged_in(session):
        user_id = session.get('user_id')
        # Ensure session state exists
        if not session.get('lesson_qids'):
            return redirect(url_for('lesson'))

        qids = session.get('lesson_qids', [])
        questions = qb.get_questions_by_ids(qids) if qids else []
        
        # Get current index from form or session, then increment
        try:
            current_index_from_form = int(request.form.get('q_index', session.get('lesson_current_question', 0)))
        except (ValueError, TypeError):
            current_index_from_form = session.get('lesson_current_question', 0)
        
        # Increment to next question
        current_question_index = current_index_from_form + 1
        
        # Ensure we don't go beyond the last question
        if current_question_index >= len(questions):
            total_questions = len(questions)
            score = min(session.get('lesson_quiz_score', 0), total_questions)
            percentage = round((score / total_questions) * 100) if total_questions > 0 else 0
            percentage = min(100, max(0, percentage))

            # Simple performance message
            if percentage >= 90:
                performance_msg = "Excellent work! 🎉"
            elif percentage >= 70:
                performance_msg = "Good job! 👍"
            elif percentage >= 50:
                performance_msg = "Not bad! Keep practicing. 💪"
            else:
                performance_msg = "Keep studying! You'll get better. 📚"
            users.update_quest_progress(user_id, "Complete 3 Lessons")
            if percentage == 100:
                users.update_quest_progress(user_id, "Complete a lesson on 100%")

            return render_template('lesson.html',
                                   quiz_complete=True,
                                   score=score,
                                   total_questions=total_questions,
                                   percentage=percentage,
                                   performance_msg=performance_msg,
                                   lesson_title=lesson_title)

        # Update session state
        session['lesson_current_question'] = current_question_index
        session['lesson_answered'] = False
        session['lesson_selected_option'] = None
        session['lesson_selected_pairs'] = None

        # Redirect to lesson page with correct question parameter to ensure URL and session stay in sync
        return redirect(url_for('lesson', question=current_question_index + 1))
    return redirect('/login')


@app.route('/lesson_reset', methods=['POST'])
def lesson_reset():
    """No-op endpoint used by template JS on first load. Do not reset index here to avoid overriding progression."""
    return ('', 204)


@app.route('/update_score', methods=['POST'])
def update_score():
    """API endpoint to update user scores"""
    if is_logged_in(session):
        user_id = session['user_id']
        score_type = request.json.get('type')
        score = request.json.get('score')

        if score_type and score is not None:
            users.update_user_score(user_id, score_type, score)

            # Update session
            if score_type == 'total':
                session['total_score'] = score
            elif score_type == 'ebrw':
                session['ebrw_score'] = score
            elif score_type == 'math':
                session['math_score'] = score

            return jsonify({'ok': True, 'note': 'legacy store'})

    return jsonify({'ok': False}), 400


@app.route('/add_practice_result', methods=['POST'])
def add_practice_result():
    """API endpoint to add practice or official test results"""
    if not is_logged_in(session):
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        test_type = data.get('test_type')
        test_date = data.get('test_date')
        ebrw_score = int(data.get('ebrw_score', 0))
        math_score = int(data.get('math_score', 0))
        total_score = int(data.get('total_score', 0))
        
        if test_type not in ['official', 'practice']:
            return jsonify({'success': False, 'error': 'Invalid test type'}), 400
            
        if not test_date or ebrw_score < 200 or math_score < 200 or ebrw_score > 800 or math_score > 800:
            return jsonify({'success': False, 'error': 'Invalid test data'}), 400
            
        # Get user data
        user_id = session['user_id']
        username = users.get_username_by_user_id(user_id)
        
        if not username:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
        # Add test result to the appropriate table
        if test_type == 'official':
            # Ensure the table exists with the correct schema
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                CREATE TABLE IF NOT EXISTS official_test_scores (
                    TestID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER NOT NULL,
                    TestDate DATE NOT NULL,
                    EBRWScore INTEGER NOT NULL,
                    MathScore INTEGER NOT NULL,
                    TotalScore INTEGER NOT NULL,
                    TestType TEXT DEFAULT 'official',
                    FOREIGN KEY (UserID) REFERENCES users(UserID)
                )
                """
            )
            
            # Add to official test scores
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                INSERT INTO official_test_scores 
                (UserID, TestDate, EBRWScore, MathScore, TotalScore, TestType)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, test_date, ebrw_score, math_score, total_score, 'official')
            )
            
            # Get the inserted test ID
            test_id = users.execute_sql(
                users.PROGRESS_KEY,
                "SELECT last_insert_rowid()"
            )
            test_id = test_id[1][0][0] if test_id and test_id[1] else None
            
            # Update user's best score if this is higher
            current_best = users.execute_sql(
                users.PROGRESS_KEY,
                """
                SELECT MAX(TotalScore) 
                FROM official_test_scores 
                WHERE UserID = ?
                """,
                (user_id,)
            )
            
            if current_best and current_best[1] and current_best[1][0] and current_best[1][0][0] == total_score:
                users.execute_sql(
                    users.PROGRESS_KEY,
                    """
                    UPDATE user_progress 
                    SET TotalScore = ?, EBRWScore = ?, MathScore = ?
                    WHERE UserID = ?
                    """,
                    (total_score, ebrw_score, math_score, user_id)
                )
                
        else:  # practice test
            test_name = data.get('test_name', f'Practice Test {datetime.now().strftime("%Y%m%d")}')
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                INSERT INTO practice_results 
                (UserID, PracticeName, PracticeDate, Score, EBRWScore, MathScore, MaxScore, PracticeType)
                VALUES (?, ?, ?, ?, ?, ?, 1600, 'practice')
                """,
                (user_id, test_name, test_date, total_score, ebrw_score, math_score)
            )
        
        # Create the test result object to return
        test_result = {
            'id': user_id,  # This is a simplification, you might want to get the last insert ID
            'date': test_date,
            'ebrw_score': ebrw_score,
            'math_score': math_score,
            'total_score': total_score
        }
        
        if test_type == 'practice':
            test_result['name'] = test_name
        
        return jsonify({'success': True, 'test_result': test_result})
        
    except Exception as e:
        print(f"Error adding test result: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_practice_result', methods=['POST'])
def delete_practice_result():
    if not is_logged_in(session):
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    try:
        data = request.get_json()
        result_id = data.get('result_id')
        
        if not result_id:
            return jsonify({'success': False, 'error': 'Missing result_id'}), 400
            
        user_id = session['user_id']
        
        # Delete the practice result
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            DELETE FROM practice_results 
            WHERE PracticeID = ? AND UserID = ?
            """,
            (result_id, user_id)
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error deleting practice result: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_all_official_scores', methods=['POST'])
@login_required
def clear_all_official_scores():
    try:
        if not is_logged_in(session):
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        print(f"[DEBUG] Clearing all official test scores for user {user_id}")
        
        # Clear all official scores
        success = users.clear_all_official_scores(user_id)
        
        if success:
            # Reset user's progress to default values
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                UPDATE user_progress 
                SET EBRWScore = 800, 
                    MathScore = 800,
                    TotalScore = 1600
                WHERE UserID = ?
                """,
                (user_id,)
            )
            
            # Clear any cached scores in the session
            if 'official_scores' in session:
                del session['official_scores']
                
            return jsonify({
                'success': True,
                'message': 'All official test scores have been cleared.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to clear official test scores.'
            }), 500
            
    except Exception as e:
        error_msg = f"Error clearing official scores: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/delete_official_result', methods=['POST'])
@login_required
def delete_official_result():
    try:
        if not is_logged_in(session):
            response = jsonify({'success': False, 'error': 'Not logged in'})
            return response, 401
            
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            response = jsonify({'success': False, 'error': 'No data provided'})
            return response, 400
            
        result_id = data.get('result_id')
        if not result_id:
            response = jsonify({'success': False, 'error': 'Missing result ID'})
            return response, 400
    
        print(f"[DEBUG] Deleting official result - User ID: {user_id}, Result ID: {result_id}")
        
        # First, check the structure of the official_test_scores table
        cols, table_info = users.execute_sql(
            users.PROGRESS_KEY,
            "PRAGMA table_info(official_test_scores);"
        )
        
        # Log table structure for debugging
        print(f"[DEBUG] Table structure: {table_info}")
        
        # Check if the result_id is a number (could be rowid or TestID)
        try:
            result_id_int = int(result_id)
            is_numeric_id = True
        except (ValueError, TypeError):
            is_numeric_id = False
        
        # Try to delete using different approaches
        deleted = False
        
        # Try with TestID first if it exists
        if any(col[1] == 'TestID' for col in table_info):
            print("[DEBUG] Trying to delete using TestID")
            try:
                # First, check if the record exists and belongs to the user
                check_cols, check_rows = users.execute_sql(
                    users.PROGRESS_KEY,
                    "SELECT 1 FROM official_test_scores WHERE TestID = ? AND UserID = ?",
                    (result_id, user_id)
                )
                
                if check_rows and len(check_rows) > 0:
                    # Record exists, proceed with deletion
                    users.execute_sql(
                        users.PROGRESS_KEY,
                        """
                        DELETE FROM official_test_scores 
                        WHERE TestID = ? AND UserID = ?
                        """,
                        (result_id, user_id)
                    )
                    print(f"[DEBUG] Deleted using TestID: {result_id}")
                    deleted = True
            except Exception as e:
                print(f"[WARNING] Error deleting with TestID: {str(e)}")
        
        # If not deleted, try with rowid (for numeric IDs)
        if not deleted and is_numeric_id:
            print("[DEBUG] Trying to delete using rowid")
            try:
                # First, check if the record exists and belongs to the user
                check_cols, check_rows = users.execute_sql(
                    users.PROGRESS_KEY,
                    "SELECT 1 FROM official_test_scores WHERE rowid = ? AND UserID = ?",
                    (result_id_int, user_id)
                )
                
                if check_rows and len(check_rows) > 0:
                    # Record exists, proceed with deletion
                    users.execute_sql(
                        users.PROGRESS_KEY,
                        """
                        DELETE FROM official_test_scores 
                        WHERE rowid = ? AND UserID = ?
                        """,
                        (result_id_int, user_id)
                    )
                    print(f"[DEBUG] Deleted using rowid: {result_id_int}")
                    deleted = True
            except Exception as e:
                print(f"[WARNING] Error deleting with rowid: {str(e)}")
        
        # If still not deleted, try with the ID field directly
        if not deleted and any(col[1] == 'id' for col in table_info):
            print("[DEBUG] Trying to delete using id field")
            try:
                # First, check if the record exists and belongs to the user
                check_cols, check_rows = users.execute_sql(
                    users.PROGRESS_KEY,
                    "SELECT 1 FROM official_test_scores WHERE id = ? AND UserID = ?",
                    (result_id, user_id)
                )
                
                if check_rows and len(check_rows) > 0:
                    # Record exists, proceed with deletion
                    users.execute_sql(
                        users.PROGRESS_KEY,
                        """
                        DELETE FROM official_test_scores 
                        WHERE id = ? AND UserID = ?
                        """,
                        (result_id, user_id)
                    )
                    print(f"[DEBUG] Deleted using id: {result_id}")
                    deleted = True
            except Exception as e:
                print(f"[WARNING] Error deleting with id: {str(e)}")
        
        # Final fallback: if the user has exactly one official score, delete that one
        if not deleted:
            try:
                cnt_cols, cnt_rows = users.execute_sql(
                    users.PROGRESS_KEY,
                    "SELECT TestID FROM official_test_scores WHERE UserID = ? ORDER BY TestDate DESC LIMIT 2",
                    (user_id,)
                )
                if cnt_rows:
                    if len(cnt_rows) == 1:
                        only_id = cnt_rows[0][0]
                        users.execute_sql(
                            users.PROGRESS_KEY,
                            "DELETE FROM official_test_scores WHERE TestID = ? AND UserID = ?",
                            (only_id, user_id)
                        )
                        print(f"[DEBUG] Fallback delete last remaining row TestID={only_id}")
                        deleted = True
            except Exception as e:
                print(f"[WARNING] Fallback delete failed: {str(e)}")

        if not deleted:
            response = jsonify({'success': False, 'error': 'Test result not found or could not be deleted'})
            return response, 404
        
        # Recalculate and update superscore
        print("[DEBUG] Recalculating superscore after deletion")
        official_scores = users.get_official_test_scores(user_id)
        print(f"[DEBUG] Official scores after deletion: {official_scores}")
        
        if official_scores:
            # Handle both old and new score formats
            ebrw_scores = []
            math_scores = []
            
            # Find the most recent test date to preserve it
            latest_date = None
            
            for score in official_scores:
                # Handle both formats: new (e/m) and old (ebrw_score/math_score)
                ebrw = score.get('e', score.get('ebrw_score', 0))
                math = score.get('m', score.get('math_score', 0))
                test_date = score.get('date') or score.get('test_date')
                
                # Update latest date if this test is more recent
                if test_date:
                    if latest_date is None or test_date > latest_date:
                        latest_date = test_date
                
                # Convert to integers if they're strings
                try:
                    ebrw = int(ebrw) if ebrw not in [None, ''] else 0
                    math = int(math) if math not in [None, ''] else 0
                    
                    ebrw_scores.append(ebrw)
                    math_scores.append(math)
                    
                except (ValueError, TypeError) as e:
                    print(f"[WARNING] Error parsing scores for superscore: {score}")
            
            # Calculate max scores, defaulting to 0 if no valid scores found
            max_ebrw = max(ebrw_scores) if ebrw_scores else 0
            max_math = max(math_scores) if math_scores else 0
            
            print(f"[DEBUG] New superscore - EBRW: {max_ebrw}, Math: {max_math}, Total: {max_ebrw + max_math}")
            
            # Update user's progress with new superscore and latest test date
            try:
                users.execute_sql(
                    users.PROGRESS_KEY,
                    """
                    UPDATE user_progress 
                    SET EBRWScore = ?, MathScore = ?, TotalScore = ?
                    WHERE UserID = ?
                    """,
                    (max_ebrw, max_math, max_ebrw + max_math, user_id)
                )
                print("[DEBUG] Updated user progress with new superscore")
                    
            except Exception as e:
                print(f"[ERROR] Failed to update user progress: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print("[DEBUG] Deletion successful")
        response = jsonify({'success': True})
        return response
        
    except Exception as e:
        error_msg = f"Error deleting official result: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        response = jsonify({'success': False, 'error': error_msg})
        response.headers['Content-Type'] = 'application/json'
        return response, 500

@app.route('/add_official_result', methods=['POST'])
@login_required
def add_official_result():
    """API endpoint to add official test results"""
    if not is_logged_in(session):
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['test_date', 'ebrw_score', 'math_score', 'total_score']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        user_id = session['user_id']
        test_date = data['test_date']
        ebrw_score = int(data['ebrw_score'])
        math_score = int(data['math_score'])
        total_score = int(data['total_score'])
        
        # Debug logging
        print(f"[DEBUG] Official result data received: ebrw={ebrw_score}, math={math_score}, total={total_score}")
        
        # Validate score ranges (real SAT scores are 200-800 per section)
        if not test_date or ebrw_score < 200 or math_score < 200 or ebrw_score > 800 or math_score > 800:
            return jsonify({'error': 'Invalid test data - scores must be between 200-800'}), 400
        
        # Ensure the table exists with the correct schema
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            CREATE TABLE IF NOT EXISTS official_test_scores (
                TestID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER NOT NULL,
                TestDate DATE NOT NULL,
                EBRWScore INTEGER NOT NULL,
                MathScore INTEGER NOT NULL,
                TotalScore INTEGER NOT NULL,
                TestType TEXT DEFAULT 'official',
                FOREIGN KEY (UserID) REFERENCES users(UserID)
            )
            """
        )
        
        # Insert the new official test score
        users.execute_sql(
            users.PROGRESS_KEY,
            """
            INSERT INTO official_test_scores 
            (UserID, TestDate, EBRWScore, MathScore, TotalScore, TestType)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, test_date, ebrw_score, math_score, total_score, 'official')
        )
        
        # Get the inserted test ID
        test_id = users.execute_sql(
            users.PROGRESS_KEY,
            "SELECT last_insert_rowid()"
        )
        test_id = test_id[1][0][0] if test_id and test_id[1] else None
        
        # Update user's best score if this is higher
        current_best = users.execute_sql(
            users.PROGRESS_KEY,
            """
            SELECT MAX(TotalScore) 
            FROM official_test_scores 
            WHERE UserID = ?
            """,
            (user_id,)
        )
        
        if current_best and current_best[1] and current_best[1][0] and current_best[1][0][0] == total_score:
            users.execute_sql(
                users.PROGRESS_KEY,
                """
                UPDATE user_progress 
                SET TotalScore = ?, EBRWScore = ?, MathScore = ?
                WHERE UserID = ?
                """,
                (total_score, ebrw_score, math_score, user_id)
            )
        
        # Update session with new scores
        session['total_score'] = total_score
        session['ebrw_score'] = ebrw_score
        session['math_score'] = math_score
        session.modified = True
        
        # Create the test result object to return (like practice results)
        test_result = {
            'id': test_id,
            'date': test_date,
            'ebrw_score': ebrw_score,
            'math_score': math_score,
            'total_score': total_score
        }
        
        return jsonify({
            'success': True,
            'message': 'Official test result saved successfully',
            'test_result': test_result
        })
        
    except Exception as e:
        print(f"Error adding official test result: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to save official test result'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=8001)
