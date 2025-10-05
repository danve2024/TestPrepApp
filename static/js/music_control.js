document.addEventListener("DOMContentLoaded", function () {
        const music = document.getElementById("background-music");

        // Auto-restore state from localStorage
        if (localStorage.getItem("musicEnabled") === "true") {
            music.currentTime = 0;
            music.play();
        }

        // Listen to changes in settings toggle (if present)
        const observer = new MutationObserver(() => {
            const musicToggle = document.getElementById("sound-toggle");
            if (musicToggle) {
                musicToggle.addEventListener("change", function () {
                    if (musicToggle.checked) {
                        music.currentTime = 0;
                        music.play();
                        localStorage.setItem("musicEnabled", "true");
                    } else {
                        music.pause();
                        music.currentTime = 0;
                        localStorage.setItem("musicEnabled", "false");
                    }
                });
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    });