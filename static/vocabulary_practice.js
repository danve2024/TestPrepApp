// Список слов
const flashcards = [
    {word: "Apple", translation: "Яблоко"},
    {word: "Book", translation: "Книга"},
    {word: "House", translation: "Дом"},
    {word: "Sun", translation: "Солнце"}
];

let currentIndex = 0;

const flashcard = document.getElementById("flashcard");
const wordText = document.getElementById("wordText");
const translationText = document.getElementById("translationText");

function showCard(index) {
    wordText.textContent = flashcards[index].word;
    translationText.textContent = flashcards[index].translation;
    flashcard.classList.remove("flipped");
}

flashcard.addEventListener("click", () => {
    flashcard.classList.toggle("flipped");
});

document.getElementById("learnedBtn").addEventListener("click", () => {
    nextCard(true);
});
document.getElementById("repeatBtn").addEventListener("click", () => {
    nextCard(false);
});

function nextCard(learned) {
    // Здесь можно сохранять прогресс
    currentIndex++;
    if(currentIndex >= flashcards.length) {
        alert("Lesson complete!");
        currentIndex = 0; // начать заново
    }
    showCard(currentIndex);
}

// Показ первой карточки
showCard(currentIndex);