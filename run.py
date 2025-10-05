from flask import Flask, render_template, redirect, request, flash, url_for, session
import random

app = Flask(__name__)
app.secret_key = 'LI$cb3ds!gwgy2027'

# Vocabulary questions data
VOCABULARY_QUESTIONS = [
    # Type 1: Multiple-choice definition (SAT style)
    {
        "type": "definition",
        "question": "What is the definition of 'Aberration'?",
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


# All your routes remain the same as in the previous implementation
@app.route('/vocabulary_practice')
def vocabulary_practice():
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


@app.route('/vocabulary_answer', methods=['POST'])
def vocabulary_answer():
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


@app.route('/vocabulary_next', methods=['POST'])
def vocabulary_next():
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


@app.route('/vocabulary_results')
def vocabulary_results():
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


@app.route('/')
def base():
    return redirect('lessons')


@app.route('/lessons')
def lessons():
    return render_template('lessons.html')


@app.route('/progress')
def score():
    return render_template('progress.html')


@app.route('/streak')
def streak():
    return render_template('streak.html')


@app.route('/timed')
def timed():
    return render_template('timed.html')


@app.route('/quests')
def quests():
    return render_template('quests.html')


@app.route('/vocabulary')
def vocabulary():
    return render_template('vocabulary.html')


@app.route('/profile')
def profile():
    return render_template('profile.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/ebrw_info')
def ebrw_info():
    return render_template('ebrw_info.html')


@app.route('/lesson')
def lesson():
    return render_template('lesson.html')


if __name__ == '__main__':
    app.run(debug=True, port=8000)