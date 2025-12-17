import sqlite3
import os
import random
from typing import List, Dict, Any

def generate_demo_questions(count: int = 100) -> List[Dict[str, Any]]:
    """Generate demo SAT-style questions."""
    questions = []
    
    # Common subjects and topics
    subjects = ['Math', 'Reading', 'Writing and Language']
    math_topics = ['Algebra', 'Geometry', 'Problem Solving', 'Data Analysis', 'Advanced Math']
    reading_topics = ['History', 'Science', 'Literature', 'Social Studies']
    writing_topics = ['Grammar', 'Rhetoric', 'Vocabulary in Context']
    difficulties = ['Easy', 'Medium', 'Hard']
    
    for i in range(1, count + 1):
        subject = random.choice(subjects)
        difficulty = random.choice(difficulties)
        
        if subject == 'Math':
            topic = random.choice(math_topics)
            question_text = generate_math_question(topic, difficulty)
            options = generate_math_options(question_text)
            correct = options[0]  # First option is correct for math
        elif subject == 'Reading':
            topic = random.choice(reading_topics)
            question_text, options, correct = generate_reading_question(topic, difficulty)
        else:  # Writing and Language
            topic = random.choice(writing_topics)
            question_text, options, correct = generate_writing_question(topic, difficulty)
        
        questions.append({
            'QuestionID': f'demo_{i}',
            'Domain': subject,
            'Skill': topic,
            'Text': f'This is a {difficulty.lower()} {subject} question about {topic}.',
            'Question': question_text,
            'Option1': options[0],
            'Option2': options[1],
            'Option3': options[2],
            'Option4': options[3],
            'Correct': correct,
            'Explanation': f'Explanation for question {i}: The correct answer is {correct} because...',
            'Difficulty': difficulty
        })
    
    return questions

def generate_math_question(topic: str, difficulty: str) -> str:
    """Generate a math question based on topic and difficulty."""
    if topic == 'Algebra':
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        c = random.randint(1, 5)
        if difficulty == 'Easy':
            return f'If {a}x + {b} = {a*2 + b}, what is the value of x?'
        else:
            return f'If {a}(x + {b}) = {a*(b+2)}, what is the value of x?'
    
    elif topic == 'Geometry':
        side = random.randint(5, 15)
        if difficulty == 'Easy':
            return f'What is the area of a square with side length {side}?'
        else:
            return f'What is the length of the diagonal of a square with side length {side}?'
    
    else:  # Default math question
        return f'What is {random.randint(1,10)} + {random.randint(1,10)}?'

def generate_math_options(question: str) -> List[str]:
    """Generate plausible multiple choice options for math questions."""
    # Initialize default values
    correct = 2  # Default correct answer
    options = ['2', '3', '4', '5']  # Default options
    
    if 'area of a square' in question or 'diagonal' in question:
        # Extract the side length from the question
        words = question.split()
        side = None
        for i, word in enumerate(words):
            if word.isdigit():
                side = int(word)
                break
        
        # Default side length if none found
        if side is None:
            side = 10  # Default side length
            
        if 'area' in question:
            correct = side * side
            options = [
                str(correct),
                str(side * 4),  # Perimeter
                str(side * side * 2),  # Double area
                str(side * side // 2)  # Half area
            ]
        else:  # diagonal
            correct = round(side * (2 ** 0.5), 2)
            options = [
                str(correct),
                str(side * 2),  # Double side
                str(side),  # Same as side
                str(round(side / (2 ** 0.5), 2))  # Side / sqrt(2)
            ]
    else:  # Basic algebra
        # Extract numbers from question
        nums = [int(s) for s in question.split() if s.isdigit()]
        if len(nums) >= 2:
            a, b = nums[0], nums[1]
            correct = 2 if 'x' in question else a + b
            options = [
                str(correct),
                str(correct + random.randint(1, 3)),
                str(correct - random.randint(1, 3)),
                str(correct + random.randint(4, 6))
            ]
    
    random.shuffle(options)
    # Make sure correct is first (will be used as correct answer)
    if str(correct) in options:
        options.remove(str(correct))
    return [str(correct)] + options

def generate_reading_question(topic: str, difficulty: str) -> tuple:
    """Generate a reading comprehension question."""
    passages = {
        'History': 'The American Revolution was a period in the late 18th century...',
        'Science': 'Photosynthesis is the process by which green plants...',
        'Literature': 'In the opening lines of the novel, the protagonist...',
        'Social Studies': 'The concept of supply and demand is fundamental to...'
    }
    
    questions = {
        'History': 'What was the main cause of the conflict described?',
        'Science': 'What is the primary purpose of the process described?',
        'Literature': 'What can be inferred about the character based on this passage?',
        'Social Studies': 'What economic principle is being illustrated?'
    }
    
    passage = passages.get(topic, 'This is a sample reading passage.')
    question = questions.get(topic, 'What is the main idea of this passage?')
    
    options = [
        'A plausible but incorrect option 1',
        'A plausible but incorrect option 2',
        'A plausible but incorrect option 3',
        'The correct answer to the question'
    ]
    
    if difficulty == 'Hard':
        options = [
            'A subtle inference that requires careful reading',
            'A detail that is mentioned but not the main point',
            'An assumption not supported by the text',
            'The correct nuanced interpretation'
        ]
    
    random.shuffle(options)
    return f"{passage}\n\n{question}", options, options[-1]

def generate_writing_question(topic: str, difficulty: str) -> tuple:
    """Generate a writing/language question."""
    if topic == 'Grammar':
        sentences = [
            'The team of researchers (is/are) preparing their findings.',
            'Neither the students nor the teacher (was/were) aware of the schedule change.',
            'Each of the participants (has/have) completed their assignment.'
        ]
        question = f"Which of the following correctly completes the sentence?\n\n{random.choice(sentences)}"
        options = [
            'is/was/has',
            'are/were/have',
            'is/were/has',
            'are/was/have'
        ]
    else:  # Vocabulary or Rhetoric
        words = ['ephemeral', 'ubiquitous', 'quintessential', 'meticulous']
        word = random.choice(words)
        question = f"Which of the following is the best definition of '{word}'?"
        options = [
            'lasting for a very short time' if word == 'ephemeral' else 'existing everywhere' if word == 'ubiquitous' else 'representing the most perfect example' if word == 'quintessential' else 'showing great attention to detail',
            'difficult to understand',
            'occurring every year',
            'having great power or influence'
        ]
    
    return question, options, options[0]

def add_questions_to_db(questions: List[Dict[str, Any]]) -> int:
    """Add generated questions to the database."""
    db_path = os.path.join(os.path.dirname(__file__), 'question_bank.db')
    
    if not os.path.exists(db_path):
        print("Error: question_bank.db not found.")
        return 0
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        added = 0
        for q in questions:
            try:
                cursor.execute("""
                    INSERT INTO QUESTIONS 
                    (QuestionID, Domain, Skill, Text, Question, 
                     Option1, Option2, Option3, Option4, 
                     Correct, Explanation, Difficulty)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    q['QuestionID'],
                    q['Domain'],
                    q['Skill'],
                    q['Text'],
                    q['Question'],
                    q['Option1'],
                    q['Option2'],
                    q['Option3'],
                    q['Option4'],
                    q['Correct'],
                    q['Explanation'],
                    q['Difficulty']
                ))
                added += 1
            except sqlite3.IntegrityError:
                # Skip duplicate QuestionID
                continue
        
        conn.commit()
        return added
    
    except Exception as e:
        print(f"Error adding questions: {e}")
        conn.rollback()
        return 0
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("Generating 100 demo questions...")
    demo_questions = generate_demo_questions(100)
    print(f"Adding {len(demo_questions)} questions to the database...")
    added = add_questions_to_db(demo_questions)
    print(f"Successfully added {added} new questions to the database.")
    
    # Create duplicates of the new questions
    print("Creating duplicates of the new questions...")
    os.system("python duplicate_questions.py")
