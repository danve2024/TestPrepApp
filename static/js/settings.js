// static/settings.js
document.addEventListener("DOMContentLoaded", function () {
    const musicToggle = document.getElementById("productivity-toggle");
    const music = document.getElementById("background-music");

    if (localStorage.getItem("musicEnabled") === "true") {
        if (musicToggle) musicToggle.checked = true;
        music.currentTime = 0;
        music.play().catch(err => console.log("Autoplay blocked:", err));
    }

    if (musicToggle) {
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
});