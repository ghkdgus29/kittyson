// kittyson screen: show /api/widget as-is, tick "time" every second, poll every minute.
// Text colors come from /cat/today.json, where the server has measured today's photo.

const POLL_MS = 60_000;
const API = "/api/widget";
const MIN_FIT = 0.6;    // a long line shrinks to fit, but never below this share of the base size

const $json = document.getElementById("json");
const $bg = document.getElementById("bg");

let data = null;        // last payload from the server
let offsetMs = 0;       // server wall clock (read as if it were UTC) - device clock
let shownDate = null;   // YYYY-MM-DD of the background currently shown
let themedDate = null;  // YYYY-MM-DD the current text colors were measured for

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// The server sends its local date and time without an offset. Reading them as UTC gives a
// clock that can be advanced and printed back with toISOString(), whatever zone the device is in.
function serverNow() { return Date.now() + offsetMs; }

function wallClock() {
  const iso = new Date(serverNow()).toISOString();
  return { date: iso.slice(0, 10), time: iso.slice(11, 19) };
}

function render(obj) {
  const keys = Object.keys(obj);
  const lines = keys.map((k, i) => {
    const comma = i < keys.length - 1 ? "," : "";
    const id = k === "time" || k === "date" ? ` id="${k}"` : ""; // the two values tick() rewrites
    const value = escapeHtml(JSON.stringify(obj[k]));
    return `<div class="line">  <span class="fit"><span class="k">${escapeHtml(JSON.stringify(k))}</span>: <span class="s"${id}>${value}</span>${comma}</span></div>`;
  });
  $json.innerHTML = `<div class="line">{</div>${lines.join("")}<div class="line">}</div>`;
  fit();
}

// One line per key: a line wider than the card gets a smaller font instead of wrapping.
// The indent keeps its size so the keys stay in one column.
function fit() {
  const room = $json.clientWidth;
  for (const span of $json.querySelectorAll(".fit")) {
    span.style.fontSize = "";
    const indent = span.offsetLeft;
    const width = span.getBoundingClientRect().width;
    if (indent + width > room) span.style.fontSize = `${Math.max(MIN_FIT, (room - indent) / width) * 100}%`;
  }
}

function tick() {
  const now = wallClock();
  for (const key of ["time", "date"]) {
    const el = document.getElementById(key);
    if (el) el.textContent = JSON.stringify(now[key]);
  }
}

function scheduleTick() {
  // Fire just after each second boundary so the display never lags a full second.
  const wait = 1000 - (serverNow() % 1000) + 5;
  setTimeout(() => { tick(); scheduleTick(); }, wait);
}

function showBackground(dateStr) {
  if (dateStr === shownDate) return;
  const img = new Image();
  img.onload = () => {
    $bg.src = img.src;
    $bg.classList.add("ready");
    shownDate = dateStr;
  };
  img.src = `/cat/today.jpg?d=${encodeURIComponent(dateStr)}`;
}

function rgbTriplet(hex) {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(" ");
}

function applyTheme(theme) {
  const root = document.documentElement.style;
  for (const name of ["punct", "key", "str"]) root.setProperty(`--${name}`, theme[name]);
  root.setProperty("--halo", rgbTriplet(theme.halo));
  root.setProperty("--halo-a", String(theme.halo_alpha));
}

async function showTheme(dateStr) {
  if (dateStr === themedDate) return;
  try {
    const res = await fetch(`/cat/today.json?d=${encodeURIComponent(dateStr)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    applyTheme((await res.json()).theme);
    themedDate = dateStr;
  } catch (err) {
    console.warn("kittyson theme failed:", err); // default colors stay, next poll retries
  }
}

async function poll() {
  try {
    const res = await fetch(API, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const fresh = await res.json();
    const serverMs = Date.parse(`${fresh.date}T${fresh.time}Z`);
    if (!Number.isNaN(serverMs)) offsetMs = serverMs - Date.now();
    data = fresh;
    render(data);
    tick();
    showBackground(fresh.date);
    showTheme(fresh.date);
  } catch (err) {
    // Keep the clock running on whatever we had.
    console.warn("kittyson poll failed:", err);
    if (data) tick();
  }
}

poll();
scheduleTick();
setInterval(poll, POLL_MS);
document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
window.addEventListener("resize", fit);
