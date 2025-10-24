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
