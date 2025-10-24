document.addEventListener("DOMContentLoaded", function () {
  const music = document.getElementById("background-music");
  if (!music) return;

  // Restore last playback position across pages (session-scoped)
  const restorePosition = () => {
    const t = parseFloat(sessionStorage.getItem("musicCurrentTime") || "0");
    if (!isNaN(t) && isFinite(t) && t > 0) {
      // Small rewind to avoid jarring
      music.currentTime = Math.max(0, t - 0.25);
    }
  };

  const savePosition = () => {
    try { sessionStorage.setItem("musicCurrentTime", String(music.currentTime || 0)); } catch (e) {}
  };

  // Persist on progress and lifecycle events
  music.addEventListener("timeupdate", savePosition);
  window.addEventListener("beforeunload", savePosition);
  document.addEventListener("visibilitychange", () => { if (document.hidden) savePosition(); });

  // Auto-restore and play if enabled
  if (localStorage.getItem("musicEnabled") === "true") {
    restorePosition();
    music.play().catch(() => {});
  }

  // Listen to changes in settings toggle (if present)
  const observer = new MutationObserver(() => {
    const musicToggle = document.getElementById("sound-toggle");
    if (musicToggle && !musicToggle.__boundMusic) {
      musicToggle.__boundMusic = true;
      musicToggle.addEventListener("change", function () {
        if (musicToggle.checked) {
          localStorage.setItem("musicEnabled", "true");
          restorePosition();
          music.play().catch(() => {});
        } else {
          localStorage.setItem("musicEnabled", "false");
          savePosition();
          music.pause();
        }
      });
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
});