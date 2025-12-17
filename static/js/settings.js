// static/settings.js
document.addEventListener("DOMContentLoaded", function () {
  // Background music control (productivity mode)
  const musicToggle = document.getElementById("productivity-toggle");
  const music = document.getElementById("background-music");
  if (localStorage.getItem("musicEnabled") === "true") {
    if (musicToggle) musicToggle.checked = true;
    if (music) {
      music.currentTime = 0;
      music.play().catch(err => console.log("Autoplay blocked:", err));
    }
  }
  if (musicToggle && music) {
    musicToggle.addEventListener("change", function () {
      if (musicToggle.checked) {
        music.currentTime = 0;
        music.play().catch(err => console.log("Play blocked:", err));
        localStorage.setItem("musicEnabled", "true");
      } else {
        music.pause();
        music.currentTime = 0;
        localStorage.setItem("musicEnabled", "false");
      }
    });
  }

  // Change tracking and Save button enablement
  const form = document.getElementById('settings-form');
  const saveBtn = document.getElementById('saveSettingsBtn');
  let isDirty = false;

  function serializeForm(f) {
    const data = {};
    if (!f) return data;
    Array.from(f.elements).forEach(el => {
      if (!el.name && !el.id) return;
      const key = el.name || el.id;
      if (el.type === 'checkbox') data[key] = el.checked;
      else if (el.type === 'radio') { if (el.checked) data[key] = el.value; }
      else data[key] = el.value;
    });
    return data;
  }

  const initialState = serializeForm(form);

  function setDirty(flag) {
    isDirty = !!flag;
    if (saveBtn) {
      saveBtn.disabled = !isDirty;
      saveBtn.classList.toggle('enabled', isDirty);
    }
  }

  function onChanged() { 
    setDirty(true);
    // Auto-save after 2 seconds of inactivity
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(autoSave, 2000);
  }

  let autoSaveTimer;
  function autoSave() {
    if (!isDirty || !form) return;
    
    // Show saving indicator
    if (saveBtn) {
      const originalText = saveBtn.textContent;
      saveBtn.textContent = 'Saving...';
      saveBtn.disabled = true;
    }
    
    // Submit form via fetch
    const formData = new FormData(form);
    fetch(form.action || window.location.href, {
      method: 'POST',
      body: formData
    })
    .then(response => response.text())
    .then(() => {
      setDirty(false);
      // Show saved indicator briefly
      if (saveBtn) {
        saveBtn.textContent = 'Saved!';
        saveBtn.classList.add('saved');
        setTimeout(() => {
          saveBtn.textContent = originalText;
          saveBtn.classList.remove('saved');
          saveBtn.disabled = true;
        }, 1500);
      }
    })
    .catch(error => {
      console.error('Auto-save failed:', error);
      // Restore button state on error
      if (saveBtn) {
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
      }
    });
  }

  if (form) {
    Array.from(form.elements).forEach(el => {
      el.addEventListener('change', onChanged);
      if (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'email' || el.type === 'range')) {
        el.addEventListener('input', onChanged);
      }
    });
  }

  // Prevent navigation if unsaved changes (but allow auto-save to complete)
  window.addEventListener('beforeunload', function (e) {
    if (!isDirty) return;
    // Clear auto-save timer and try to save immediately
    clearTimeout(autoSaveTimer);
    autoSave();
    // Still show warning as fallback
    e.preventDefault();
    e.returnValue = '';
  });

  // Intercept in-page navigation (header/footer links) - try auto-save first
  document.querySelectorAll('a[href]').forEach(a => {
    a.addEventListener('click', function (e) {
      const isSaveButton = (e.target && e.target.closest && e.target.closest('#saveSettingsBtn'));
      if (isDirty && !isSaveButton) {
        e.preventDefault();
        // Try auto-save immediately, then navigate
        clearTimeout(autoSaveTimer);
        autoSave();
        setTimeout(() => {
          window.location.href = a.href;
        }, 500);
      }
    });
  });

  // On form submit, clear dirty and allow navigation
  if (form) {
    form.addEventListener('submit', function () { setDirty(false); });
  }

  // Font scale is rendered from server settings and controlled by settings page slider.
});