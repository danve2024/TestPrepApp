# Vocabulary questions data moved from run.py for modularity

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


# Reading/Comprehension vocabulary questions moved from run.py
VOCABULARY_QUESTIONS = [
    {
        "type": "multiple_choice",
        "text": "While many critics have dismissed video games as mere entertainment, recent studies suggest they develop valuable cognitive skills. Research indicates that strategic games improve problem-solving abilities, while fast-paced action games enhance visual processing and attention to detail.",
        "question": "The author's primary purpose in the passage is most likely to:",
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
        "text": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions.",
        "question": "The tone of the passage can best be described as:",
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
        "text": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions.",
        "question": "In context, the phrase 'cultural vandalism' primarily serves to:",
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
        "text": "First, consider the economic benefits of renewable energy. Next, examine the environmental advantages. Finally, assess the technological feasibility of widespread adoption. Each perspective reveals compelling reasons to transition from fossil fuels.",
        "question": "Which choice best describes the overall structure of the passage?",
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
        "text": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions.",
        "question": "The author most likely mentions 'digital subscriptions' in order to:",
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
        "text": "The decision to cut funding for public libraries represents nothing short of cultural vandalism. These institutions serve as vital community hubs, providing access to knowledge for those who cannot afford personal book collections or digital subscriptions.",
        "question": "Which choice most accurately captures how the author of the passage uses the term 'vital'?",
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
