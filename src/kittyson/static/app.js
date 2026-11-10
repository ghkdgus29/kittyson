// kittyson screen: show /api/widget as-is, tick "now" every second, poll every minute.

const POLL_MS = 60_000;
const API = "/api/widget";

const $json = document.getElementById("json");
const $bg = document.getElementById("bg");

let data = null;        // last payload from the server
let offsetMs = 0;       // server clock - device clock
let utcOffsetMin = 9 * 60; // from the "+09:00" suffix of "now"
let shownDate = null;   // YYYY-MM-DD of the background currently shown

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// Parse "+09:00" / "-05:30" / "Z" into minutes.
function parseUtcOffset(iso) {
  const m = iso.match(/([+-])(\d{2}):(\d{2})$/);
  if (!m) return 0;
  const sign = m[1] === "-" ? -1 : 1;
  return sign * (Number(m[2]) * 60 + Number(m[3]));
}

function pad(n) { return String(n).padStart(2, "0"); }

// Format a UTC epoch ms as ISO 8601 with the server's fixed offset.
function isoAt(epochMs, offMin) {
  const d = new Date(epochMs + offMin * 60_000);
  const sign = offMin < 0 ? "-" : "+";
  const abs = Math.abs(offMin);
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}` +
    `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}

function serverNow() { return Date.now() + offsetMs; }

function render(obj) {
  const keys = Object.keys(obj);
  const lines = keys.map((k, i) => {
    const comma = i < keys.length - 1 ? "," : "";
    const cls = k === "now" ? "s now" : "s";
    const id = k === "now" ? ' id="now"' : "";
    const value = escapeHtml(JSON.stringify(obj[k]));
    return `  <span class="k">${escapeHtml(JSON.stringify(k))}</span>: <span class="${cls}"${id}>${value}</span>${comma}`;
  });
  $json.innerHTML = `{\n${lines.join("\n")}\n}`;
}

function tick() {
  const $now = document.getElementById("now");
  if (!$now) return;
  $now.textContent = JSON.stringify(isoAt(serverNow(), utcOffsetMin));
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

async function poll() {
  try {
    const res = await fetch(API, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const fresh = await res.json();
    const serverMs = Date.parse(fresh.now);
    if (!Number.isNaN(serverMs)) {
      offsetMs = serverMs - Date.now();
      utcOffsetMin = parseUtcOffset(fresh.now);
    }
    data = fresh;
    render(data);
    tick();
    showBackground(fresh.now.slice(0, 10));
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
