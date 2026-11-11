// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: orange; icon-glyph: cat;

// kittyson loader for Scriptable (https://scriptable.app)
//
// Paste this once. On every run it downloads the newest kittyson.js from GitHub and runs it,
// so a push to main reaches the phone without touching Scriptable again.
// The last downloaded copy is kept, and used when GitHub cannot be reached.
//
// Server address: the widget's Parameter wins, then SERVER below.

const SERVER = "http://192.168.0.10:8787";

const SOURCE = "https://raw.githubusercontent.com/ghkdgus29/kittyson/main/clients/scriptable/kittyson.js";
const TIMEOUT_S = 6;

const fm = FileManager.local();
const dir = fm.joinPath(fm.documentsDirectory(), "kittyson-loader");
if (!fm.fileExists(dir)) fm.createDirectory(dir, true);
const cached = fm.joinPath(dir, "kittyson.js");

async function latestCode() {
  try {
    const req = new Request(SOURCE);
    req.timeoutInterval = TIMEOUT_S;
    const code = await req.loadString();
    const status = req.response && req.response.statusCode;
    if (status && status !== 200) throw new Error(`HTTP ${status}`);
    if (!code || !code.includes("kittyson")) throw new Error("unexpected script body");
    fm.writeString(cached, code);
    return code;
  } catch (err) {
    console.warn(`kittyson-loader: download failed (${err}), using the saved copy`);
    return fm.fileExists(cached) ? fm.readString(cached) : null;
  }
}

const code = await latestCode();
if (code) {
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  await new AsyncFunction("KITTYSON_SERVER", code)(SERVER);
} else {
  const w = new ListWidget();
  w.backgroundColor = new Color("#1e1e1e");
  const t = w.addText('{ "meow": "🙀 loader offline" }');
  t.font = Font.regularMonospacedSystemFont(12);
  t.textColor = new Color("#ffd9a8");
  if (config.runsInWidget) Script.setWidget(w);
  else await w.presentMedium();
  Script.complete();
}
