let streak = parseInt(localStorage.getItem("streak")) || 0;
let lastDate = localStorage.getItem("lastDate") || null;
let streakGoal = parseInt(localStorage.getItem("streakGoal")) || 7;

const streakNumber = document.getElementById("streakNumber");
const streakMessage = document.getElementById("streakMessage");
const streakHistory = document.getElementById("streakHistory");
const backButton = document.getElementById("backButton");
const tabs = document.querySelectorAll(".tab");
const tabContents = document.querySelectorAll(".tab-content");

function updateStreak() {
    const today = new Date().toDateString();
    if (lastDate !== today) {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        if (lastDate === yesterday.toDateString()) {
            streak++;
        } else {
            streak = 1;
        }
        lastDate = today;
        localStorage.setItem("streak", streak);
        localStorage.setItem("lastDate", lastDate);
    }
}

function renderStreak() {
    streakNumber.textContent = streak;
    streakMessage.textContent =
        streak < streakGoal ? "Keep it up!" :
        streak === streakGoal ? "You reached your goal!" : "New record!";

    streakHistory.innerHTML = "";
    for (let i = 1; i <= streakGoal; i++) {
        const dayDiv = document.createElement("div");
        dayDiv.className = "streak-day";
        dayDiv.textContent = i;
        dayDiv.style.width = "40px";
        dayDiv.style.height = "40px";
        dayDiv.style.display = "flex";
        dayDiv.style.alignItems = "center";
        dayDiv.style.justifyContent = "center";
        dayDiv.style.borderRadius = "50%";
        dayDiv.style.backgroundColor = i <= streak ? "#58CC02" : "#ccc";
        dayDiv.style.color = "#fff";
        streakHistory.appendChild(dayDiv);
    }

    highlightGoal();
}

function setGoal(goal) {
    streakGoal = goal;
    localStorage.setItem("streakGoal", streakGoal);
    renderStreak();
}

function highlightGoal() {
    [7, 14, 28].forEach(g => {
        const btn = document.getElementById(`goal${g}`);
        if (g === streakGoal) {
            btn.style.backgroundColor = "#58CC02";
            btn.style.color = "#fff";
        } else {
            btn.style.backgroundColor = "#ddd";
            btn.style.color = "#333";
        }
    });
}

backButton.onclick = function () {
    window.location.href = "/lessons";
};

tabs.forEach(tab => {
    tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        tabContents.forEach(c => c.style.display = "none");
        document.getElementById(tab.dataset.tab).style.display = "flex";
    });
});

updateStreak();
renderStreak();
