let streak = parseInt(localStorage.getItem("streak")) || 0;
let lastDate = localStorage.getItem("lastDate") || null;
let streakGoal = parseInt(localStorage.getItem("streakGoal")) || 7;
let __SERVER_DATA_JSON = null;
try {
  const el = document.getElementById('streakData');
  if (el && el.textContent) __SERVER_DATA_JSON = JSON.parse(el.textContent);
} catch (_) {}
const SERVER_DATA = (typeof window !== 'undefined' && window.STREAK_DATA) ? window.STREAK_DATA : __SERVER_DATA_JSON;
const serverMode = !!SERVER_DATA;

// Calendar state
const today = new Date();
let calYear = today.getFullYear();
let calMonth = today.getMonth(); // 0..11
if (serverMode) {
  if (SERVER_DATA.year && SERVER_DATA.month) {
    calYear = SERVER_DATA.year;
    calMonth = (SERVER_DATA.month - 1);
  }
}

// Completed days (ISO yyyy-mm-dd strings)
const completedDays = new Set(
  serverMode ? (SERVER_DATA.completed_days || []) : JSON.parse(localStorage.getItem("completedDays") || "[]")
);

// Elements
const streakNumber = document.getElementById("streakNumber");
const streakMessage = document.getElementById("streakMessage");
const backButton = document.getElementById("backButton");
const tabs = document.querySelectorAll(".tab");
const tabContents = document.querySelectorAll(".tab-content");
const calPrev = document.getElementById("calPrev");
const calNext = document.getElementById("calNext");
const calMonthLabel = document.getElementById("calMonthLabel");
const calGrid = document.getElementById("calGrid");
const saveGoalBtn = document.getElementById("saveGoalBtn");
const goalInfo = document.getElementById("goalInfo");
const calTooltip = document.getElementById("calTooltip");

// Persisted saved goal preset (effective date is tomorrow)
let savedStreakGoal = serverMode ? (SERVER_DATA.goal?.goal_days || streakGoal) : (parseInt(localStorage.getItem("savedStreakGoal")) || streakGoal);
let savedGoalEffectiveDate = serverMode ? (SERVER_DATA.goal?.effective_from || null) : (localStorage.getItem("savedGoalEffectiveDate") || null); // ISO

if (serverMode) {
  // Override streak and goal from server state
  if (SERVER_DATA.state) {
    streak = SERVER_DATA.state.current_streak || 0;
  }
  if (SERVER_DATA.goal && SERVER_DATA.goal.goal_days) {
    streakGoal = SERVER_DATA.goal.goal_days;
  }
}
let goalDirty = false;

function updateSaveState() {
  if (!saveGoalBtn) return;
  // Dirty if current selection differs from saved value
  goalDirty = (streakGoal !== savedStreakGoal);
  saveGoalBtn.disabled = !goalDirty;
  saveGoalBtn.classList.toggle('enabled', goalDirty);
}

function toISO(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getWeekStartDay() {
  const v = (localStorage.getItem('weekStartDay') || 'monday').toLowerCase();
  return v; // 'monday'..'sunday'
}

function getWeekStartIndexJS() {
  // Map week start to JS getDay base (0=Sun..6=Sat)
  const map = {
    'sunday': 0,
    'monday': 1,
    'tuesday': 2,
    'wednesday': 3,
    'thursday': 4,
    'friday': 5,
    'saturday': 6,
  };
  const w = getWeekStartDay();
  return map[w] ?? 1; // default Monday
}

function updateStreak() {
  if (serverMode) return; // server is source of truth
  const todayStr = new Date().toDateString();
  if (lastDate !== todayStr) {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    if (lastDate === yesterday.toDateString()) {
      streak++;
    } else {
      streak = 1;
    }
    lastDate = todayStr;
    localStorage.setItem("streak", String(streak));
    localStorage.setItem("lastDate", lastDate);
    // Also mark today as completed (front-end only for now)
    const iso = toISO(new Date());
    if (!completedDays.has(iso)) {
      completedDays.add(iso);
      localStorage.setItem("completedDays", JSON.stringify(Array.from(completedDays)));
    }
  }
}

function renderHeader() {
  const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  calMonthLabel.textContent = `${monthNames[calMonth]} ${calYear}`;
}

function getIndexFromWeekStart(jsDay) {
  // JS: 0=Sun..6=Sat; compute index relative to chosen week start
  const start = getWeekStartIndexJS();
  return (jsDay - start + 7) % 7;
}

function renderCalendar() {
  renderHeader();
  // Update weekday headers to match chosen week start
  const weekdayNames = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const start = getWeekStartIndexJS();
  for (let i = 0; i < 7; i++) {
    const child = calGrid.children[i];
    if (child && child.classList.contains('cal-weekday')) {
      const label = weekdayNames[(start + i) % 7];
      child.textContent = label;
    }
  }
  // Clear old days (keep weekday headers: first 7 children)
  while (calGrid.children.length > 7) calGrid.removeChild(calGrid.lastChild);

  const firstOfMonth = new Date(calYear, calMonth, 1);
  const firstWeekdayIndex = getIndexFromWeekStart(firstOfMonth.getDay());
  const daysInThisMonth = new Date(calYear, calMonth + 1, 0).getDate();

  // Previous month trailing days to fill Monday-first grid
  const prevMonthLastDate = new Date(calYear, calMonth, 0).getDate();
  for (let i = 0; i < firstWeekdayIndex; i++) {
    const dayNum = prevMonthLastDate - firstWeekdayIndex + 1 + i;
    const cell = document.createElement('div');
    cell.className = 'cal-day other-month';
    const span = document.createElement('span');
    span.className = 'date-num';
    span.textContent = String(dayNum);
    cell.appendChild(span);
    calGrid.appendChild(cell);
  }

  // Compute streak start day based on consecutive completedDays back from today
  const startISO = computeStreakStartISO();
  // Compute goal target date (Nth day from today) and mark it with a goal outline
  const goalTarget = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  goalTarget.setDate(goalTarget.getDate() + Math.max(0, (streakGoal - 1)));
  const goalISO = toISO(goalTarget);

  // Current month days
  for (let d = 1; d <= daysInThisMonth; d++) {
    const cell = document.createElement('div');
    cell.className = 'cal-day';
    const span = document.createElement('span');
    span.className = 'date-num';
    span.textContent = String(d);
    cell.appendChild(span);

    const dateObj = new Date(calYear, calMonth, d);
    const iso = toISO(dateObj);
    const isToday = toISO(today) === iso;
    if (isToday) {
      cell.classList.add('today');
      // tooltip for today
      cell.addEventListener('mouseenter', () => {
        if (!calTooltip) return;
        calTooltip.textContent = `Today`;
        const x = cell.offsetLeft + (cell.offsetWidth / 2);
        const y = cell.offsetTop - 8;
        calTooltip.style.left = `${x}px`;
        calTooltip.style.top = `${y}px`;
        calTooltip.hidden = false;
      });
      cell.addEventListener('mouseleave', () => { if (calTooltip) calTooltip.hidden = true; });
    }
    if (completedDays.has(iso)) cell.classList.add('completed');
    if (startISO && iso === startISO) cell.classList.add('start');
    if (iso === goalISO) {
      cell.classList.add('goal');
      // custom tooltip
      cell.addEventListener('mouseenter', () => {
        if (!calTooltip) return;
        calTooltip.textContent = `Your goal (${streakGoal} days)`;
        const x = cell.offsetLeft + (cell.offsetWidth / 2);
        const y = cell.offsetTop - 8; // small gap above the cell
        calTooltip.style.left = `${x}px`;
        calTooltip.style.top = `${y}px`;
        calTooltip.hidden = false;
      });
      cell.addEventListener('mouseleave', () => { if (calTooltip) calTooltip.hidden = true; });
    }
    calGrid.appendChild(cell);
  }

  // Next month leading days to complete the last row (optional)
  const totalCells = calGrid.children.length;
  const remainder = totalCells % 7;
  if (remainder !== 0) {
    const fill = 7 - remainder;
    for (let i = 1; i <= fill; i++) {
      const cell = document.createElement('div');
      cell.className = 'cal-day other-month';
      const span = document.createElement('span');
      span.className = 'date-num';
      span.textContent = String(i);
      cell.appendChild(span);
      calGrid.appendChild(cell);
    }
  }
}

function updateGoalLabel(val) {
  if (streakMessage) streakMessage.textContent = `Goal: ${val} days`;
}

function renderStreakSummary() {
  streakNumber.textContent = String(streak);
  // Keep message as goal label for clarity
  updateGoalLabel(streakGoal);
}

function setGoal(goal) {
  streakGoal = goal;
  localStorage.setItem("streakGoal", String(streakGoal));
  highlightGoal();
  renderGoalInfo();
  updateSaveState();
  renderCalendar();
  updateGoalLabel(streakGoal);
}

function highlightGoal() {
  [7, 14, 28].forEach(g => {
    const btn = document.getElementById(`goal${g}`);
    if (!btn) return;
    if (g === streakGoal) {
      btn.style.backgroundColor = "#58CC02";
      btn.style.color = "#fff";
    } else {
      btn.style.backgroundColor = "#ddd";
      btn.style.color = "#333";
    }
  });
}

// Expose setGoal for inline onclick
window.setGoal = setGoal;

async function loadMonth(y, m) {
  // Update local state and fetch completed days from server
  calYear = y; calMonth = m - 1; // internal 0..11
  if (!serverMode) { renderCalendar(); return; }
  try {
    const res = await fetch(`/streak/month?year=${y}&month=${m}`, { headers: { 'Accept': 'application/json' } });
    const json = await res.json();
    if (json && json.ok) {
      // Replace completedDays with server data
      completedDays.clear();
      (json.completed_days || []).forEach(d => completedDays.add(d));
      renderCalendar();
    }
  } catch (e) { console.error('Failed to load month', e); }
}

// Month navigation
if (calPrev) calPrev.addEventListener('click', () => {
  let y = calYear, m = calMonth + 1; // 1..12
  m -= 1; if (m < 1) { m = 12; y -= 1; }
  loadMonth(y, m);
});
if (calNext) calNext.addEventListener('click', () => {
  let y = calYear, m = calMonth + 1; // 1..12
  m += 1; if (m > 12) { m = 1; y += 1; }
  loadMonth(y, m);
});

// Save goal behavior: can only take effect from tomorrow or later
function renderGoalInfo() {
  if (!goalInfo) return;
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const isoTomorrow = toISO(tomorrow);
  if (savedGoalEffectiveDate) {
    goalInfo.textContent = `Saved goal: ${savedStreakGoal} days (effective from ${savedGoalEffectiveDate}).`;
  } else {
    goalInfo.textContent = `Select a goal and press Save. It will take effect starting ${isoTomorrow}.`;
  }
}

if (saveGoalBtn) saveGoalBtn.addEventListener('click', async () => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const isoTomorrow = toISO(tomorrow);
  // Enforce: cannot set effective date today or earlier
  if (serverMode) {
    try {
      saveGoalBtn.disabled = true;
      const res = await fetch('/streak/goal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal_days: streakGoal })
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const json = await res.json();
      if (json && json.ok) {
        savedStreakGoal = streakGoal;
        savedGoalEffectiveDate = json.effective_from || isoTomorrow;
        updateGoalLabel(savedStreakGoal);
        // Persist locally to avoid flashing back to 7 in any fallback path
        localStorage.setItem('streakGoal', String(savedStreakGoal));
      } else {
        throw new Error('Save failed');
      }
    } catch (e) {
      console.error('Failed to save goal', e);
      if (goalInfo) goalInfo.textContent = 'Failed to save goal. Please try again.';
    } finally {
      // Reset dirty state only if saved
      updateSaveState();
      saveGoalBtn.disabled = (streakGoal === savedStreakGoal);
    }
  } else {
    savedStreakGoal = streakGoal;
    savedGoalEffectiveDate = isoTomorrow;
    localStorage.setItem('savedStreakGoal', String(savedStreakGoal));
    localStorage.setItem('savedGoalEffectiveDate', savedGoalEffectiveDate);
    updateGoalLabel(savedStreakGoal);
  }
  renderGoalInfo();
  updateSaveState();
  renderCalendar();
});

// Helper: compute streak start date ISO by walking back from today
function computeStreakStartISO() {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const todayISO = toISO(t);
  if (!completedDays.has(todayISO)) return null;
  let cursor = new Date(t);
  while (true) {
    const prev = new Date(cursor);
    prev.setDate(prev.getDate() - 1);
    const prevISO = toISO(prev);
    if (completedDays.has(prevISO)) {
      cursor = prev;
      continue;
    }
    break;
  }
  return toISO(cursor);
}

// Tabs and back
if (backButton) backButton.onclick = () => { window.location.href = "/lessons"; };
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    tabContents.forEach(c => c.style.display = "none");
    document.getElementById(tab.dataset.tab).style.display = "flex";
  });
});

// Block navigation away if goal changes are not saved (real page exits only)
window.addEventListener('beforeunload', function (e) {
  if (!goalDirty) return;
  e.preventDefault();
  e.returnValue = '';
});

// Initial render
updateStreak();
renderStreakSummary();
highlightGoal();
renderGoalInfo();
updateSaveState();
renderCalendar();
