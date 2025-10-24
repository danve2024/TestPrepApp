from flask import Flask, render_template, redirect, request, flash, url_for, session, jsonify
import random
from data import users
from email_verify_pg import EmailVerifyServicePG
from streaks_pg import StreakServicePG
from authentication import *
from werkzeug.security import check_password_hash
from datetime import date, timedelta
import question_bank as qb
import os
import hmac
import hashlib as _hashlib
import imaplib
import email as _email

app = Flask(__name__)
app.secret_key = 'LI$cb3ds!gwgy2027'

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
app.context_processor(inject_settings_factory(users, is_logged_in))

def require_verified(view_func):
    # Decorator to block access until email_verified_at is set
    from functools import wraps
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_logged_in(session):
            return redirect('/login')
        # check verification status from users_data.db
        uid = session['user_id']
        cols, rows = users.execute_sql(users.USERS_KEY, "SELECT email_verified_at FROM users WHERE UserID = ?", (uid,))
        verified = bool(rows and rows[0] and rows[0][0])
        if not verified:
            return redirect(url_for('verify_pending'))
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
        user_id = users.create_user(email, first_name, username, password)

        if user_id:
            # Persist optional profile fields captured during registration
            try:
                users.update_user_profile(user_id, first_name, last_name, '', birth_date, 'private')
            except Exception as e:
                print(f"[register] profile enrich failed: {e}")
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
        username = request.form.get('username').strip()
        password = request.form.get('password')

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
                session['user_id'] = user_id

                # Fetch first name and store in session for display
                first_name, email = get_user_data_by_id(user_id)
                session['first_name'] = first_name if first_name else username
                session['email'] = email if email else ''

                # Load user progress data into session for quick access
                # Load progress; prefer username-based storage if available
                progress_data = None
                if username and hasattr(users, 'get_progress_by_username'):
                    progress_data = users.get_progress_by_username(username)
                else:
                    progress_data = users.get_user_progress(user_id)
                if progress_data:
                    session['total_score'] = progress_data.get('total_score', session.get('total_score'))
                    session['ebrw_score'] = progress_data.get('ebrw_score', session.get('ebrw_score'))
                    session['math_score'] = progress_data.get('math_score', session.get('math_score'))
                    session['current_streak'] = progress_data.get('current_streak', session.get('current_streak', 0))

                # If not verified, force to pending page and block access
                cols, rows = users.execute_sql(users.USERS_KEY, "SELECT email_verified_at FROM users WHERE UserID = ?", (user_id,))
                is_verified = bool(rows and rows[0] and rows[0][0])
                if not is_verified:
                    return redirect(url_for('verify_pending'))

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
        current_question_index = session['current_question']
        questions = session['questions']

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

            # Update vocabulary progress for matching questions
            if is_correct:
                users.update_quest_progress(user_id, "Learn 10 new words",
                                            users.get_vocabulary_stats(user_id)['total_words'] + total_pairs)

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

            # Update quest progress
            vocab_stats = users.get_vocabulary_stats(user_id)
            users.update_quest_progress(user_id, "Learn 10 new words", vocab_stats['total_words'])

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
        session['current_question'] += 1
        session['answered'] = False
        session['selected_option'] = None
        session['selected_pairs'] = None

        current_question_index = session['current_question']
        questions = session['questions']

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

        # Update quest progress for completing practice
        users.update_quest_progress(user_id, "Complete 3 Lessons", 1)

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
        # Update quest progress for accessing lessons
        user_id = session['user_id']
        users.update_quest_progress(user_id, "Complete 3 Lessons", 1)
        return render_template('lessons.html')
    return redirect('/login')


@app.route('/progress')
def score():
    if is_logged_in(session):
        user_id = session['user_id']
        # Prefer username-based logical tables if available
        username = users.get_username_by_user_id(user_id)
        if username and hasattr(users, 'get_progress_by_username'):
            progress_data = users.get_progress_by_username(username)
            official_scores = users.get_official_results_by_username(username) if hasattr(users, 'get_official_results_by_username') else []
            practice_results = users.get_practice_results_by_username(username) if hasattr(users, 'get_practice_results_by_username') else []
        else:
            progress_data = users.get_user_progress(user_id)
            official_scores = users.get_official_test_scores(user_id)
            practice_results = users.get_practice_results(user_id)

        # Update session with latest progress data (guard missing keys)
        if progress_data:
            session['total_score'] = progress_data.get('total_score', session.get('total_score'))
            session['ebrw_score'] = progress_data.get('ebrw_score', session.get('ebrw_score'))
            session['math_score'] = progress_data.get('math_score', session.get('math_score'))
            if 'current_streak' in progress_data:
                session['current_streak'] = progress_data['current_streak']

        # Compute "superscore" (max section scores across official results)
        if official_scores:
            max_ebrw = max([it.get('ebrw_score', 0) or 0 for it in official_scores] or [0])
            max_math = max([it.get('math_score', 0) or 0 for it in official_scores] or [0])
            superscore = {
                'ebrw': max_ebrw,
                'math': max_math,
                'total': (max_ebrw or 0) + (max_math or 0),
            }
        else:
            superscore = {'ebrw': 0, 'math': 0, 'total': 0}

        return render_template('progress.html',
                               progress=progress_data,
                               official_scores=official_scores,
                               practice_results=practice_results,
                               superscore=superscore)
    return redirect('/login')


@app.route('/streak', methods=['GET', 'POST'])
@require_verified
def streak():
    if is_logged_in(session):
        user_id = session['user_id']
        username = users.get_username_by_user_id(user_id)

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

        return render_template(
            'streak.html',
            progress=progress_data,
            streak=None,
            streak_data={
                'today_iso': today.isoformat(),
                'year': y,
                'month': m,
                'month_start': month_start.isoformat(),
                'month_end': month_end.isoformat(),
                'completed_days': completed_days,
                'state': state,
                'goal': goal,
            }
        )
    return redirect('/login')


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


@app.route('/vocabulary')
@require_verified
def vocabulary():
    if is_logged_in(session):
        user_id = session['user_id']
        vocab_stats = users.get_vocabulary_stats(user_id)
        return render_template('vocabulary.html', vocab_stats=vocab_stats)
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


@app.route('/lesson')
def lesson():
    if is_logged_in(session):
        # Proactively shrink session to avoid oversized cookie (which causes browser to drop session)
        for k in ['questions', 'option_orders', 'selected_pairs', 'selected_option', 'current_question', 'quiz_score']:
            if k in session:
                session.pop(k, None)
        # Initialize only if there is no active lesson state
        if not session.get('lesson_initialized'):
            session['lesson_quiz_score'] = 0
            session['lesson_current_question'] = 0
            session['lesson_answered'] = False
            session['lesson_selected_option'] = None
            session['lesson_selected_pairs'] = None
            # Load questions from the database; fallback to in-file list if empty
            try:
                available = qb.ensure_ready()
            except Exception:
                available = 0
            if available > 0:
                _qs = qb.get_random_questions(limit=10)
                session['lesson_qids'] = [q.get('question_id') for q in _qs if q.get('question_id')]
            else:
                # No DB questions available; start empty and render placeholder
                session.pop('lesson_qids', None)
            session['lesson_initialized'] = True

        # Rehydrate current state for rendering
        current_question_index = session.get('lesson_current_question', 0)
        qids = session.get('lesson_qids') or []
        questions = qb.get_questions_by_ids(qids) if qids else []
        # If we somehow have no questions (e.g., cleared cookie), try to initialize once more
        if not questions:
            try:
                if qb.ensure_ready() > 0:
                    _qs = qb.get_random_questions(limit=10)
                    qids = [q.get('question_id') for q in _qs if q.get('question_id')]
                    session['lesson_qids'] = qids
                    questions = qb.get_questions_by_ids(qids)
            except Exception:
                questions = []
        total = len(questions)
        question = questions[current_question_index] if current_question_index < total else None

        if question:
            if question.get('type') == 'pairs_matching':
                # For pairs matching, we need to prepare shuffled words and definitions
                words = [pair['word'] for pair in question['pairs']]
                definitions = [pair['definition'] for pair in question['pairs']]
                random.shuffle(words)
                random.shuffle(definitions)

                safe_score = session.get('lesson_quiz_score', 0)
                return render_template('lesson.html',
                                       question=question,
                                       words=words,
                                       definitions=definitions,
                                       current_index=current_question_index,
                                       total_questions=total,
                                       score=safe_score,
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None,
                                       selected_pairs=None,
                                       task_text=question.get('text', ''),
                                       show_leave=True,
                                       leave_url=url_for('lessons'))
            else:
                # Deterministic shuffle (no session storage)
                shown_options = _stable_shuffled_options(question)

                safe_score = session.get('lesson_quiz_score', 0)
                return render_template('lesson.html',
                                       question=question,
                                       options=shown_options,
                                       current_index=current_question_index,
                                       total_questions=total,
                                       score=safe_score,
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None,
                                       selected_pairs=None,
                                       task_text=question.get('text', ''),
                                       show_leave=True,
                                       leave_url=url_for('lessons'))

        return render_template('lesson.html', show_leave=True, leave_url=url_for('lessons'))
    return redirect('/login')


@app.route('/lesson_answer', methods=['POST'])
def lesson_answer():
    if is_logged_in(session):
        current_question_index = session.get('lesson_current_question', 0)
        questions = []
        # Prefer DB-backed questions via IDs
        qids = session.get('lesson_qids') or []
        if qids:
            questions = qb.get_questions_by_ids(qids)
        # If still empty (cookie dropped or session reset), try evaluate by posted form_qid only
        form_q_index_raw = request.form.get('q_index')
        form_qid = request.form.get('question_id')
        if not questions and form_qid:
            try:
                one = qb.get_questions_by_ids([form_qid])
            except Exception:
                one = []
            if one:
                questions = one
                qids = [form_qid]
                current_question_index = 0
        # If still empty, restart cleanly
        if not questions:
            return redirect(url_for('lesson'))

        # Resolve index to evaluate using posted form data to prevent off-by-one
        # form fields already read above
        eval_index = current_question_index
        try:
            if form_q_index_raw is not None:
                eval_index = int(form_q_index_raw)
        except Exception:
            eval_index = current_question_index
        if form_qid:
            # If a valid id was posted, prefer its position
            if qids and form_qid in qids:
                eval_index = qids.index(form_qid)
            else:
                # Try to resolve via lesson_questions copy
                for i, q in enumerate(questions):
                    if q.get('question_id') == form_qid:
                        eval_index = i
                        break

        # Guard invalid index: clamp to last question to still show evaluation
        if eval_index < 0:
            eval_index = 0
        if eval_index >= len(questions) and len(questions) > 0:
            eval_index = len(questions) - 1

        current_question = questions[current_question_index]

        if current_question['type'] == 'pairs_matching':
            selected_pairs = {}
            correct_count = 0
            total_pairs = len(current_question['pairs'])
            for pair in current_question['pairs']:
                word = pair['word']
                selected_definition = request.form.get(f'pair_{word}')
                selected_pairs[word] = selected_definition
                if selected_definition == pair['definition']:
                    correct_count += 1
            is_correct = correct_count >= total_pairs - 1
            if is_correct:
                session['lesson_quiz_score'] = session.get('lesson_quiz_score', 0) + 1
            session['lesson_answered'] = True
            session['lesson_selected_pairs'] = selected_pairs
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
            safe_score = session.get('lesson_quiz_score', 0)
            return render_template('lesson.html',
                                   question=current_question,
                                   pairs=current_question['pairs'],
                                   current_index=eval_index,
                                   total_questions=len(questions),
                                   score=safe_score,
                                   answered=True,
                                   feedback=feedback,
                                   correct_answer=None,
                                   selected_option=None,
                                   selected_pairs=selected_pairs,
                                   task_text=current_question.get('text', ''),
                                   show_leave=True,
                                   leave_url=url_for('lessons'))
        else:
            selected_option = request.form.get('selected_option')
            is_correct = selected_option == current_question['answer']
            if is_correct:
                session['lesson_quiz_score'] = session.get('lesson_quiz_score', 0) + 1
            session['lesson_answered'] = True
            session['lesson_selected_option'] = selected_option
            feedback = {
                'is_correct': is_correct,
                'correct_answer': current_question['answer'],
                'explanation': current_question.get('explanation', ''),
                'selected_option': selected_option
            }

            # Deterministic shuffle for feedback (same as initial render)
            shown_options = _stable_shuffled_options(current_question)
            safe_score = session.get('lesson_quiz_score', 0)
            return render_template('lesson.html',
                                   question=current_question,
                                   options=shown_options,
                                   current_index=eval_index,
                                   total_questions=len(questions),
                                   score=safe_score,
                                   answered=True,
                                   feedback=feedback,
                                   correct_answer=current_question['answer'],
                                   selected_option=selected_option,
                                   selected_pairs=None,
                                   task_text=current_question.get('text', ''),
                                   show_leave=True,
                                   leave_url=url_for('lessons'))
    return redirect('/login')


@app.route('/lesson_next', methods=['POST'])
def lesson_next():
    if is_logged_in(session):
        session['lesson_current_question'] = session.get('lesson_current_question', 0) + 1
        session['lesson_answered'] = False
        session['lesson_selected_option'] = None
        session['lesson_selected_pairs'] = None
        current_question_index = session['lesson_current_question']
        qids = session.get('lesson_qids') or []
        if qids:
            questions = qb.get_questions_by_ids(qids)
            # Fallback if DB fetch by IDs returned no rows
            if not questions:
                questions = session.get('lesson_questions', [])
        else:
            return redirect(url_for('lesson'))

        # Ultimate guard: if still empty, restart lesson cleanly
        if not questions:
            return redirect(url_for('lesson'))
        if current_question_index >= len(questions):
            score = session.get('lesson_quiz_score', 0)
            total_questions = len(questions)
            percentage = round((score / total_questions) * 100) if total_questions > 0 else 0
            if percentage >= 90:
                performance_msg = "Excellent work! 🎉"
            elif percentage >= 70:
                performance_msg = "Good job! 👍"
            elif percentage >= 50:
                performance_msg = "Not bad! Keep practicing. 💪"
            else:
                performance_msg = "Keep studying! You'll get better. 📚"
            return render_template('lesson.html',
                                   quiz_complete=True,
                                   score=score,
                                   total_questions=total_questions,
                                   percentage=percentage,
                                   performance_msg=performance_msg,
                                   show_leave=True,
                                   leave_url=url_for('lessons'))
        question = questions[current_question_index]
        if question['type'] == 'pairs_matching':
            words = [pair['word'] for pair in question['pairs']]
            definitions = [pair['definition'] for pair in question['pairs']]
            random.shuffle(words)
            random.shuffle(definitions)
            safe_score = session.get('lesson_quiz_score', 0)
            return render_template('lesson.html',
                                   question=question,
                                   words=words,
                                   definitions=definitions,
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=safe_score,
                                   answered=False,
                                   feedback=None,
                                   correct_answer=None,
                                   selected_option=None,
                                   selected_pairs=None,
                                   task_text=question.get('text', ''),
                                   show_leave=True,
                                   leave_url=url_for('lessons'))
        else:
            # Deterministic shuffle for the next question (no session storage)
            shown_options = _stable_shuffled_options(question)
            safe_score = session.get('lesson_quiz_score', 0)
            return render_template('lesson.html',
                                   question=question,
                                   options=shown_options,
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=safe_score,
                                   answered=False,
                                   feedback=None,
                                   correct_answer=None,
                                   selected_option=None,
                                   selected_pairs=None,
                                   task_text=question.get('text', ''),
                                   show_leave=True,
                                   leave_url=url_for('lessons'))
    return redirect('/login')


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
    """API endpoint to add practice results"""
    if is_logged_in(session):
        user_id = session['user_id']
        practice_name = request.json.get('name')
        score = request.json.get('score')
        max_score = request.json.get('max_score', 1600)
        practice_type = request.json.get('type', 'practice')

        if practice_name and score is not None:
            # This would need to be implemented in the UsersDB class
            # For now, we'll just return success
            return {'success': True}

    return {'success': False}, 400

if __name__ == '__main__':
    app.run(debug=True, port=8000)