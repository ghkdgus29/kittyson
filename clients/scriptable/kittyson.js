// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: orange; icon-glyph: cat;

// kittyson widget for Scriptable (https://scriptable.app)
//
// Shows /api/widget from the kittyson server as raw JSON over today's cat.
// The "now" line ticks every second: iOS draws a timer counting up from midnight,
// which reads as the current time.
//
// Server address, first match wins:
//   1. the widget's Parameter (long-press widget > Edit Widget)
//   2. SERVER in kittyson-loader.js, when this file is run through the loader
//   3. DEFAULT_SERVER below

const DEFAULT_SERVER = "http://192.168.0.10:8787";
const LOADER_SERVER = typeof KITTYSON_SERVER === "string" ? KITTYSON_SERVER : "";

// 0 = cat untouched. Raise toward 0.4 if text is hard to read on bright photos.
const SHADE = 0;

const COLORS = {
  punct: new Color("#ffffff", 0.9),
  key: new Color("#9cdcfe"),
  str: new Color("#ffd9a8"),
  now: new Color("#ffffff"),
  shadow: new Color("#000000", 0.9),
};

const CHAR_W = 0.62;   // monospaced advance, in units of font size (slightly generous)
const LINE_H = 1.4;    // line height, in units of font size
const TIMEOUT_S = 8;

const SERVER = String(args.widgetParameter || LOADER_SERVER || DEFAULT_SERVER).trim().replace(/\/+$/, "");
const fm = FileManager.local();
const CACHE_DIR = fm.joinPath(fm.cacheDirectory(), "kittyson");
if (!fm.fileExists(CACHE_DIR)) fm.createDirectory(CACHE_DIR, true);

// ---------- data ----------

async function loadData() {
  const cachePath = fm.joinPath(CACHE_DIR, "widget.json");
  try {
    const req = new Request(`${SERVER}/api/widget`);
    req.timeoutInterval = TIMEOUT_S;
    const data = await req.loadJSON();
    if (!data || typeof data.now !== "string") throw new Error("unexpected payload");
    fm.writeString(cachePath, JSON.stringify(data));
    return data;
  } catch (err) {
    console.warn(`kittyson: server unreachable (${err}), using cache`);
    if (fm.fileExists(cachePath)) {
      try { return JSON.parse(fm.readString(cachePath)); } catch (_) {}
    }
    return null;
  }
}

async function loadCat(dateStr) {
  const todayPath = fm.joinPath(CACHE_DIR, `cat-${dateStr}.jpg`);
  if (fm.fileExists(todayPath)) return fm.readImage(todayPath);
  try {
    const req = new Request(`${SERVER}/cat/today.jpg?d=${encodeURIComponent(dateStr)}`);
    req.timeoutInterval = TIMEOUT_S * 2;
    const img = await req.loadImage();
    fm.writeImage(todayPath, img);
    for (const name of fm.listContents(CACHE_DIR)) {
      if (name.startsWith("cat-") && name !== `cat-${dateStr}.jpg`) {
        fm.remove(fm.joinPath(CACHE_DIR, name));
      }
    }
    return img;
  } catch (err) {
    console.warn(`kittyson: cat not loaded (${err}), using an older one`);
    const old = fm.listContents(CACHE_DIR).filter((n) => n.startsWith("cat-")).sort().pop();
    return old ? fm.readImage(fm.joinPath(CACHE_DIR, old)) : null;
  }
}

// ---------- time ----------

function pad(n) { return String(n).padStart(2, "0"); }

// "+09:00" -> 540. Falls back to +09:00 if the string has no offset.
function offsetMinutes(iso) {
  const m = /([+-])(\d{2}):(\d{2})$/.exec(iso || "");
  if (!m) return 540;
  return (m[1] === "-" ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]));
}

function offsetString(min) {
  const abs = Math.abs(min);
  return `${min < 0 ? "-" : "+"}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

// The server's wall clock right now, computed from the device clock.
// (The cached "now" may be minutes old, so it is only used for its UTC offset.)
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
    offset: offsetString(offMin),
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
    if (c === 0xfe0f || c === 0x200d) continue;         // variation selector, joiner
    n += c >= 0x1100 ? 1.7 : 1;
  }
  return n;
}

function linesFor(family, data) {
  const q = (v) => JSON.stringify(String(v ?? ""));
  if (family === "small") {
    return [
      { key: "now", kind: "time" },
      { key: "cat", value: q(data.cat) },
      { key: "weather", value: q(String(data.weather || "").split(" ").slice(0, 2).join(" ")) },
    ];
  }
  if (family === "medium") {
    return [
      { key: "now", kind: "iso" },
      { key: "cat", value: q(data.cat) },
      { key: "weather", value: q(data.weather) },
      { key: "fortune", value: q(data.fortune) },
    ];
  }
  // large: every key the server sent, in the server's order
  return Object.keys(data).map((k) => (k === "now" ? { key: "now", kind: "iso" } : { key: k, value: q(data[k]) }));
}

function lineUnits(line) {
  const head = 2 + units(`"${line.key}": `) + 1; // indent + key + trailing comma
  if (line.kind === "iso") return head + 27;      // "2026-11-10T14:01:53+09:00"
  if (line.kind === "time") return head + 10;     // "14:01:53"
  return head + units(line.value);
}

function style(el, font, color) {
  el.font = font;
  el.textColor = color;
  el.lineLimit = 1;
  el.shadowColor = COLORS.shadow;
  el.shadowRadius = 2.5;
  el.shadowOffset = new Point(0, 0.5);
  return el;
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

function buildJsonWidget(data, bg, family) {
  const offMin = offsetMinutes(data.now);
  const clock = serverClock(offMin);
  const lines = linesFor(family, data);
  const size = widgetSize(family);
  const padding = family === "small" ? 10 : 14;

  const innerW = size.w - padding * 2;
  const innerH = size.h - padding * 2;
  const widest = Math.max(...lines.map(lineUnits));
  const byWidth = innerW / (widest * CHAR_W);
  const byHeight = innerH / ((lines.length + 2) * LINE_H);
  const fontSize = Math.max(7, Math.min(15, Math.floor(Math.min(byWidth, byHeight) * 2) / 2));

  const regular = Font.regularMonospacedSystemFont(fontSize);
  const bold = Font.boldMonospacedSystemFont(fontSize);
  const charW = fontSize * CHAR_W;

  const w = new ListWidget();
  w.setPadding(padding, padding, padding, padding);
  w.spacing = Math.round(fontSize * (LINE_H - 1.2) * 10) / 10;
  w.backgroundColor = new Color("#111111");
  if (bg) w.backgroundImage = shadeImage(bg, SHADE);
  w.url = `${SERVER}/`;
  w.refreshAfterDate = nextRefresh(clock);

  w.addSpacer(); // push the JSON block to the bottom, like the web screen

  style(addRowText(w, "{"), regular, COLORS.punct);

  lines.forEach((line, i) => {
    const comma = i < lines.length - 1 ? "," : "";
    const row = addRow(w);
    row.addSpacer(charW * 2);
    style(row.addText(`"${line.key}"`), regular, COLORS.key);
    style(row.addText(": "), regular, COLORS.punct);

    if (line.kind) {
      const shape = timerShape(clock.hour, clock.minute);
      const before = line.kind === "iso" ? `"${clock.date}T${shape.prefix}` : `"${shape.prefix}`;
      const after = line.kind === "iso" ? `${clock.offset}"` : `"`;
      style(row.addText(before), bold, COLORS.now);
      // A timer text grabs all free width, so pin it inside a fixed-width box.
      const box = row.addStack();
      box.size = new Size(Math.ceil(shape.chars * charW) + 1, 0);
      const timer = box.addDate(clock.midnight);
      timer.applyTimerStyle();
      style(timer, bold, COLORS.now);
      timer.minimumScaleFactor = 0.8;
      style(row.addText(after), bold, COLORS.now);
    } else {
      const value = style(row.addText(line.value), regular, COLORS.str);
      value.minimumScaleFactor = 0.6; // long Korean lines shrink instead of clipping
    }

    if (comma) style(row.addText(comma), regular, COLORS.punct);
    row.addSpacer();
  });

  style(addRowText(w, "}"), regular, COLORS.punct);
  return w;
}

function addRowText(widget, text) {
  const row = addRow(widget);
  const t = row.addText(text);
  row.addSpacer();
  return t;
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
    t.textColor = COLORS.punct;
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
  const data = await loadData();

  let widget;
  if (!data) {
    widget = buildErrorWidget(family);
  } else if (accessory) {
    widget = buildAccessoryWidget(data, family);
  } else {
    const today = serverClock(offsetMinutes(data.now)).date;
    const bg = await loadCat(today);
    widget = buildJsonWidget(data, bg, family === "extraLarge" ? "large" : family);
  }

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentLarge(); // preview when run inside the app
  }
  Script.complete();
}

await main();
