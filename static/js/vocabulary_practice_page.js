// Audio elements
const correctSound = document.getElementById('correctSound');
const incorrectSound = document.getElementById('incorrectSound');

// Function to play sound based on answer
function playAnswerSound(isCorrect) {
    // Reset audio to start
    correctSound.currentTime = 0;
    incorrectSound.currentTime = 0;

    // Stop any currently playing audio
    correctSound.pause();
    incorrectSound.pause();

    // Play the appropriate sound
    if (isCorrect) {
        correctSound.play().catch(e => {
            console.log('Audio play failed:', e);
        });
    } else {
        incorrectSound.play().catch(e => {
            console.log('Audio play failed:', e);
        });
    }
}

// For regular multiple choice questions
function selectOption(option) {
    document.querySelectorAll('.option-button').forEach(btn => {
        btn.classList.remove('selected');
    });

    event.target.classList.add('selected');
    document.getElementById('selected_option').value = option;
    document.getElementById('submitButton').disabled = false;
}

// For Duolingo-style fill in the blanks
function selectWord(word) {
    // Don't proceed if already answered or during animation
    if (document.querySelector('.answered') || document.querySelector('.flying-word')) {
        return;
    }

    const blankSpace = document.getElementById('blankSpace');
    const selectedOption = document.getElementById('selected_option');

    // Clear previous selection
    blankSpace.innerHTML = '';
    selectedOption.value = word;

    // Create flying word effect
    const wordBubble = event.target;
    const wordRect = wordBubble.getBoundingClientRect();
    const blankRect = blankSpace.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    // Create flying element
    const flyingWord = document.createElement('div');
    flyingWord.className = 'word-bubble flying-word';
    flyingWord.textContent = word;
    flyingWord.style.position = 'fixed';
    flyingWord.style.left = wordRect.left + 'px';
    flyingWord.style.top = (wordRect.top + scrollTop) + 'px';
    flyingWord.style.width = wordRect.width + 'px';
    flyingWord.style.transform = 'scale(1)';
    flyingWord.style.zIndex = '1000';
    flyingWord.style.transition = 'none';
    flyingWord.style.pointerEvents = 'none';

    // Copy all styles from the original bubble
    flyingWord.style.background = getComputedStyle(wordBubble).background;
    flyingWord.style.color = getComputedStyle(wordBubble).color;
    flyingWord.style.borderRadius = getComputedStyle(wordBubble).borderRadius;
    flyingWord.style.fontWeight = getComputedStyle(wordBubble).fontWeight;
    flyingWord.style.boxShadow = getComputedStyle(wordBubble).boxShadow;
    flyingWord.style.fontSize = getComputedStyle(wordBubble).fontSize;
    flyingWord.style.padding = getComputedStyle(wordBubble).padding;

    document.body.appendChild(flyingWord);

    // Disable all word bubbles during animation
    document.querySelectorAll('.word-bubble').forEach(bubble => {
        if (!bubble.classList.contains('flying-word')) {
            bubble.style.pointerEvents = 'none';
            bubble.style.opacity = '0.6';
        }
    });

    // Force reflow
    flyingWord.offsetHeight;

    // Animate to blank space
    flyingWord.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
    flyingWord.style.left = (blankRect.left + (blankRect.width - wordRect.width) / 2) + 'px';
    flyingWord.style.top = (blankRect.top + scrollTop) + 'px';
    flyingWord.style.transform = 'scale(0.9)';

    setTimeout(() => {
        flyingWord.remove();

        // Add word to blank space
        const selectedWord = document.createElement('div');
        selectedWord.className = 'selected-word-bubble';
        selectedWord.textContent = word;
        blankSpace.appendChild(selectedWord);

        // Enable submit button
        document.getElementById('submitButton').disabled = false;

        // Re-enable word bubbles (if not answered)
        if (!document.querySelector('.answered')) {
            document.querySelectorAll('.word-bubble').forEach(bubble => {
                if (!bubble.classList.contains('flying-word') &&
                    !bubble.classList.contains('used-correct') &&
                    !bubble.classList.contains('used-incorrect') &&
                    !bubble.classList.contains('correct-answer')) {
                    bubble.style.pointerEvents = 'auto';
                    bubble.style.opacity = '1';
                }
            });
        }

        // Add bounce animation to the placed word
        selectedWord.style.animation = 'bounceIn 0.5s ease-out';
    }, 600);
}

// For pairs matching
let selectedWord = null;
let selectedDefinition = null;

function selectMatchingItem(element) {
    if (element.classList.contains('word-item')) {
        // Select word
        document.querySelectorAll('.word-item').forEach(item => {
            item.classList.remove('selected');
        });
        element.classList.add('selected');
        selectedWord = element.getAttribute('data-word');
    } else if (element.classList.contains('definition-item')) {
        // Select definition
        document.querySelectorAll('.definition-item').forEach(item => {
            item.classList.remove('selected');
        });
        element.classList.add('selected');
        selectedDefinition = element.getAttribute('data-definition');
    }

    // Check if we have both selected and try to match
    if (selectedWord && selectedDefinition) {
        // Store the pair
        document.getElementById(`pair_${selectedWord}`).value = selectedDefinition;

        // Visual feedback
        const wordElement = document.querySelector(`.word-item[data-word="${selectedWord}"]`);
        const defElement = document.querySelector(`.definition-item[data-definition="${selectedDefinition}"]`);

        wordElement.classList.add('matched');
        defElement.classList.add('matched');

        // Add connection line animation
        createConnectionLine(wordElement, defElement);

        // Reset selection
        selectedWord = null;
        selectedDefinition = null;
        document.querySelectorAll('.word-item, .definition-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Check if all pairs are matched
        checkAllPairsMatched();
    }
}

function createConnectionLine(wordElement, defElement) {
    const wordRect = wordElement.getBoundingClientRect();
    const defRect = defElement.getBoundingClientRect();
    const container = document.querySelector('.pairs-matching-container');

    const line = document.createElement('div');
    line.className = 'connection-line';
    line.style.position = 'absolute';
    line.style.left = (wordRect.right - container.getBoundingClientRect().left) + 'px';
    line.style.top = (wordRect.top + wordRect.height / 2 - container.getBoundingClientRect().top) + 'px';
    line.style.width = '0px';
    line.style.height = '2px';
    line.style.backgroundColor = '#4caf50';
    line.style.transformOrigin = 'left center';
    line.style.transition = 'width 0.4s ease-out';
    line.style.zIndex = '1';

    container.style.position = 'relative';
    container.appendChild(line);

    // Calculate line length and angle
    const deltaX = defRect.left - wordRect.right;
    const deltaY = (defRect.top + defRect.height / 2) - (wordRect.top + wordRect.height / 2);
    const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI;

    line.style.width = length + 'px';
    line.style.transform = `rotate(${angle}deg)`;

    // Remove line after animation
    setTimeout(() => {
        line.style.opacity = '0.7';
    }, 1000);
}

function checkAllPairsMatched() {
    const allWords = document.querySelectorAll('.word-item');
    const allMatched = Array.from(allWords).every(word => word.classList.contains('matched'));

    if (allMatched) {
        document.getElementById('submitButton').disabled = false;
    }
}

// Function to initialize word bank click events
function initializeWordBank() {
    const wordBubbles = document.querySelectorAll('#wordBank .word-bubble');

    wordBubbles.forEach(bubble => {
        // Only add event listeners to interactive bubbles
        if (!bubble.classList.contains('used-correct') &&
            !bubble.classList.contains('used-incorrect') &&
            !bubble.classList.contains('correct-answer')) {

            // Remove any existing event listeners by cloning
            const newBubble = bubble.cloneNode(true);
            bubble.parentNode.replaceChild(newBubble, bubble);
        }
    });

    // Re-select after cloning and add fresh event listeners
    const freshBubbles = document.querySelectorAll('#wordBank .word-bubble');

    freshBubbles.forEach(bubble => {
        if (!bubble.classList.contains('used-correct') &&
            !bubble.classList.contains('used-incorrect') &&
            !bubble.classList.contains('correct-answer')) {

            bubble.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const word = this.getAttribute('data-word');
                if (word) {
                    selectWord(word);
                }
            });

            // Add visual feedback
            bubble.style.cursor = 'pointer';
            bubble.style.opacity = '1';
        } else {
            // Make non-interactive bubbles look disabled
            bubble.style.cursor = 'default';
            bubble.style.opacity = '0.6';
        }
    });
    // Also play sound when form is submitted (for immediate feedback)
    document.addEventListener('submit', function(e) {
    if (e.target && e.target.id === 'quizForm') {
        // This will play the sound when the page reloads with results
        // The actual sound will be played in DOMContentLoaded when the feedback is shown
    }
});
}

// Initialize all interactions when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize pairs matching if needed
    const wordItems = document.querySelectorAll('.word-item');
    const definitionItems = document.querySelectorAll('.definition-item');

    if (wordItems.length > 0) {
        wordItems.forEach(item => {
            item.addEventListener('click', function() {
                selectMatchingItem(this);
            });
        });

        definitionItems.forEach(item => {
            item.addEventListener('click', function() {
                selectMatchingItem(this);
            });
        });
    }

    // Initialize word bank interactions for fill-in-the-blanks
    const wordBank = document.getElementById('wordBank');
    if (wordBank) {
        initializeWordBank();
    }

    // Play sound if we're on an answered question
    const feedbackElement = document.getElementById('feedback');
    if (feedbackElement) {
        const isCorrect = feedbackElement.style.color === 'green' ||
                         feedbackElement.textContent.includes('✓');
        playAnswerSound(isCorrect);
    }
});

// Also play sound when form is submitted (for immediate feedback)
document.addEventListener('submit', function(e) {
    if (e.target && e.target.id === 'quizForm') {
        // This will play the sound when the page reloads with results
        // The actual sound will be played in DOMContentLoaded when the feedback is shown
    }
});