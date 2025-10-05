const questions = [
    {
        type: "definition",
        question: "Aberration",
        options: [
            "A departure from what is normal",
            "A type of fruit",
            "A musical instrument",
            "A large building"
        ],
        answer: "A departure from what is normal"
    },
    {
        type: "definition",
        question: "Capricious",
        options: [
            "Subject to sudden changes in mood",
            "Extremely careful",
            "Very generous",
            "Full of energy"
        ],
        answer: "Subject to sudden changes in mood"
    },
    {
        type: "definition",
        question: "Ephemeral",
        options: [
            "Lasting a very short time",
            "Extremely heavy",
            "Very happy",
            "Related to water"
        ],
        answer: "Lasting a very short time"
    },
    {
        type: "definition",
        question: "Loquacious",
        options: [
            "Tending to talk a lot",
            "Unwilling to speak",
            "Full of energy",
            "Friendly"
        ],
        answer: "Tending to talk a lot"
    },
    {
        type: "definition",
        question: "Obfuscate",
        options: [
            "To make unclear or confusing",
            "To celebrate",
            "To teach",
            "To destroy"
        ],
        answer: "To make unclear or confusing"
    }
];

let currentIndex = 0;
let selectedOption = null;
let answered = false;

const questionText = document.getElementById("questionText");
const answerButtons = document.getElementById("answerButtons");
const feedback = document.getElementById("feedback");
const backButton = document.getElementById("backButton");

const actionButton = document.createElement("button");
actionButton.className = "start";
actionButton.textContent = "Answer";
actionButton.style.marginTop = "20px";
actionButton.onclick = handleAction;

function showQuestion(index) {
    questionText.textContent = questions[index].question;
    answerButtons.innerHTML = "";
    feedback.textContent = "";
    selectedOption = null;
    answered = false;

    questions[index].options.forEach(option => {
        const btn = document.createElement("button");
        btn.className = "option-button";
        btn.textContent = option;
        btn.onclick = () => selectOption(btn, option);
        answerButtons.appendChild(btn);
    });

    if (!actionButton.parentElement) {
        answerButtons.parentElement.appendChild(actionButton);
    }
    actionButton.textContent = "Answer";
    actionButton.disabled = true;
}

function selectOption(button, option) {
    Array.from(answerButtons.children).forEach(btn => {
        btn.classList.remove("selected");
    });
    button.classList.add("selected");
    selectedOption = option;
    actionButton.disabled = false;
}

function handleAction() {
    if (!answered) {
        checkAnswer();
        answered = true;
        actionButton.textContent = "Continue";
    } else {
        nextQuestion();
    }
}

function checkAnswer() {
    if (selectedOption === questions[currentIndex].answer) {
        feedback.textContent = "Correct!";
        feedback.style.color = "green";
    } else {
        feedback.textContent = "Wrong! Correct: " + questions[currentIndex].answer;
        feedback.style.color = "red";
    }
}

function nextQuestion() {
    currentIndex++;
    if (currentIndex < questions.length) {
        showQuestion(currentIndex);
    } else {
        lessonComplete();
    }
}

function lessonComplete() {
    questionText.textContent = "Lesson Complete!";
    answerButtons.innerHTML = "";
    feedback.textContent = "";
    actionButton.remove();
    backButton.style.display = "inline-block";
}

function backToVocabulary() {
    window.location.href = "vocabulary";
}

showQuestion(currentIndex);
