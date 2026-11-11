// kittyson screen: show /api/widget as-is, tick "time" every second, poll every minute.
// Text colors come from /cat/today.json, where the server has measured today's photo.

const POLL_MS = 60_000;
const API = "/api/widget";
const MIN_FONT_PX = 6;
const STUB_CH = 6;      // a wrapped value never leaves a last row shorter than this many characters

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
    return `<div class="line"><span class="k">${escapeHtml(JSON.stringify(k))}</span>: <span class="s"${id}>${value}</span>${comma}</div>`;
  });
  $json.innerHTML = `<div class="brace">{</div>${lines.join("")}<div class="brace">}</div>`;
  fit();
}

// True when some wrapped line ends in a stub like `v1",`. A smaller font suits it better.
function hasStub(px) {
  for (const line of $json.querySelectorAll(".line")) {
    const range = document.createRange();
    range.selectNodeContents(line);
    const rects = [...range.getClientRects()].filter((r) => r.width > 0);
    if (!rects.length) continue;
    const top = Math.min(...rects.map((r) => r.top));
    const bottom = Math.max(...rects.map((r) => r.bottom));
    if (bottom - top < px * 1.6) continue; // a single row
    const last = rects.filter((r) => r.bottom > bottom - px / 2);
    const width = Math.max(...last.map((r) => r.right)) - Math.min(...last.map((r) => r.left));
    if (width < STUB_CH * px * 0.6) return true;
  }
  return false;
}

// The JSON fills the card: the biggest font at which every line, wrapped to the card's
// width (style.css indents the wrapped rows), still fits its height.
function fit() {
  const fits = (px) => {
    $json.style.fontSize = `${px}px`;
    return $json.scrollHeight <= $json.clientHeight && $json.scrollWidth <= $json.clientWidth;
  };
  let lo = MIN_FONT_PX;
  let hi = $json.clientWidth / 4;
  while (hi - lo > 0.25) {
    const mid = (lo + hi) / 2;
    if (fits(mid)) lo = mid; else hi = mid;
  }
  // lo is the biggest size that fits. Step down from it until no line ends in a stub.
  let px = lo;
  while (px > MIN_FONT_PX && (!fits(px) || hasStub(px))) px -= 0.5;
  fits(px);
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
document.fonts.ready.then(fit);
