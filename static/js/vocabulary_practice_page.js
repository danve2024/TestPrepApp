// Vocabulary practice page functionality

// Multiple choice selection
function selectOption(option) {
    document.getElementById('selected_option').value = option;
    
    // Remove selected class from all buttons
    document.querySelectorAll('.option-button').forEach(btn => {
        btn.classList.remove('selected');
    });
    
    // Add selected class to clicked button
    event.target.classList.add('selected');
    
    // Enable submit button
    document.getElementById('submitButton').disabled = false;
}

// Matching pairs functionality aligned with lesson page
class MatchingGame {
    constructor() {
        this.selectedWord = null;
        this.selectedDefinition = null;
        this.matches = new Map();
        this.correctPairs = new Map();
        this.mistakesAllowed = 1; // one mistake allowed; second mistake auto-fails
        this.mistakesMade = 0;

        this.container = document.querySelector('.pairs-matching-container');
        this.svg = this.container ? this.container.querySelector('.match-lines-overlay') : null;

        this.init();
    }

    init() {
        this.loadCorrectPairs();
        this.updateSubmitButton();
    }

    loadCorrectPairs() {
        const questionData = window.questionData || {};
        if (questionData.pairs) {
            questionData.pairs.forEach(pair => this.correctPairs.set(pair.word, pair.definition));
        }
    }

    selectWord(wordElement) {
        if (wordElement.classList.contains('matched') || wordElement.classList.contains('used')) return;
        this.clearSelections();
        this.selectedWord = wordElement;
        wordElement.classList.add('selected');
        if (this.selectedDefinition) this.tryMatch();
    }

    selectDefinition(definitionElement) {
        if (definitionElement.classList.contains('matched') || definitionElement.classList.contains('used')) return;
        this.clearSelections();
        this.selectedDefinition = definitionElement;
        definitionElement.classList.add('selected');
        if (this.selectedWord) this.tryMatch();
    }

    clearSelections() {
        document.querySelectorAll('.match-item.selected').forEach(item => item.classList.remove('selected'));
    }

    tryMatch() {
        if (!(this.selectedWord && this.selectedDefinition)) return;
        const word = this.selectedWord.dataset.value;
        const definition = this.selectedDefinition.dataset.value;
        const isCorrect = this.correctPairs.get(word) === definition;

        this.matches.set(word, definition);
        const hiddenInput = document.getElementById(`pair_${word}`);
        if (hiddenInput) hiddenInput.value = definition;

        this.selectedWord.classList.remove('selected');
        this.selectedDefinition.classList.remove('selected');

        if (isCorrect) {
            this.selectedWord.classList.add('matched', 'correct');
            this.selectedDefinition.classList.add('matched', 'correct');
            this.playSound('correctSound');
        } else {
            this.selectedWord.classList.add('matched', 'incorrect');
            this.selectedDefinition.classList.add('matched', 'incorrect');
            this.mistakesMade++;
            this.playSound('incorrectSound');
            // First mistake: reset the question for a fresh attempt
            if (this.mistakesMade === 1) {
                setTimeout(() => this.resetExercise(), 600);
            }
            // Second mistake: auto-submit as incorrect
            else if (this.mistakesMade > this.mistakesAllowed) {
                this.autoSubmitIncorrect();
            }
        }

        this.selectedWord = null;
        this.selectedDefinition = null;
        this.updateSubmitButton();

        // Draw or redraw lines after every match
        this.redrawLines();
    }

    playSound(id) {
        const sound = document.getElementById(id);
        if (sound) { sound.currentTime = 0; sound.play().catch(() => {}); }
    }

    redrawLines() {
        if (!this.svg) return;
        const setSvgSize = () => {
            const rect = this.container.getBoundingClientRect();
            this.svg.setAttribute('width', rect.width);
            this.svg.setAttribute('height', rect.height);
            this.svg.setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
        };
        const anchorOf = (el, side) => {
            const r = el.getBoundingClientRect();
            const c = this.container.getBoundingClientRect();
            const edgePad = 10; // keep a bit inside the card to avoid clipping under borders
            const x = side === 'right' ? (r.left - c.left + r.width - edgePad) : (r.left - c.left + edgePad);
            const y = (r.top - c.top) + r.height / 2;
            return { x, y };
        };
        const drawSteppedPath = (a, b, color, offsetPx = 0) => {
            const midX = (a.x + b.x) / 2 + offsetPx;
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            const d = `M ${a.x} ${a.y} L ${midX} ${a.y} L ${midX} ${b.y} L ${b.x} ${b.y}`;
            path.setAttribute('d', d);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', color);
            path.setAttribute('stroke-width', '5');
            path.setAttribute('stroke-linecap', 'round');
            path.setAttribute('stroke-linejoin', 'round');
            this.svg.appendChild(path);
        };
        const offsetForIndex = (idx) => {
            // Alternate offsets to distinguish overlapping paths
            const step = 12; // px, a bit tighter since we anchor to inner edges
            const pattern = [0, -step, step, -2*step, 2*step, -3*step, 3*step];
            return pattern[idx % pattern.length];
        };
        setSvgSize();
        while (this.svg.firstChild) this.svg.removeChild(this.svg.firstChild);
        const wordItems = Array.from(document.querySelectorAll('.word-item'));
        const defItems = Array.from(document.querySelectorAll('.definition-item'));
        const totalW = wordItems.length, totalD = defItems.length;
        let i = 0;
        this.matches.forEach((defVal, wordVal) => {
            const wEl = document.querySelector(`.word-item[data-value="${CSS.escape(wordVal)}"]`);
            const dEl = document.querySelector(`.definition-item[data-value="${CSS.escape(defVal)}"]`);
            if (!wEl || !dEl) return;
            const a = anchorOf(wEl, 'right');
            const b = anchorOf(dEl, 'left');
            const wIndex = wordItems.indexOf(wEl);
            const dIndex = defItems.indexOf(dEl);
            const correct = wEl.classList.contains('correct') && dEl.classList.contains('correct');
            const color = correct ? '#4caf50' : (wEl.classList.contains('incorrect') || dEl.classList.contains('incorrect') ? '#f44336' : '#1CB0F6');
            const offset = offsetForIndex(i++);
            drawSteppedPath(a, b, color, offset);
        });
    }

    autoSubmitIncorrect() {
        // Ensure hidden inputs reflect current matches; unmatched remain empty
        this.matches.forEach((defn, word) => {
            const hiddenInput = document.getElementById(`pair_${word}`);
            if (hiddenInput) hiddenInput.value = defn;
        });
        const form = document.getElementById('quizForm');
        if (form) { form.submit(); }
    }

    resetExercise() {
        this.matches.clear();
        document.querySelectorAll('.match-item').forEach(item => item.classList.remove('matched', 'correct', 'incorrect', 'used'));
        document.querySelectorAll('input[id^="pair_"]').forEach(input => { input.value = ''; });
        const submitButton = document.getElementById('submitButton');
        if (submitButton) { submitButton.disabled = true; submitButton.textContent = 'Check Answers'; submitButton.style.backgroundColor = '#58CC02'; }
    }

    updateSubmitButton() {
        const submitButton = document.getElementById('submitButton');
        const totalWords = document.querySelectorAll('.word-item').length;
        if (!submitButton) return;
        const allMatched = this.matches.size === totalWords;
        const withinMistakeLimit = this.mistakesMade <= this.mistakesAllowed;
        submitButton.disabled = !allMatched || !withinMistakeLimit;
        if (allMatched && !withinMistakeLimit) {
            submitButton.textContent = 'Too Many Mistakes';
            submitButton.style.backgroundColor = '#f44336';
        } else if (allMatched) {
            submitButton.textContent = 'Check Answers';
            submitButton.style.backgroundColor = '#58CC02';
        }
    }
}

function setupFillBlank() {
    const wordBubbles = document.querySelectorAll('.word-bubble');
    const blankSpace = document.getElementById('blankSpace');
    const selectedOptionInput = document.getElementById('selected_option');
    
    wordBubbles.forEach(bubble => {
        bubble.addEventListener('click', function() {
            if (this.style.pointerEvents === 'none') return;
            
            const word = this.getAttribute('data-word');
            selectedOptionInput.value = word;
            
            // Clear blank space
            blankSpace.innerHTML = '';
            
            // Create flying word effect
            const flyingWord = this.cloneNode(true);
            flyingWord.classList.add('flying-word');
            flyingWord.style.position = 'absolute';
            flyingWord.style.left = this.getBoundingClientRect().left + 'px';
            flyingWord.style.top = this.getBoundingClientRect().top + 'px';
            
            document.body.appendChild(flyingWord);
            
            // Animate to blank space
            const blankRect = blankSpace.getBoundingClientRect();
            const finalLeft = blankRect.left + (blankRect.width - flyingWord.offsetWidth) / 2;
            const finalTop = blankRect.top + (blankRect.height - flyingWord.offsetHeight) / 2;
            
            flyingWord.style.transition = 'all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
            flyingWord.style.left = finalLeft + 'px';
            flyingWord.style.top = finalTop + 'px';
            flyingWord.style.transform = 'scale(1.2)';
            
            setTimeout(() => {
                blankSpace.appendChild(this.cloneNode(true));
                document.body.removeChild(flyingWord);
                
                // Enable submit button
                document.getElementById('submitButton').disabled = false;
            }, 500);
        });
    });
}

// Sound effects
function playSound(soundId) {
    const sound = document.getElementById(soundId);
    if (sound) {
        sound.currentTime = 0;
        sound.play().catch(e => console.log('Audio play failed:', e));
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize matching game if pairs-matching
    if (document.querySelector('.pairs-matching-container') && typeof answered !== 'undefined') {
        // question data injected below
        if (!window.answered) {
            window.matchingGame = new MatchingGame();
            // Redraw on resize/scroll
            const redraw = () => window.matchingGame && window.matchingGame.redrawLines();
            window.addEventListener('resize', redraw);
            window.addEventListener('scroll', redraw, true);
        } else {
            // Review mode: draw all submitted pairs; stepped only for opposite-angle (1st<->4th), else straight
            const container = document.querySelector('.pairs-matching-container');
            const svg = container ? container.querySelector('.match-lines-overlay') : null;
            if (container && svg && window.selectedPairs) {
                const setSvgSize = () => {
                    const rect = container.getBoundingClientRect();
                    svg.setAttribute('width', rect.width);
                    svg.setAttribute('height', rect.height);
                    svg.setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
                };
                const centerOf = (el) => {
                    const r = el.getBoundingClientRect();
                    const c = container.getBoundingClientRect();
                    return { x: (r.left - c.left) + r.width / 2, y: (r.top - c.top) + r.height / 2 };
                };
                const drawAll = () => {
                    setSvgSize();
                    while (svg.firstChild) svg.removeChild(svg.firstChild);
                    const wordItems = Array.from(document.querySelectorAll('.word-item'));
                    const defItems = Array.from(document.querySelectorAll('.definition-item'));
                    const totalW = wordItems.length, totalD = defItems.length;
                    Object.keys(window.selectedPairs || {}).forEach(word => {
                        const def = window.selectedPairs[word];
                        const wEl = document.querySelector(`.word-item[data-value="${CSS.escape(word)}"]`);
                        const dEl = document.querySelector(`.definition-item[data-value="${CSS.escape(def)}"]`);
                        if (!wEl || !dEl) return;
                        const a = centerOf(wEl);
                        const b = centerOf(dEl);
                        const wIndex = wordItems.indexOf(wEl);
                        const dIndex = defItems.indexOf(dEl);
                        const correct = wEl.classList.contains('correct') && dEl.classList.contains('correct');
                        const color = correct ? '#4caf50' : '#f44336';
                        if ((totalW >= 4 && totalD >= 4) && ((wIndex === 0 && dIndex === 3) || (wIndex === 3 && dIndex === 0))) {
                            const midX = (a.x + b.x) / 2;
                            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                            const dPath = `M ${a.x} ${a.y} L ${midX} ${a.y} L ${midX} ${b.y} L ${b.x} ${b.y}`;
                            path.setAttribute('d', dPath);
                            path.setAttribute('fill', 'none');
                            path.setAttribute('stroke', color);
                            path.setAttribute('stroke-width', '5');
                            path.setAttribute('stroke-linecap', 'round');
                            path.setAttribute('stroke-linejoin', 'round');
                            svg.appendChild(path);
                        } else {
                            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                            line.setAttribute('x1', a.x);
                            line.setAttribute('y1', a.y);
                            line.setAttribute('x2', b.x);
                            line.setAttribute('y2', b.y);
                            line.setAttribute('stroke', color);
                            line.setAttribute('stroke-width', '4');
                            line.setAttribute('stroke-linecap', 'round');
                            svg.appendChild(line);
                        }
                    });
                };
                drawAll();
                window.addEventListener('resize', drawAll);
                window.addEventListener('scroll', drawAll, true);
            }
        }
    }
    
    // Setup fill in the blanks if present
    if (document.getElementById('blankSpace')) {
        setupFillBlank();
    }
    
    // Add sound effects for feedback
    const feedback = document.getElementById('feedback');
    if (feedback) {
        if (feedback.style.color === 'green') {
            playSound('correctSound');
        } else if (feedback.style.color === 'red') {
            playSound('incorrectSound');
        }
    }
    
    // Play finish sound if quiz is complete
    if (document.querySelector('.results-summary')) {
        playSound('finishSound');
    }
});

// Form submission handling
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton && submitButton.disabled) {
                e.preventDefault();
                return false;
            }
        });
    });
});