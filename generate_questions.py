"""
Generate new SAT-style English questions to reach 3000 total questions.
Uses patterns from existing questions to create similar but unique questions.
"""
import sqlite3
import random
import os
import hashlib
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), 'question_bank.db')

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize database schema."""
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

def count_questions():
    """Count current questions in database."""
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM QUESTIONS")
        return cur.fetchone()[0]

def generate_question_id():
    """Generate a unique question ID."""
    return hashlib.md5(f"{random.random()}{random.randint(10000, 99999)}".encode()).hexdigest()[:8]

# Question templates based on SAT question types
QUESTION_TEMPLATES = {
    'words_in_context': {
        'domain': 'Craft and Structure',
        'skill': 'Words in Context',
        'passage_templates': [
            "The researcher's approach to the problem was {adjective}, demonstrating a {quality} that few others possessed.",
            "In analyzing the data, the team discovered that the initial hypothesis was {adjective}, requiring a complete {noun} of their methodology.",
            "The author's {adjective} writing style captivated readers, who found her {noun} both engaging and thought-provoking.",
            "The scientist's {adjective} observations led to a {noun} breakthrough in understanding the phenomenon.",
            "The historian's {adjective} examination of the documents revealed {noun} insights into the period.",
            "The artist's {adjective} technique showcased a {noun} that distinguished her work from contemporaries.",
            "The philosopher's {adjective} argument presented a {noun} that challenged conventional thinking.",
            "The economist's {adjective} analysis provided {noun} into market trends.",
        ],
        'question_templates': [
            "As used in the text, what does the word \"{word}\" most nearly mean?",
            "As used in the text, what does the phrase \"{phrase}\" most nearly mean?",
        ],
        'word_options': [
            ('meticulous', ['careful', 'hasty', 'casual', 'random']),
            ('profound', ['superficial', 'deep', 'obvious', 'simple']),
            ('ambiguous', ['clear', 'uncertain', 'definite', 'obvious']),
            ('elaborate', ['simple', 'detailed', 'brief', 'basic']),
            ('substantial', ['minor', 'significant', 'trivial', 'negligible']),
            ('novel', ['traditional', 'new', 'common', 'typical']),
            ('coherent', ['confusing', 'logical', 'random', 'disjointed']),
            ('implicit', ['explicit', 'implied', 'obvious', 'clear']),
            ('explicit', ['hidden', 'clear', 'vague', 'ambiguous']),
            ('comprehensive', ['limited', 'complete', 'partial', 'incomplete']),
            ('precise', ['vague', 'exact', 'approximate', 'general']),
            ('vague', ['clear', 'unclear', 'specific', 'precise']),
            ('subtle', ['obvious', 'delicate', 'blatant', 'direct']),
            ('obscure', ['famous', 'unclear', 'well-known', 'prominent']),
            ('conspicuous', ['hidden', 'noticeable', 'invisible', 'subtle']),
        ]
    },
    'text_completion': {
        'domain': 'Expression of Ideas',
        'skill': 'Transitions',
        'passage_templates': [
            "The study of ancient civilizations has long fascinated historians. {transition} recent archaeological discoveries have {verb} our understanding of these cultures.",
            "Climate change poses significant challenges to ecosystems worldwide. {transition} some species have demonstrated remarkable {noun} to changing conditions.",
            "The development of artificial intelligence has accelerated rapidly in recent years. {transition} concerns about its {noun} continue to grow.",
            "Literary analysis requires careful examination of both form and content. {transition} understanding the {noun} context is equally important.",
            "Scientific research depends on rigorous methodology and peer review. {transition} the {noun} of results remains a critical concern.",
            "The preservation of historical documents requires specialized techniques. {transition} digital archiving has {verb} new possibilities for conservation.",
            "Urban planning must balance growth with sustainability. {transition} innovative design solutions are {verb} this challenge.",
        ],
        'question_templates': [
            "Which choice completes the text with the most logical and precise word or phrase?",
        ],
        'transition_options': [
            ('However', ['Therefore', 'Similarly', 'Consequently', 'Furthermore']),
            ('Moreover', ['Nevertheless', 'Instead', 'However', 'Therefore']),
            ('Consequently', ['However', 'Additionally', 'Similarly', 'Therefore']),
            ('Furthermore', ['Nevertheless', 'Instead', 'However', 'Therefore']),
            ('Nevertheless', ['Therefore', 'Additionally', 'Similarly', 'Furthermore']),
            ('Additionally', ['However', 'Therefore', 'Instead', 'Nevertheless']),
            ('Similarly', ['However', 'Therefore', 'Instead', 'Nevertheless']),
        ]
    },
    'inferences': {
        'domain': 'Information and Ideas',
        'skill': 'Inferences',
        'passage_templates': [
            "Recent studies in cognitive psychology have revealed that memory formation is more complex than previously understood. Researchers found that the process involves multiple brain regions working in concert, with each region contributing to different aspects of memory encoding and retrieval. The findings suggest that memory is not a single unified system but rather a distributed network of interconnected processes.",
            "The decline of traditional print media has been well-documented over the past two decades. However, recent data indicates that certain niche publications have actually experienced growth during this period. These publications typically focus on specialized topics and maintain dedicated readerships willing to pay premium prices for high-quality content.",
            "Ecological research in forest ecosystems has shown that biodiversity plays a crucial role in ecosystem stability. Studies comparing monoculture forests with diverse forests have consistently demonstrated that the latter are more resilient to disease, pests, and environmental changes. This resilience appears to stem from the complex interactions between different species.",
            "The evolution of language is a subject of ongoing debate among linguists. Some researchers argue that language developed gradually over thousands of years, while others propose that it emerged relatively suddenly in human history. Recent genetic studies have provided new evidence suggesting that the capacity for complex language may have developed earlier than previously thought.",
            "The relationship between technology and education has transformed significantly in recent decades. While early educational technology focused primarily on delivering content, modern approaches emphasize interactive learning and personalized instruction. This shift reflects a broader understanding of how students learn most effectively.",
        ],
        'question_templates': [
            "Which choice most logically completes the text?",
            "It can most reasonably be inferred from the text that",
            "The text most strongly suggests that",
        ]
    },
    'central_ideas': {
        'domain': 'Information and Ideas',
        'skill': 'Central Ideas and Details',
        'passage_templates': [
            "The concept of sustainable development has evolved significantly since its introduction in the 1980s. Initially focused primarily on environmental conservation, the framework now encompasses economic growth, social equity, and environmental protection as interconnected goals. This holistic approach recognizes that long-term prosperity requires balancing these three dimensions.",
            "The Renaissance period marked a fundamental shift in European thought and culture. Artists, scientists, and philosophers began to question traditional authorities and explore new ways of understanding the world. This intellectual movement laid the groundwork for the scientific revolution and modern Western thought.",
            "The development of the printing press in the fifteenth century revolutionized the spread of information throughout Europe. Prior to this innovation, books were rare and expensive, accessible primarily to the wealthy and educated elite. The printing press made knowledge more widely available, contributing to increased literacy rates and the democratization of learning.",
            "Marine ecosystems face numerous threats from human activities, including overfishing, pollution, and climate change. Conservation efforts have focused on establishing protected areas and regulating fishing practices. However, scientists argue that comprehensive solutions require addressing multiple factors simultaneously rather than focusing on individual threats in isolation.",
        ],
        'question_templates': [
            "Which choice best states the main idea of the text?",
            "The central claim of the text is that",
        ]
    },
    'command_of_evidence': {
        'domain': 'Information and Ideas',
        'skill': 'Command of Evidence',
        'passage_templates': [
            "Educational researchers have found that student engagement significantly impacts learning outcomes. Studies show that students who actively participate in class discussions and collaborative activities demonstrate better retention of material and improved critical thinking skills. Additionally, research indicates that engagement levels correlate with long-term academic success.",
            "The preservation of historical documents requires careful environmental controls. Temperature, humidity, and light exposure must be carefully regulated to prevent deterioration. Without proper conditions, valuable historical records can be permanently damaged. Modern archival facilities employ sophisticated climate control systems to maintain optimal preservation conditions.",
            "The impact of social media on mental health has been the subject of extensive research. Some studies suggest that excessive social media use may contribute to increased anxiety and depression, particularly among adolescents. However, other research indicates that social media can also provide valuable support networks and opportunities for connection.",
        ],
        'question_templates': [
            "Which quotation from the text most directly supports the answer to the previous question?",
            "Which finding, if true, would most directly support the claim?",
        ]
    },
    'rhetorical_synthesis': {
        'domain': 'Expression of Ideas',
        'skill': 'Rhetorical Synthesis',
        'passage_templates': [
            "While researching a topic, a student has taken the following notes:\n- The Great Wall of China was constructed over multiple dynasties.\n- It spans approximately 13,000 miles across northern China.\n- The wall served both defensive and symbolic purposes.\n- Modern conservation efforts face challenges from tourism and environmental factors.\n\nThe student wants to provide an overview of the Great Wall's historical significance and current status.",
            "While researching a topic, a student has taken the following notes:\n- Renewable energy sources include solar, wind, and hydroelectric power.\n- These sources produce minimal greenhouse gas emissions.\n- Initial installation costs can be high, but long-term savings are significant.\n- Many countries are investing heavily in renewable energy infrastructure.\n\nThe student wants to explain the benefits and challenges of renewable energy adoption.",
        ],
        'question_templates': [
            "Which choice most effectively uses relevant information from the notes to accomplish this goal?",
        ]
    }
}

def generate_words_in_context_question(template_data, difficulty):
    """Generate a 'Words in Context' question."""
    passage_template = random.choice(template_data['passage_templates'])
    question_template = random.choice(template_data['question_templates'])
    word_pair = random.choice(template_data['word_options'])
    
    word, correct_options = word_pair
    correct = correct_options[0]  # First option is correct
    wrong_options = correct_options[1:]
    
    # Fill in passage template
    adjectives = ['meticulous', 'profound', 'careful', 'thorough', 'detailed', 'precise', 'subtle', 'comprehensive']
    qualities = ['attention to detail', 'dedication', 'precision', 'expertise', 'skill', 'insight', 'understanding']
    nouns = ['revision', 'reconsideration', 'analysis', 'examination', 'review', 'breakthrough', 'innovation']
    verbs = ['transformed', 'revolutionized', 'enhanced', 'improved', 'advanced', 'refined']
    
    passage = passage_template.format(
        adjective=random.choice(adjectives),
        quality=random.choice(qualities),
        noun=random.choice(nouns),
        verb=random.choice(verbs)
    )
    
    # Insert the word into passage if not already there
    if word not in passage.lower():
        # Replace one of the adjectives with the word
        passage = passage.replace(random.choice(adjectives), word, 1)
    
    # Create question
    question = question_template.format(word=word, phrase=f"{word} approach")
    
    # Create options - correct answer plus 3 wrong ones
    options = [correct] + random.sample(wrong_options, 3)
    random.shuffle(options)
    correct_idx = options.index(correct)
    correct_letter = ['A', 'B', 'C', 'D'][correct_idx]
    
    return {
        'passage': passage,
        'question': question,
        'options': options,
        'correct': correct_letter,
        'explanation': f'The word "{word}" in this context means {correct.lower()}, as it best fits the meaning of the passage.'
    }

def generate_text_completion_question(template_data, difficulty):
    """Generate a 'Text Completion' question."""
    passage_template = random.choice(template_data['passage_templates'])
    question_template = random.choice(template_data['question_templates'])
    transition_pair = random.choice(template_data['transition_options'])
    
    transition, other_transitions = transition_pair
    correct = transition
    
    # Fill in passage
    verbs = ['revolutionized', 'transformed', 'enhanced', 'improved', 'advanced', 'addressed', 'solved']
    nouns = ['adaptability', 'resilience', 'flexibility', 'durability', 'stability', 'impact', 'implications']
    contexts = ['historical', 'cultural', 'social', 'political', 'economic', 'environmental']
    validities = ['validity', 'reliability', 'accuracy', 'precision', 'credibility']
    
    passage = passage_template.format(
        transition=transition,
        verb=random.choice(verbs),
        noun=random.choice(nouns + contexts + validities)
    )
    
    # Remove the transition from passage to make it a blank
    passage = passage.replace(transition, '______')
    
    question = question_template
    
    # Create options
    options = [correct] + random.sample(other_transitions, 3)
    random.shuffle(options)
    correct_idx = options.index(correct)
    correct_letter = ['A', 'B', 'C', 'D'][correct_idx]
    
    return {
        'passage': passage,
        'question': question,
        'options': options,
        'correct': correct_letter,
        'explanation': f'"{correct}" is the most logical choice as it best connects the ideas in the passage.'
    }

def generate_inference_question(template_data, difficulty):
    """Generate an 'Inferences' question."""
    passage = random.choice(template_data['passage_templates'])
    question_template = random.choice(template_data['question_templates'])
    
    # Generate plausible options based on passage content
    if 'memory' in passage.lower():
        options = [
            "Memory formation involves multiple brain systems working together.",
            "Memory is stored in a single location in the brain.",
            "Memory encoding and retrieval are identical processes.",
            "Memory research has reached its final conclusions."
        ]
        correct_idx = 0
    elif 'media' in passage.lower() or 'publication' in passage.lower():
        options = [
            "Some specialized publications have succeeded despite industry trends.",
            "All print media is experiencing decline.",
            "Digital media has completely replaced print media.",
            "Niche publications are less valuable than mainstream ones."
        ]
        correct_idx = 0
    elif 'biodiversity' in passage.lower() or 'ecosystem' in passage.lower() or 'forest' in passage.lower():
        options = [
            "Diverse ecosystems are generally more stable than simple ones.",
            "Monoculture forests are more resilient to change.",
            "Species diversity has no impact on ecosystem health.",
            "All forest types respond similarly to environmental stress."
        ]
        correct_idx = 0
    elif 'language' in passage.lower():
        options = [
            "The development of language remains a topic of ongoing research.",
            "Language development is fully understood by scientists.",
            "All linguists agree on how language evolved.",
            "Language capacity developed only recently in human history."
        ]
        correct_idx = 0
    elif 'technology' in passage.lower() or 'education' in passage.lower():
        options = [
            "Educational approaches have evolved to emphasize interactive learning.",
            "Technology has had no impact on education.",
            "Early educational technology was more effective than modern approaches.",
            "Personalized instruction is no longer valued in education."
        ]
        correct_idx = 0
    else:
        # Generic options
        options = [
            "The topic discussed has multiple important aspects.",
            "The research findings are definitive and unchanging.",
            "The subject matter is simple and straightforward.",
            "Further investigation is unnecessary."
        ]
        correct_idx = 0
    
    question = question_template
    
    correct_letter = ['A', 'B', 'C', 'D'][correct_idx]
    
    return {
        'passage': passage,
        'question': question,
        'options': options,
        'correct': correct_letter,
        'explanation': 'This choice most logically follows from the information presented in the text.'
    }

def generate_central_ideas_question(template_data, difficulty):
    """Generate a 'Central Ideas' question."""
    passage = random.choice(template_data['passage_templates'])
    question_template = random.choice(template_data['question_templates'])
    
    if 'sustainable' in passage.lower():
        options = [
            "Sustainable development requires balancing economic, social, and environmental goals.",
            "Environmental conservation is the only important aspect of development.",
            "Economic growth should take priority over other concerns.",
            "Social equity is unrelated to environmental protection."
        ]
        correct_idx = 0
    elif 'renaissance' in passage.lower():
        options = [
            "The Renaissance represented a fundamental shift toward questioning traditional authority.",
            "The Renaissance had no lasting impact on European culture.",
            "Art and science developed independently during this period.",
            "Traditional authorities remained unchallenged during the Renaissance."
        ]
        correct_idx = 0
    elif 'printing' in passage.lower():
        options = [
            "The printing press made knowledge more widely accessible.",
            "Books remained rare and expensive after the printing press.",
            "The printing press had no impact on literacy rates.",
            "Only the wealthy benefited from the printing press."
        ]
        correct_idx = 0
    elif 'marine' in passage.lower() or 'ecosystem' in passage.lower():
        options = [
            "Marine conservation requires addressing multiple threats simultaneously.",
            "Individual conservation efforts are sufficient to protect marine ecosystems.",
            "Overfishing is the only significant threat to marine ecosystems.",
            "Climate change has no impact on marine environments."
        ]
        correct_idx = 0
    else:
        options = [
            "The topic has evolved to encompass multiple interconnected dimensions.",
            "The subject matter has remained unchanged over time.",
            "Only one aspect of the topic is important.",
            "The topic is no longer relevant."
        ]
        correct_idx = 0
    
    question = question_template
    
    correct_letter = ['A', 'B', 'C', 'D'][correct_idx]
    
    return {
        'passage': passage,
        'question': question,
        'options': options,
        'correct': correct_letter,
        'explanation': 'This choice best captures the main idea presented in the text.'
    }

def generate_command_of_evidence_question(template_data, difficulty):
    """Generate a 'Command of Evidence' question."""
    passage = random.choice(template_data['passage_templates'])
    question_template = random.choice(template_data['question_templates'])
    
    # Extract sentences from passage as potential evidence
    sentences = [s.strip() for s in passage.split('.') if len(s.strip()) > 20]
    
    if len(sentences) >= 2:
        correct_quote = sentences[1] if len(sentences) > 1 else sentences[0]
    else:
        correct_quote = passage[:100] + "..."
    
    # Create plausible but incorrect quote options
    if 'engagement' in passage.lower():
        options = [
            f'"{correct_quote}"',
            '"Students who do not participate show similar outcomes."',
            '"Technology alone determines learning success."',
            '"Traditional lectures are always more effective."'
        ]
        correct_idx = 0
    elif 'preservation' in passage.lower() or 'document' in passage.lower():
        options = [
            f'"{correct_quote}"',
            '"Historical documents require no special care."',
            '"Digital storage is unnecessary for preservation."',
            '"Climate control has no impact on document preservation."'
        ]
        correct_idx = 0
    else:
        options = [
            f'"{correct_quote}"',
            '"The research findings are inconclusive."',
            '"No studies have been conducted on this topic."',
            '"The evidence contradicts the main claim."'
        ]
        correct_idx = 0
    
    question = question_template
    
    correct_letter = ['A', 'B', 'C', 'D'][correct_idx]
    
    return {
        'passage': passage,
        'question': question,
        'options': options,
        'correct': correct_letter,
        'explanation': 'This quotation most directly supports the claim made in the text.'
    }

def generate_rhetorical_synthesis_question(template_data, difficulty):
    """Generate a 'Rhetorical Synthesis' question."""
    passage_template = random.choice(template_data['passage_templates'])
    question_template = random.choice(template_data['question_templates'])
    
    passage = passage_template
    
    # Extract goal from passage
    goal_match = re.search(r'wants to (.*?)\.', passage, re.IGNORECASE)
    goal = goal_match.group(1) if goal_match else "provide information"
    
    # Generate options that synthesize the notes
    if 'Great Wall' in passage:
        options = [
            "The Great Wall of China, constructed over multiple dynasties and spanning approximately 13,000 miles, served both defensive and symbolic purposes throughout its history, though modern conservation efforts now face challenges from tourism and environmental factors.",
            "The Great Wall was built in a single dynasty and has no historical significance.",
            "The Great Wall is only important for tourism purposes.",
            "Conservation efforts have completely solved all challenges facing the Great Wall."
        ]
        correct_idx = 0
    elif 'renewable' in passage.lower() or 'energy' in passage.lower():
        options = [
            "Renewable energy sources such as solar, wind, and hydroelectric power produce minimal greenhouse gas emissions and offer long-term savings, though initial installation costs can be high, leading many countries to invest heavily in renewable energy infrastructure.",
            "Renewable energy has no benefits and is too expensive.",
            "Only solar power is a viable renewable energy source.",
            "Renewable energy requires no initial investment."
        ]
        correct_idx = 0
    else:
        # Generic synthesis
        notes = re.findall(r'- (.+)', passage)
        if notes:
            synthesized = " ".join(notes[:3]) + "."
            options = [
                synthesized,
                "The notes contain no useful information.",
                "Only one aspect of the topic is relevant.",
                "The information contradicts itself."
            ]
        else:
            options = [
                "The information from the notes provides a comprehensive overview.",
                "The notes are irrelevant to the topic.",
                "Only partial information should be used.",
                "The notes contradict each other."
            ]
        correct_idx = 0
    
    question = question_template
    
    correct_letter = ['A', 'B', 'C', 'D'][correct_idx]
    
    return {
        'passage': passage,
        'question': question,
        'options': options,
        'correct': correct_letter,
        'explanation': 'This choice most effectively synthesizes the relevant information from the notes to accomplish the stated goal.'
    }

def generate_question(question_type, difficulty):
    """Generate a question of the specified type."""
    import re
    template_data = QUESTION_TEMPLATES[question_type]
    
    if question_type == 'words_in_context':
        return generate_words_in_context_question(template_data, difficulty)
    elif question_type == 'text_completion':
        return generate_text_completion_question(template_data, difficulty)
    elif question_type == 'inferences':
        return generate_inference_question(template_data, difficulty)
    elif question_type == 'central_ideas':
        return generate_central_ideas_question(template_data, difficulty)
    elif question_type == 'command_of_evidence':
        return generate_command_of_evidence_question(template_data, difficulty)
    elif question_type == 'rhetorical_synthesis':
        return generate_rhetorical_synthesis_question(template_data, difficulty)
    else:
        # Default to inference
        return generate_inference_question(template_data, difficulty)

def main():
    print("Generating questions to reach 3000 total...")
    
    init_db()
    current_count = count_questions()
    print(f"Current questions in database: {current_count}")
    
    needed = 3000 - current_count
    if needed <= 0:
        print(f"Already have {current_count} questions, which is >= 3000. Done!")
        return
    
    print(f"Need to generate {needed} more questions")
    
    # Question type distribution
    question_types = [
        'words_in_context',
        'text_completion',
        'inferences',
        'central_ideas',
        'command_of_evidence',
        'rhetorical_synthesis'
    ]
    
    # Difficulty distribution (approximately 30% easy, 40% medium, 30% hard)
    difficulties = ['Easy'] * 30 + ['Medium'] * 40 + ['Hard'] * 30
    
    # Domains and skills
    domains = [
        'Information and Ideas',
        'Craft and Structure',
        'Expression of Ideas',
        'Standard English Conventions'
    ]
    
    skills_map = {
        'Information and Ideas': ['Inferences', 'Central Ideas and Details', 'Command of Evidence'],
        'Craft and Structure': ['Words in Context', 'Text Structure and Purpose', 'Cross-Text Connections'],
        'Expression of Ideas': ['Rhetorical Synthesis', 'Transitions'],
        'Standard English Conventions': ['Form, Structure, and Sense']
    }
    
    generated = []
    existing_ids = set()
    
    # Get existing question IDs to avoid duplicates
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT QuestionID FROM QUESTIONS WHERE QuestionID IS NOT NULL")
        existing_ids = {row[0] for row in cur.fetchall()}
    
    print("Generating questions...")
    for i in range(needed):
        question_type = random.choice(question_types)
        difficulty = random.choice(difficulties)
        domain = random.choice(domains)
        skill = random.choice(skills_map.get(domain, ['Inferences']))
        
        try:
            q_data = generate_question(question_type, difficulty)
            
            question_id = generate_question_id()
            
            # Ensure unique ID
            attempts = 0
            while question_id in existing_ids and attempts < 10:
                question_id = generate_question_id()
                attempts += 1
            
            if question_id in existing_ids:
                print(f"Skipping duplicate ID at question {i+1}")
                continue
            
            existing_ids.add(question_id)
            
            generated.append({
                'QuestionID': question_id,
                'Domain': domain,
                'Skill': skill,
                'Text': q_data['passage'],
                'Question': q_data['question'],
                'Option1': q_data['options'][0],
                'Option2': q_data['options'][1],
                'Option3': q_data['options'][2],
                'Option4': q_data['options'][3],
                'Correct': q_data['correct'],
                'Explanation': q_data['explanation'],
                'Difficulty': difficulty
            })
            
            if (i + 1) % 100 == 0:
                print(f"Generated {i + 1}/{needed} questions...")
        except Exception as e:
            print(f"Error generating question {i+1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\nGenerated {len(generated)} questions")
    print("Inserting into database...")
    
    with get_conn() as conn:
        insert_sql = """
            INSERT INTO QUESTIONS (QuestionID, Domain, Skill, Text, Question, Option1, Option2, Option3, Option4, Correct, Explanation, Difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        inserted = 0
        for q in generated:
            try:
                conn.execute(insert_sql, (
                    q['QuestionID'], q['Domain'], q['Skill'], q['Text'], q['Question'],
                    q['Option1'], q['Option2'], q['Option3'], q['Option4'],
                    q['Correct'], q['Explanation'], q['Difficulty']
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                # Skip duplicates
                continue
            except Exception as e:
                print(f"Error inserting question {q['QuestionID']}: {e}")
        
        conn.commit()
    
    print(f"\nSuccessfully inserted {inserted} questions!")
    
    final_count = count_questions()
    print(f"Final question count: {final_count}")

if __name__ == '__main__':
    import re
    main()

