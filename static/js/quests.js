function animateQuestBars() {
  const fills = document.querySelectorAll('.quest-progress-fill');
  fills.forEach((fill, index) => {
    const target = parseInt(fill.getAttribute('data-target')) || 0;
    fill.style.width = '0%';
    setTimeout(() => {
      fill.style.width = target + '%';
      if (target >= 100) {
        fill.classList.add('completed');
      }
    }, index * 300);
  });
}

document.addEventListener('DOMContentLoaded', animateQuestBars);
window.addEventListener('content:loaded', animateQuestBars);
