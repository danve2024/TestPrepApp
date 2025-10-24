# Project File Roles

This document summarizes the role of each major file/folder in the project.

## Application code

- **run.py**
  - Flask app entrypoint and all routes.
  - Handles authentication checks, lessons flow, vocabulary practice flow, and results.
  - Implements session state for:
    - Vocabulary: `questions`, `current_question`, `quiz_score`, `option_orders`, etc.
    - Lessons: `lesson_qids`, `lesson_current_question`, `lesson_quiz_score`, `lesson_initialized`.
  - Lesson-specific logic:
    - Loads random questions from `question_bank.db` using IDs stored in `lesson_qids`.
    - Deterministic shuffle of options per question (`_stable_shuffled_options`) to keep order stable without bloating session.
    - `POST /lesson_answer` evaluates the submitted question (anchored to hidden `question_id`/`q_index`) and renders feedback.
    - `POST /lesson_next` advances to the next lesson question and renders it.

- **question_bank.py**
  - Database adapter and utilities for the lessons question bank.
  - Creates/ensures `question_bank.db`, parses source files, and exposes:
    - `ensure_ready()` to confirm DB availability.
    - `get_random_questions(limit)` to fetch a batch of lesson questions.
    - `get_questions_by_ids(ids)` to resolve a stable set from IDs.
  - Maps DB schema fields to app-ready MCQ dicts, including A–D letter mapping to the actual correct option text.

## Templates (Jinja2)

- **templates/base.html**
  - Global layout: HTML skeleton, common header/footer, and CSS/JS includes.

- **templates/lessons.html**
  - Lessons landing page: lists lessons and entry points.

- **templates/lesson.html**
  - Single lesson page: shows current passage (if any), question prompt, answer UI, and feedback/results.
  - Uses `answered` to toggle between selection UI and feedback.
  - Receives state from server:
    - `question`, `options` (shuffled deterministically), `current_index`, `total_questions`, `score`, `feedback`, `correct_answer`, `quiz_complete`.
  - Includes hidden fields `question_id` and `q_index` on forms to anchor evaluation to the exact question shown.

- **templates/vocabulary_practice.html**
  - Vocabulary practice page (non-DB).
  - Mirrors the same UX pattern:
    - Shuffle order kept per index via `session['option_orders']`.
    - Submit for feedback; Continue to advance.

- **templates/ebrw_info.html**
  - Informational page about the EBRW section (English-based Reading & Writing).

## Static assets

- **static/css/base.css**
  - Global styling, base layout, typography, colors.

- **static/css/practice.css**
  - Page-specific styles for practice/lesson UI:
    - Option buttons, selected/correct/incorrect states.
    - Sticky question header, spacing, and feedback visuals.

- **static/js/theme_toggle.js**
  - Client-side theme switch (e.g., light/dark).

- **static/js/music_control.js**
  - Background music and sound effects control.

- **static/audio/**
  - `correct.mp3`, `incorrect.mp3`, `finish.mp3`, `MainTheme.mp3` for feedback/UX cues.

## Data

- **question_bank.db**
  - SQLite database with lesson questions.
  - Columns include: Domain, Skill, Text (passage), Question, Option1–4, Correct (A–D), Explanation, Difficulty, and a `question_id`.

- (Optional source) **question_bank.txt / PDFs**
  - Raw source that can be parsed and imported into the DB by `question_bank.py`.

## How the flows work

- **Vocabulary practice**
  - On start, questions are placed in session as in-memory objects.
  - `option_orders` keeps a per-index shuffle.
  - `POST /vocabulary_answer` renders feedback for the same question.
  - `POST /vocabulary_next` advances the index.

- **Lessons (DB-backed)**
  - `GET /lesson`:
    - Initializes once per session (`lesson_initialized`).
    - Stores only question IDs (`lesson_qids`) to keep cookies small.
    - Rebuilds the current question from DB each request.
    - Uses deterministic per-question shuffle for stable option order.
  - `POST /lesson_answer`:
    - Reads hidden `question_id` and `q_index`.
    - Evaluates the submitted question and renders feedback without advancing.
  - `POST /lesson_next`:
    - Increments `lesson_current_question` and renders the next question.
  - Results summary is rendered at the end on the same `lesson.html`.

## Summary

- Backend routes live in `run.py`.
- Lessons are DB-driven via `question_bank.py` and `question_bank.db`.
- UI is rendered by Jinja templates (`lesson.html`, `vocabulary_practice.html`, etc.).
- Static assets provide styles, scripts, and sounds.
- Session is kept lean for lessons by storing only IDs and rebuilding from DB, with deterministic shuffling for consistent UI between requests.

## Per-file catalog

Root
- **run.py**: Flask app entrypoint; routing for auth, vocabulary practice, lessons, results; lesson deterministic shuffle; session management.
- **question_bank.py**: SQLite adapter and import utilities for lessons; ensures DB; fetch by IDs/random; maps A–D to correct option text.
- **authentication.py**: Helpers or endpoints for login/auth flows (session checks, user auth utilities).
- **data.py**: Shared data helpers, constants, or legacy in-memory datasets used by parts of the app.
- **email_verify_pg.py**: Email verification page/flow endpoints (send/verify codes, status, redirects).
- **streaks_pg.py**: Streaks page/logic endpoints (calculating and displaying user streaks).
- **wsgi.py**: WSGI entrypoint for deploying the Flask app under a WSGI server.
- **script.sh**: Shell script for project tasks (e.g., setup/run scripts on compatible systems).
- **nohup.out**: Log output from background process runs (not required for app logic).
- **.DS_Store**: macOS metadata file (safe to ignore/delete).

Databases (SQLite)
- **login_info.db**: Stores login-related data (users/credentials metadata).
- **progress_data.db**: Stores user progress, quiz scores, and related metrics.
- **users_data.db**: Additional user profile/state data.
- **question_bank.db**: Lessons question bank (questions, options A–D, correct letter, explanations, passages, difficulty, ids).

Docs
- **docs/PROJECT_FILE_ROLES.md**: This documentation file describing project files.

App package
- **app/config.py**: Application configuration helpers (env-based config, constants).
- **app/context_processors.py**: Injects global variables/settings into all templates.
- **app/services/email_service.py**: Email sending utilities (SMTP wrappers, templating hooks).
- **app/routes/settings.py**: Settings-related routes or blueprint (user preferences, toggles, saving settings).
- **app/data/questions.py**: Source questions/data structures for vocabulary or sample content.

Templates
- **templates/base.html**: Base layout wrapper (common head/body; CSS/JS includes).
- **templates/welcome.html**: Landing/welcome page for first-time or general entry.
- **templates/menu.html**: Main menu/dashboard page.
- **templates/login.html**: Login page template.
- **templates/register.html**: Registration page template.
- **templates/profile.html**: User profile page.
- **templates/progress.html**: Progress dashboard page.
- **templates/quests.html**: Quests overview page.
- **templates/settings.html**: Settings UI.
- **templates/streak.html**: Streaks page UI.
- **templates/verify_pending.html**: Email verification pending page.
- **templates/vocabulary.html**: Vocabulary feature landing/setup page.
- **templates/vocabulary_practice.html**: Vocabulary quiz page (in-memory questions, per-index option shuffle, feedback flow).
- **templates/lessons.html**: Lessons hub page (list/enter lessons).
- **templates/lessons_old.html**: Older lessons page (legacy, for reference or cleanup).
- **templates/lesson.html**: Lesson quiz page (DB-backed questions; deterministic shuffle; feedback/results on same template).
- **templates/ebrw_info.html**: EBRW informational page.
- **templates/timed.html**: Timed practice/test page UI.

Static assets
- **static/css/base.css**: Global styles for layout/theme.
- **static/css/practice.css**: Practice/quiz components (buttons, feedback states, layout helpers).
- **static/css/lessons.css**: Lessons page-specific styles.
- **static/css/profile.css**: Profile page styles.
- **static/css/quests.css**: Quests page styles.
- **static/css/settings.css**: Settings page styles.
- **static/css/streak.css**: Streaks page styles.
- **static/css/vocabulary.css**: Vocabulary page styles.
- **static/js/theme_toggle.js**: Theme switch handling (light/dark).
- **static/js/music_control.js**: Background music and SFX controls.
- **static/js/soft_nav.js**: Soft navigation / PJAX-like helpers (navigate without full reloads).
- **static/js/lessons.js**: Lessons page client behaviors.
- **static/js/lessons_map.js**: Lesson map/visualization.
- **static/js/matrix.js**: Visual effects/utility script.
- **static/js/profile.js**: Profile page interactions.
- **static/js/quests.js**: Quests interactions.
- **static/js/settings.js**: Settings interactions.
- **static/js/streak.js**: Streaks calculations/animations on client.
- **static/js/vocabulary_practice.js**: Shared helpers for vocabulary practice.
- **static/js/vocabulary_practice_page.js**: Vocabulary page orchestration (UI interactions).
- **static/js/vocabulary_practice_quiz.js**: Vocabulary quiz interaction logic.
- **static/audio/MainTheme.mp3**: Background theme.
- **static/audio/correct.mp3, incorrect.mp3, finish.mp3, old_incorrect.mp3**: Feedback sounds.
- **static/question_bank.pdf**: Source content for lessons parser.
- **static/question_bank.txt**: Parsed/exported source for DB import.

Generated / environment
- **__pycache__/**: Python bytecode caches.
- **.venv/**: Python virtual environment (dependencies installed here).
