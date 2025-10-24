// Theme switching functionality synced with server settings
(function() {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;
  // Initialize toggle from server-rendered class
  themeToggle.checked = document.body.classList.contains('dark-theme');

  // Debounced POST to persist change
  let timer = null;
  function persist(value) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'dark_mode', value })
      }).catch(() => {});
    }, 150);
  }

  themeToggle.addEventListener('change', function() {
    if (this.checked) {
      document.body.classList.add('dark-theme');
      persist(true);
    } else {
      document.body.classList.remove('dark-theme');
      persist(false);
    }
  });
})();