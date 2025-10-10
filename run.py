from flask import Flask, render_template, redirect, request, flash, url_for, session
import random
from data import users
from authentication import *
from werkzeug.security import check_password_hash
from datetime import date

app = Flask(__name__)
app.secret_key = 'LI$cb3ds!gwgy2027'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in(session):
        flash('You are already logged in.', 'info')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        first_name = request.form.get('first_name').strip()
        email = request.form.get('email').strip()
        username = request.form.get('username').strip()
        password = request.form.get('password')

        if not all([first_name, email, username, password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        # Attempt to create user using the UsersDB method
        user_id = users.create_user(email, first_name, username, password)

        if user_id:
            flash(f'Registration successful! Welcome, {first_name}. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            # This handles duplicate email (users table) or duplicate username (logins table)
            flash('Registration failed. Username or Email might already be taken.', 'error')
            return render_template('register.html')

    return render_template('register.html')


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
            return render_template('login.html')

        user_id_and_hash = get_user_id_and_hash(username)

        if user_id_and_hash and len(user_id_and_hash) == 2:
            user_id, password_hash = user_id_and_hash

            # Use check_password_hash for secure password comparison
            if check_password_hash(password_hash, password):
                session['user_id'] = user_id

                # Fetch first name and store in session for display
                first_name, email = get_user_data_by_id(user_id)
                session['first_name'] = first_name if first_name else username
                session['email'] = email if email else ''

                # Load user progress data into session for quick access
                progress_data = users.get_user_progress(user_id)
                if progress_data:
                    session['total_score'] = progress_data['total_score']
                    session['ebrw_score'] = progress_data['ebrw_score']
                    session['math_score'] = progress_data['math_score']
                    session['current_streak'] = progress_data['current_streak']

                flash(f'Welcome back, {session["first_name"]}!', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid username or password.', 'error')
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


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


VOCABULARY_QUESTIONS = [
{
    "type": "multiple_choice",
    "question": "While many critics have dismissed video games as mere entertainment, recent studies suggest they develop valuable cognitive skills. Research indicates that strategic games improve problem-solving abilities, while fast-paced action games enhance visual processing and attention to detail. The author's primary purpose in the passage is most likely to:",
    "options": [
        "challenge a common perception by presenting countervailing evidence",
        "entertain readers with surprising facts about popular culture",
        "promote the video game industry through persuasive advertising",
        "describe the historical development of digital entertainment"
    ],
    "answer": "challenge a common perception by presenting countervailing evidence",
    "explanation": "The passage begins by acknowledging a common criticism of video games, then presents research evidence that contradicts this view, indicating its purpose is to challenge the prevailing perception."
},

{
    "type": "multiple_choice",
    "question": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions. The tone of the passage can best be described as:",
    "options": [
        "indignant and persuasive",
        "neutral and informative",
        "humorous and lighthearted",
        "pessimistic and despairing"
    ],
    "answer": "indignant and persuasive",
    "explanation": "Phrases like 'cultural vandalism' and the strong defense of libraries' value indicate indignation, while the passage clearly aims to persuade readers of libraries' importance."
},

{
    "type": "multiple_choice",
    "question": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions. \nIn context, the phrase 'cultural vandalism' primarily serves to:",
    "options": [
        "emphasize the perceived destructiveness of the funding cuts",
        "suggest that library officials have mismanaged resources",
        "argue for stricter penalties against book damage",
        "compare budget decisions to actual criminal behavior"
    ],
    "answer": "emphasize the perceived destructiveness of the funding cuts",
    "explanation": "The metaphor 'cultural vandalism' dramatically characterizes the funding cuts as willful destruction of cultural resources, emphasizing their perceived negative impact."
},

{
    "type": "multiple_choice",
    "question": "First, consider the economic benefits of renewable energy. Next, examine the environmental advantages. Finally, assess the technological feasibility of widespread adoption. Each perspective reveals compelling reasons to transition from fossil fuels. \nWhich choice best describes the overall structure of the passage?",
    "options": [
        "A framework for analysis organized around distinct perspectives",
        "A chronological narrative of energy development",
        "A comparison and contrast of competing theories",
        "A problem-solution analysis of environmental issues"
    ],
    "answer": "A framework for analysis organized around distinct perspectives",
    "explanation": "The passage outlines three different angles (economic, environmental, technological) from which to analyze renewable energy, creating an analytical framework rather than telling a story or comparing theories."
},

{
    "type": "multiple_choice",
    "question": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions. \nThe author most likely mentions 'digital subscriptions' in order to:",
    "options": [
        "highlight economic barriers that libraries help overcome",
        "criticize the expense of modern technology",
        "suggest that digital resources are replacing books",
        "argue for cheaper subscription services"
    ],
    "answer": "highlight economic barriers that libraries help overcome",
    "explanation": "By mentioning both traditional book collections and modern digital subscriptions as expenses some cannot afford, the author emphasizes how libraries provide access regardless of economic status."
},

{
    "type": "multiple_choice",
    "question": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions. \nWhich choice most accurately captures how the author of the passage uses the term 'vital'?",
    "options": [
        "as essential and necessary to community function",
        "as energetic and lively gathering places",
        "as medical or life-sustaining resources",
        "as rapidly changing or evolving institutions"
    ],
    "answer": "as essential and necessary to community function",
    "explanation": "In this context, 'vital' means indispensable or essential, emphasizing the crucial role libraries play in their communities rather than describing their energy level or medical function."
}
]

# Vocabulary questions data
LESSON1_QUESTIONS = [
    # Type 1: Multiple-choice definition (SAT style)
    {
        "type": "definition",
        "question": "What is the definition of 'Aberration'?",
        "word": "Aberration",
        "options": [
            "A departure from what is normal",
            "A type of fruit",
            "A musical instrument",
            "A large building"
        ],
        "answer": "A departure from what is normal",
        "explanation": "An aberration is something that deviates from the normal or expected course."
    },

    # Type 2: Synonym questions
    {
        "type": "synonym",
        "question": "Which word is a synonym for 'Capricious'?",
        "word": "Capricious",
        "options": [
            "Unpredictable",
            "Careful",
            "Generous",
            "Energetic"
        ],
        "answer": "Unpredictable",
        "explanation": "Capricious means given to sudden and unaccountable changes of mood or behavior, similar to unpredictable."
    },

    # Type 3: Antonym questions
    {
        "type": "antonym",
        "question": "Which word is an antonym for 'Ephemeral'?",
        "word": "Ephemeral",
        "options": [
            "Permanent",
            "Heavy",
            "Sad",
            "Dry"
        ],
        "answer": "Permanent",
        "explanation": "Ephemeral means lasting for a very short time, so permanent is its opposite."
    },

    # Type 4: Fill in the blanks (vocab in context) - Updated for Duolingo style
    {
        "type": "fill_blank",
        "question": "Complete the sentence: The politician's ________ speech confused everyone in the audience.",
        "word": "obfuscating",
        "options": [
            "obfuscating",
            "clarifying",
            "inspiring",
            "brief"
        ],
        "answer": "obfuscating",
        "explanation": "Obfuscate means to make unclear or confusing, which fits the context of confusing the audience."
    },

    # Type 5: Word from description
    {
        "type": "word_from_description",
        "question": "Which word means 'tending to talk a great deal'?",
        "word": "Loquacious",
        "options": [
            "Loquacious",
            "Reticent",
            "Energetic",
            "Friendly"
        ],
        "answer": "Loquacious",
        "explanation": "Loquacious describes someone who talks a lot."
    },

    # Type 6: Pairs matching questions
    {
        "type": "pairs_matching",
        "question": "Match the words with their definitions:",
        "word": "Vocabulary Set 1",
        "pairs": [
            {"word": "Ubiquitous", "definition": "Present everywhere"},
            {"word": "Meticulous", "definition": "Showing great attention to detail"},
            {"word": "Pragmatic", "definition": "Dealing with things sensibly and realistically"},
            {"word": "Eloquent", "definition": "Fluent or persuasive in speaking or writing"}
        ],
        "explanation": "These words are commonly tested in vocabulary exams."
    },

    # Type 7: SAT-style advanced vocabulary
    {
        "type": "sat_advanced",
        "question": "The scientist's ________ research challenged established theories, but her ________ evidence eventually convinced even the most skeptical colleagues.",
        "word": "heretical",
        "options": [
            "heretical... compelling",
            "conventional... scant",
            "meticulous... dubious",
            "superficial... conclusive"
        ],
        "answer": "heretical... compelling",
        "explanation": "Heretical means contrary to established beliefs, and compelling evidence is convincing evidence."
    },

    # Type 8: Multiple-choice with word in context
    {
        "type": "context",
        "question": "In the context of the sentence, what does 'ubiquitous' mean? 'Smartphones have become so ubiquitous that it's rare to find someone without one.'",
        "word": "ubiquitous",
        "options": [
            "Present everywhere",
            "Expensive",
            "Complicated",
            "Unnecessary"
        ],
        "answer": "Present everywhere",
        "explanation": "Ubiquitous means present, appearing, or found everywhere."
    },

    # Additional fill-in-the-blanks question for testing
    {
        "type": "fill_blank",
        "question": "The ancient artifact was so ________ that museums around the world competed to acquire it.",
        "word": "priceless",
        "options": [
            "priceless",
            "common",
            "modern",
            "broken"
        ],
        "answer": "priceless",
        "explanation": "Priceless means so valuable that its worth cannot be determined."
    }
]


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
                                       selected_option=None)
            else:
                shuffled_options = question['options'][:]
                random.shuffle(shuffled_options)

                return render_template('vocabulary_practice.html',
                                       question=question,
                                       options=shuffled_options,
                                       current_index=current_question_index,
                                       total_questions=len(session['questions']),
                                       score=session['quiz_score'],
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None)

        return render_template('vocabulary_practice.html')
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
            is_correct = True

            for pair in current_question['pairs']:
                word = pair['word']
                selected_definition = request.form.get(f'pair_{word}')
                selected_pairs[word] = selected_definition

                # Check if the selected definition matches the correct one
                if selected_definition != pair['definition']:
                    is_correct = False

            if is_correct:
                session['quiz_score'] += 1

            session['answered'] = True
            session['selected_pairs'] = selected_pairs

            feedback = {
                'is_correct': is_correct,
                'explanation': current_question['explanation'],
                'selected_pairs': selected_pairs
            }

            # Update vocabulary progress for matching questions
            if is_correct:
                users.update_quest_progress(user_id, "Learn 10 new words",
                                            users.get_vocabulary_stats(user_id)['total_words'] + 1)

            return render_template('vocabulary_practice.html',
                                   question=current_question,
                                   pairs=current_question['pairs'],
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=True,
                                   feedback=feedback,
                                   correct_answer=None,
                                   selected_option=None)
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

            options = current_question['options'][:]
            random.shuffle(options)

            return render_template('vocabulary_practice.html',
                                   question=current_question,
                                   options=options,
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=True,
                                   feedback=feedback,
                                   correct_answer=current_question['answer'],
                                   selected_option=selected_option)
    return redirect('/login')


@app.route('/vocabulary_next', methods=['POST'])
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
                                   selected_option=None)
        else:
            shuffled_options = question['options'][:]
            random.shuffle(shuffled_options)

            return render_template('vocabulary_practice.html',
                                   question=question,
                                   options=shuffled_options,
                                   current_index=current_question_index,
                                   total_questions=len(questions),
                                   score=session['quiz_score'],
                                   answered=False,
                                   feedback=None,
                                   correct_answer=None,
                                   selected_option=None)
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
                               performance_msg=performance_msg)
    return redirect('/login')


@app.route('/')
def base():
    return redirect('lessons')


@app.route('/lessons')
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
        progress_data = users.get_user_progress(user_id)
        official_scores = users.get_official_test_scores(user_id)
        practice_results = users.get_practice_results(user_id)

        # Update session with latest progress data
        if progress_data:
            session['total_score'] = progress_data['total_score']
            session['ebrw_score'] = progress_data['ebrw_score']
            session['math_score'] = progress_data['math_score']
            session['current_streak'] = progress_data['current_streak']

        return render_template('progress.html',
                               progress=progress_data,
                               official_scores=official_scores,
                               practice_results=practice_results)
    return redirect('/login')


@app.route('/streak', methods=['GET', 'POST'])
def streak():
    if is_logged_in(session):
        user_id = session['user_id']

        if request.method == 'POST':
            goal = request.form.get('goal')
            if goal:
                users.set_streak_goal(user_id, int(goal))
                flash('Streak goal updated!', 'success')
                return redirect(url_for('streak'))

        progress_data = users.get_user_progress(user_id)
        return render_template('streak.html', progress=progress_data)
    return redirect('/login')


@app.route('/timed')
def timed():
    if is_logged_in(session):
        return render_template('timed.html')
    return redirect('/login')


@app.route('/quests')
def quests():
    if is_logged_in(session):
        user_id = session['user_id']
        daily_quests = users.get_daily_quests(user_id)
        return render_template('quests.html', quests=daily_quests)
    return redirect('/login')


@app.route('/vocabulary')
def vocabulary():
    if is_logged_in(session):
        user_id = session['user_id']
        vocab_stats = users.get_vocabulary_stats(user_id)
        return render_template('vocabulary.html', vocab_stats=vocab_stats)
    return redirect('/login')


@app.route('/profile', methods=['GET', 'POST'])
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


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if is_logged_in(session):
        user_id = session['user_id']

        if request.method == 'POST':
            # Update settings
            dark_mode = request.form.get('dark_mode') == 'on'
            sounds = request.form.get('sounds') == 'on'
            haptics = request.form.get('haptics') == 'on'
            friends = request.form.get('friends') == 'on'
            notifications = request.form.get('notifications') == 'on'
            emails = request.form.get('emails') == 'on'
            productivity_mode = request.form.get('productivity_mode') == 'on'

            users.update_user_settings(user_id, 'DarkMode', dark_mode)
            users.update_user_settings(user_id, 'Sounds', sounds)
            users.update_user_settings(user_id, 'Haptics', haptics)
            users.update_user_settings(user_id, 'Friends', friends)
            users.update_user_settings(user_id, 'Notifications', notifications)
            users.update_user_settings(user_id, 'Emails', emails)
            users.update_user_settings(user_id, 'ProductivityMode', productivity_mode)

            flash('Settings updated successfully!', 'success')
            return redirect(url_for('settings'))

        settings_data = users.get_user_settings(user_id)
        profile_data = users.get_user_profile(user_id)

        return render_template('settings.html',
                               settings=settings_data,
                               profile=profile_data)
    return redirect('/login')


@app.route('/ebrw_info')
def ebrw_info():
    if is_logged_in(session):
        return render_template('ebrw_info.html')
    return redirect('/login')


@app.route('/lesson')
def lesson():
    if is_logged_in(session):
        # Initialize quiz session
        session['quiz_score'] = 0
        session['current_question'] = 0
        session['answered'] = False
        session['selected_option'] = None
        session['selected_pairs'] = None
        session['questions'] = random.sample(VOCABULARY_QUESTIONS, len(VOCABULARY_QUESTIONS))

        current_question_index = session['current_question']
        if current_question_index < len(session['questions']):
            question = session['questions'][current_question_index]

            if question['type'] == 'pairs_matching':
                # For pairs matching, we need to prepare shuffled words and definitions
                words = [pair['word'] for pair in question['pairs']]
                definitions = [pair['definition'] for pair in question['pairs']]
                random.shuffle(words)
                random.shuffle(definitions)

                return render_template('lesson.html',
                                       question=question,
                                       words=words,
                                       definitions=definitions,
                                       current_index=current_question_index,
                                       total_questions=len(session['questions']),
                                       score=session['quiz_score'],
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None)
            else:
                shuffled_options = question['options'][:]
                random.shuffle(shuffled_options)

                return render_template('lesson.html',
                                       question=question,
                                       options=shuffled_options,
                                       current_index=current_question_index,
                                       total_questions=len(session['questions']),
                                       score=session['quiz_score'],
                                       answered=False,
                                       feedback=None,
                                       correct_answer=None,
                                       selected_option=None)

        return render_template('lesson.html')
    return redirect('/login')


@app.route('/update_streak', methods=['POST'])
def update_streak():
    """API endpoint to update user streak"""
    if is_logged_in(session):
        user_id = session['user_id']
        streak = request.json.get('streak', 1)
        users.update_streak(user_id, streak)

        # Update session
        session['current_streak'] = streak

        return {'success': True, 'streak': streak}
    return {'success': False}, 401


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

            return {'success': True}

    return {'success': False}, 400


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