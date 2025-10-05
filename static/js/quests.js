document.addEventListener("DOMContentLoaded", () => {
    const fills = document.querySelectorAll(".quest-progress-fill");

    fills.forEach((fill, index) => {
        const target = parseInt(fill.getAttribute("data-target"));

        setTimeout(() => {
            fill.style.width = target + "%";

            if (target >= 100) {
                fill.classList.add("completed");
            }
        }, index * 300);
    });
});
