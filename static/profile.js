const nicknameInput = document.getElementById("nickname");
const birthDateInput = document.getElementById("birthDate");
const privateBtn = document.getElementById("privateBtn");
const publicBtn = document.getElementById("publicBtn");
const accountInfo = document.getElementById("accountInfo");

nicknameInput.addEventListener("focus", () => {
    if(nicknameInput.value === "") nicknameInput.value = "@";
});

nicknameInput.addEventListener("blur", () => {
    if(nicknameInput.value === "@") nicknameInput.value = "";
});

birthDateInput.max = new Date().toISOString().split("T")[0];

privateBtn.addEventListener("click", () => {
    privateBtn.classList.add("active");
    publicBtn.classList.remove("active");
    accountInfo.textContent = "Others cannot search you by nickname. Your nickname remains unique.";
});

publicBtn.addEventListener("click", () => {
    publicBtn.classList.add("active");
    privateBtn.classList.remove("active");
    accountInfo.textContent = "Others can search and connect with you freely.";
});

function avatarClick() {
    alert("Avatar uploading coming soon");
}
