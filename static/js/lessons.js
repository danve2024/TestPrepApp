// Tab switching logic
document.querySelectorAll(".lessons-tab").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".lessons-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");

        document.querySelector("#english").style.display = "none";
        document.querySelector("#math").style.display = "none";

        const target = tab.dataset.tab;
        document.querySelector("#" + target).style.display = "block";
    });
});

// Scrollable map logic
document.querySelectorAll(".lessons-map").forEach(map => {
    let isDown = false, startX, startY, scrollLeft, scrollTop;

    map.addEventListener("mousedown", (e) => {
        isDown = true;
        map.style.cursor = "grabbing";
        startX = e.pageX - map.offsetLeft;
        startY = e.pageY - map.offsetTop;
        scrollLeft = map.parentElement.scrollLeft;
        scrollTop = map.parentElement.scrollTop;
    });

    map.addEventListener("mouseleave", () => { isDown = false; map.style.cursor = "grab"; });
    map.addEventListener("mouseup", () => { isDown = false; map.style.cursor = "grab"; });
    map.addEventListener("mousemove", (e) => {
        if(!isDown) return;
        e.preventDefault();
        const x = e.pageX - map.offsetLeft;
        const y = e.pageY - map.offsetTop;
        const walkX = (x - startX);
        const walkY = (y - startY);
        map.parentElement.scrollLeft = scrollLeft - walkX;
        map.parentElement.scrollTop = scrollTop - walkY;
    });
});