// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: orange; icon-glyph: cat;

// kittyson widget for Scriptable (https://scriptable.app)
//
// Shows /api/widget from the kittyson server as raw JSON over today's cat.
// - "time" ticks every second: iOS draws a timer counting up from midnight, which reads
//   as the current time.
// - The JSON fills the widget: one font size for every line, as big as fits, with long
//   values wrapped onto the next row.
// - Text colors come from /cat/today.json. The server measures today's photo and picks
//   light or dark letters, accent colors and a halo that stay readable over it.
//
// Server address, first match wins:
//   1. the widget's Parameter (long-press widget > Edit Widget)
//   2. SERVER in kittyson-loader.js, when this file is run through the loader
//   3. DEFAULT_SERVER below

const DEFAULT_SERVER = "http://192.168.0.10:8787";
const LOADER_SERVER = typeof KITTYSON_SERVER === "string" ? KITTYSON_SERVER : "";

// 0 = cat untouched. Raise toward 0.4 to darken the whole photo behind the text.
const SHADE = 0;

// Colors used until the server's theme for today's photo is known.
const DEFAULT_THEME = {
  punct: "#ffffff",
  key: "#9cdcfe",
  str: "#ffd9a8",
  halo: "#000000",
  halo_alpha: 0.9,
};

// Space between the widget's edge and the JSON, per widget size.
const PAD = { large: 12, medium: 10, small: 10 };

const MIN_FONT = 8;
const MAX_FONT = 40;
const CHAR_W = 0.62;   // monospaced advance, in units of font size (slightly generous)
const TEXT_H = 1.2;    // height of a row of text, in units of font size
const GAP = 0.12;      // least space between rows, in units of font size
const MAX_GAP = 0.6;   // most space between rows; beyond it the JSON is centered instead
const INDENT = 2;      // indent of a key, in characters
const HANG = 4;        // indent of the rows a long value wraps onto
const WIDOW = 6;       // a wrapped value never leaves fewer characters than this on its last row
const CLOCK_UNITS = 10.5; // "14:01:53" with its quotes, and the slack of the timer's box
const TIMEOUT_S = 8;

const SERVER = String(args.widgetParameter || LOADER_SERVER || DEFAULT_SERVER).trim().replace(/\/+$/, "");
const fm = FileManager.local();
const CACHE_DIR = fm.joinPath(fm.cacheDirectory(), "kittyson");
if (!fm.fileExists(CACHE_DIR)) fm.createDirectory(CACHE_DIR, true);

// ---------- data ----------

// The JSON as the server sends it now. A payload from before "now" was split into
// "time" and "date" (an old cache, or an old server) is converted, keeping the key order.
function normalize(data) {
  if (!data || typeof data !== "object") return null;
  if (typeof data.time === "string" && typeof data.date === "string") return data;
  if (typeof data.now !== "string") return null;
  const out = {};
  for (const key of Object.keys(data)) {
    if (key === "now") {
      out.time = data.now.slice(11, 19);
      out.date = data.now.slice(0, 10);
    } else {
      out[key] = data[key];
    }
  }
  return out;
}

function deviceOffset() { return -new Date().getTimezoneOffset(); }

// The server sends its wall clock without a UTC offset. Comparing it with the device
// clock right after the request gives the offset, rounded to a quarter of an hour.
function inferOffset(payload) {
  const serverMs = Date.parse(`${payload.date}T${payload.time}Z`);
  const off = Math.round((serverMs - Date.now()) / 900000) * 15;
  return Number.isFinite(off) && Math.abs(off) <= 14 * 60 ? off : deviceOffset();
}

// -> { payload, offMin } or null
async function loadData() {
  const cachePath = fm.joinPath(CACHE_DIR, "widget.json");
  try {
    const req = new Request(`${SERVER}/api/widget`);
    req.timeoutInterval = TIMEOUT_S;
    const payload = normalize(await req.loadJSON());
    if (!payload) throw new Error("unexpected payload");
    const loaded = { payload, offMin: inferOffset(payload) };
    fm.writeString(cachePath, JSON.stringify(loaded));
    return loaded;
  } catch (err) {
    console.warn(`kittyson: server unreachable (${err}), using cache`);
    if (!fm.fileExists(cachePath)) return null;
    try {
      const saved = JSON.parse(fm.readString(cachePath));
      if (saved && saved.payload) {
        const payload = normalize(saved.payload);
        return payload ? { payload, offMin: Number.isFinite(saved.offMin) ? saved.offMin : deviceOffset() } : null;
      }
      const payload = normalize(saved); // cache written by an older version of this script
      return payload ? { payload, offMin: deviceOffset() } : null;
    } catch (_) {
      return null;
    }
  }
}

// Keep only today's file of a kind ("cat-2026-11-11.jpg", "theme-2026-11-11.json").
function dropOthers(prefix, keep) {
  for (const name of fm.listContents(CACHE_DIR)) {
    if (name.startsWith(prefix) && name !== keep) fm.remove(fm.joinPath(CACHE_DIR, name));
  }
}

function newestCached(prefix) {
  const name = fm.listContents(CACHE_DIR).filter((n) => n.startsWith(prefix)).sort().pop();
  return name ? fm.joinPath(CACHE_DIR, name) : null;
}

async function loadCat(dateStr) {
  const name = `cat-${dateStr}.jpg`;
  const todayPath = fm.joinPath(CACHE_DIR, name);
  if (fm.fileExists(todayPath)) return fm.readImage(todayPath);
  try {
    const req = new Request(`${SERVER}/cat/today.jpg?d=${encodeURIComponent(dateStr)}`);
    req.timeoutInterval = TIMEOUT_S * 2;
    const img = await req.loadImage();
    fm.writeImage(todayPath, img);
    dropOthers("cat-", name);
    return img;
  } catch (err) {
    console.warn(`kittyson: cat not loaded (${err}), using an older one`);
    const old = newestCached("cat-");
    return old ? fm.readImage(old) : null;
  }
}

// Text colors the server picked for today's photo. null means "use DEFAULT_THEME".
// Asked for on every run (it is a tiny reply), so a retuned server shows up right away;
// the saved copy is only for when the server cannot be reached.
async function loadTheme(dateStr) {
  const name = `theme-${dateStr}.json`;
  const todayPath = fm.joinPath(CACHE_DIR, name);
  try {
    const req = new Request(`${SERVER}/cat/today.json?d=${encodeURIComponent(dateStr)}`);
    req.timeoutInterval = TIMEOUT_S;
    const meta = await req.loadJSON();
    if (!meta || typeof meta.theme !== "object" || !meta.theme) throw new Error("no theme in reply");
    fm.writeString(todayPath, JSON.stringify(meta.theme));
    dropOthers("theme-", name);
    return meta.theme;
  } catch (err) {
    console.warn(`kittyson: theme not loaded (${err}), using the saved one or the default`);
    const old = newestCached("theme-");
    if (!old) return null;
    try { return JSON.parse(fm.readString(old)); } catch (_) { return null; }
  }
}

function palette(theme) {
  const t = Object.assign({}, DEFAULT_THEME, theme || {});
  const hex = (name) => (/^#[0-9a-f]{6}$/i.test(String(t[name])) ? t[name] : DEFAULT_THEME[name]);
  const alpha = Number(t.halo_alpha);
  return {
    punct: new Color(hex("punct")),
    key: new Color(hex("key")),
    str: new Color(hex("str")),
    halo: new Color(hex("halo"), alpha > 0 && alpha <= 1 ? alpha : DEFAULT_THEME.halo_alpha),
  };
}

// ---------- time ----------

function pad(n) { return String(n).padStart(2, "0"); }

// The server's wall clock right now, computed from the device clock.
// (The cached payload may be minutes old, so only its UTC offset is used.)
function serverClock(offMin) {
  const shifted = new Date(Date.now() + offMin * 60000);
  const y = shifted.getUTCFullYear(), mo = shifted.getUTCMonth(), d = shifted.getUTCDate();
  const midnightMs = Date.UTC(y, mo, d) - offMin * 60000;
  return {
    date: `${y}-${pad(mo + 1)}-${pad(d)}`,
    hour: shifted.getUTCHours(),
    minute: shifted.getUTCMinutes(),
    midnight: new Date(midnightMs),
    nextMidnight: new Date(midnightMs + 86400000),
  };
}

// iOS timer style drops leading zeros: 14:01:53, 9:01:53, 12:34, 5:03.
// Return the static text to put in front and how many characters the timer itself shows.
function timerShape(hour, minute) {
  if (hour >= 10) return { prefix: "", chars: 8 };
  if (hour >= 1) return { prefix: "0", chars: 7 };
  if (minute >= 10) return { prefix: "00:", chars: 5 };
  return { prefix: "00:0", chars: 4 };
}

// When the widget should next be rebuilt: at the latest in 15 minutes, earlier if the
// timer's leading-zero shape changes or the day rolls over. iOS treats this as a hint.
function nextRefresh(clock) {
  const now = Date.now();
  const candidates = [now + 15 * 60000, clock.nextMidnight.getTime() + 2000];
  const sinceMidnight = now - clock.midnight.getTime();
  for (const boundaryMin of [10, 60, 600]) {
    const at = clock.midnight.getTime() + boundaryMin * 60000;
    if (sinceMidnight < boundaryMin * 60000) candidates.push(at + 1000);
  }
  return new Date(Math.min(...candidates));
}

// ---------- layout ----------

// Approximate widget sizes in points, by screen width.
function widgetSize(family) {
  const sw = Device.screenSize().width;
  const table = [
    // [max screen width, small, medium w, large h]
    [320, 141, 292, 311],
    [375, 148, 321, 324],
    [393, 158, 338, 354],
    [414, 169, 360, 379],
    [9999, 170, 364, 382],
  ];
  const row = table.find((r) => sw <= r[0]);
  const [, small, wide, tall] = row;
  if (family === "small") return { w: small, h: small };
  if (family === "medium") return { w: wide, h: small };
  return { w: wide, h: tall };
}

// Width of a string in monospaced-character units. Hangul, CJK and emoji are wider.
function units(s) {
  let n = 0;
  for (const ch of s) {
    const c = ch.codePointAt(0);
    if (c === 0xfe0f || c === 0x200d) continue;                 // variation selector, joiner
    if (c >= 0x1f000 || (c >= 0x2600 && c <= 0x27bf)) n += 1.8; // emoji, weather symbols
    else if (c >= 0x1100 && c !== 0x2026 && !(c >= 0x2190 && c <= 0x21ff)) n += 1.5; // Hangul, CJK
    else n += 1;                                                // ASCII, °, ·, arrows
  }
  return n;
}

// Values the device fills in itself, so they stay right while the payload ages.
const TIME = { key: "time", kind: "time" };
const DATE = { key: "date", kind: "date" };

function linesFor(family, data) {
  const q = (v) => JSON.stringify(String(v ?? ""));
  const text = (key, value) => ({ key, value: q(value === undefined ? data[key] : value) });
  if (family === "small") {
    return [TIME, DATE, text("cat"), text("weather", String(data.weather || "").split(" ").slice(0, 2).join(" "))];
  }
  if (family === "medium") return [TIME, DATE, text("cat"), text("weather"), text("fortune")];
  // large: every key the server sent, in the server's order
  return Object.keys(data).map((k) => (k === "time" ? TIME : k === "date" ? DATE : text(k)));
}

// Returns a function that styles one piece of text: size, color, halo.
function penFor(colors) {
  return (el, size, color) => {
    el.font = Font.regularMonospacedSystemFont(size);
    el.textColor = color;
    el.lineLimit = 1;
    el.minimumScaleFactor = 0.7; // safety net when a row is wider than estimated
    el.shadowColor = colors.halo;
    el.shadowRadius = Math.max(2.5, Math.round(size * 2) / 10);
    el.shadowOffset = new Point(0, 0);
    return el;
  };
}

function addRow(widget) {
  const row = widget.addStack();
  row.layoutHorizontally();
  row.centerAlignContent();
  row.spacing = 0;
  return row;
}

function shadeImage(img, amount) {
  if (!img || amount <= 0) return img;
  const ctx = new DrawContext();
  ctx.size = img.size;
  ctx.opaque = true;
  ctx.respectScreenScale = false;
  ctx.drawImageInRect(img, new Rect(0, 0, img.size.width, img.size.height));
  ctx.setFillColor(new Color("#000000", amount));
  ctx.fillRect(new Rect(0, 0, img.size.width, img.size.height));
  return ctx.getImage();
}

// "HH:MM:SS" in quotes, where the tail is a live iOS timer.
function addClockValue(row, clock, size, colors, pen) {
  const shape = timerShape(clock.hour, clock.minute);
  pen(row.addText(`"${shape.prefix}`), size, colors.str);
  // A timer text grabs all free width, so pin it inside a fixed-width box.
  const box = row.addStack();
  box.size = new Size(Math.ceil(shape.chars * size * CHAR_W) + 1, 0);
  const timer = box.addDate(clock.midnight);
  timer.applyTimerStyle();
  pen(timer, size, colors.str);
  timer.minimumScaleFactor = 0.8;
  pen(row.addText(`"`), size, colors.str);
}

// A JSON line as words that are never split: the key with the start of its value, then
// the rest of the value cut at its spaces. A word is a list of colored pieces.
function wordsFor(line, comma, clock) {
  const head = [{ text: `"${line.key}"`, color: "key" }, { text: ": ", color: "punct" }];
  const tail = comma ? [{ text: ",", color: "punct" }] : [];
  if (line.kind === "time") return [[...head, { clock: true }, ...tail]];
  const value = line.kind === "date" ? `"${clock.date}"` : line.value;
  const words = value.split(" ").map((text) => [{ text, color: "str" }]);
  words[0].unshift(...head);
  words[words.length - 1].push(...tail);
  return words;
}

function wordUnits(word) {
  return word.reduce((n, piece) => n + (piece.clock ? CLOCK_UNITS : units(piece.text)), 0);
}

// Break one JSON line into rows no wider than cap characters. The first row has the
// key's indent, the following ones hang deeper. null when a single word is too wide or
// the last row would be a stub like `v1",` (a smaller font suits such a line better).
function wrap(words, cap) {
  const rows = [];
  let used = 0;
  for (const word of words) {
    const n = wordUnits(word);
    if (rows.length && used + 1 + n <= cap) {
      rows[rows.length - 1].words.push(word);
      used += 1 + n;
      continue;
    }
    const indent = rows.length ? HANG : INDENT;
    if (indent + n > cap) return null;
    rows.push({ indent, words: [word] });
    used = indent + n;
  }
  if (rows.length > 1 && used - HANG < WIDOW) return null;
  return rows;
}

// The JSON fills the widget: the biggest font at which every line, wrapped to the
// widget's width, still fits its height.
function fitJson(lines, clock, innerW, innerH) {
  const all = lines.map((line, i) => wordsFor(line, i < lines.length - 1, clock));
  for (let font = MAX_FONT; font >= MIN_FONT; font -= 0.5) {
    const wrapped = all.map((words) => wrap(words, innerW / (font * CHAR_W)));
    if (wrapped.includes(null)) continue;
    const rows = wrapped.flat();
    const count = rows.length + 2; // the braces
    const rowH = Math.round(font * TEXT_H);
    if (count * rowH + (count + 1) * font * GAP <= innerH) return { font, rows, rowH, count };
  }
  // Nothing fits: smallest font, one row per key, and iOS squeezes what is still too long.
  const rows = all.map((words) => ({ indent: INDENT, words }));
  return { font: MIN_FONT, rows, rowH: Math.round(MIN_FONT * TEXT_H), count: rows.length + 2 };
}

function drawRow(widget, row, fit, clock, colors, pen) {
  const stack = addRow(widget);
  stack.size = new Size(0, fit.rowH);
  stack.addSpacer(Math.round(row.indent * fit.font * CHAR_W));

  // Neighbouring pieces of one color become a single text.
  let text = "";
  let color = null;
  const flush = () => {
    if (text) pen(stack.addText(text), fit.font, colors[color]);
    text = "";
  };
  row.words.forEach((word, i) => {
    const space = { text: " ", color: word[0].color };
    for (const piece of i ? [space, ...word] : word) {
      if (piece.color !== color) flush();
      color = piece.color;
      if (piece.clock) addClockValue(stack, clock, fit.font, colors, pen);
      else text += piece.text;
    }
  });
  flush();
  stack.addSpacer();
}

function buildJsonWidget(data, offMin, bg, theme, family) {
  const clock = serverClock(offMin);
  const size = widgetSize(family);
  const pad = PAD[family] || PAD.large;
  const colors = palette(theme);
  const pen = penFor(colors);

  const innerH = size.h - pad * 2;
  const fit = fitJson(linesFor(family, data), clock, size.w - pad * 2, innerH);
  // Height the rows leave over is shared out between them, up to a point.
  const spare = (innerH - fit.count * fit.rowH) / (fit.count + 1);
  const gap = Math.min(Math.max(spare, fit.font * GAP), fit.font * MAX_GAP);

  const w = new ListWidget();
  w.setPadding(pad, pad, pad, pad);
  w.spacing = Math.floor(gap * 10) / 10;
  w.backgroundColor = new Color("#111111");
  if (bg) w.backgroundImage = shadeImage(bg, SHADE);
  w.url = `${SERVER}/`;
  w.refreshAfterDate = nextRefresh(clock);

  const brace = (text) => {
    const row = addRow(w);
    row.size = new Size(0, fit.rowH);
    pen(row.addText(text), fit.font, colors.punct);
    row.addSpacer();
  };

  w.addSpacer(); // the two spacers center whatever height is still left
  brace("{");
  for (const row of fit.rows) drawRow(w, row, fit, clock, colors, pen);
  brace("}");
  w.addSpacer();
  return w;
}

// Lock Screen widgets: no photo, system tint, a few plain lines.
function buildAccessoryWidget(data, family) {
  const w = new ListWidget();
  w.url = `${SERVER}/`;
  w.refreshAfterDate = new Date(Date.now() + 15 * 60000);
  if (family === "accessoryInline") {
    w.addText(`🐱 ${data.weather}`);
    return w;
  }
  if (family === "accessoryCircular") {
    const t = w.addText(String(data.weather || "🐱").split(" ").slice(0, 2).join("\n"));
    t.font = Font.boldMonospacedSystemFont(11);
    t.centerAlignText();
    return w;
  }
  const font = Font.regularMonospacedSystemFont(11);
  for (const key of ["cat", "weather", "fortune"]) {
    const t = w.addText(`"${key}": ${JSON.stringify(String(data[key] ?? ""))}`);
    t.font = font;
    t.lineLimit = 1;
    t.minimumScaleFactor = 0.6;
  }
  return w;
}

function buildErrorWidget(family) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#111111");
  const font = Font.regularMonospacedSystemFont(family === "small" ? 10 : 12);
  for (const line of ["{", `  "meow": "🙀",`, `  "error": "서버에 닿지 못했어요",`, `  "server": ${JSON.stringify(SERVER)}`, "}"]) {
    const t = w.addText(line);
    t.font = font;
    t.textColor = new Color(DEFAULT_THEME.punct);
    t.minimumScaleFactor = 0.5;
    t.lineLimit = 1;
  }
  w.refreshAfterDate = new Date(Date.now() + 5 * 60000);
  return w;
}

// ---------- main ----------

async function main() {
  const family = config.widgetFamily || "large";
  const accessory = family.startsWith("accessory");
  const loaded = await loadData();

  let widget;
  if (!loaded) {
    widget = buildErrorWidget(family);
  } else if (accessory) {
    widget = buildAccessoryWidget(loaded.payload, family);
  } else {
    const today = serverClock(loaded.offMin).date;
    const [bg, theme] = await Promise.all([loadCat(today), loadTheme(today)]);
    widget = buildJsonWidget(loaded.payload, loaded.offMin, bg, theme, family === "extraLarge" ? "large" : family);
  }

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentLarge(); // preview when run inside the app
  }
  Script.complete();
}

await main();
