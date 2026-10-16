// Builds Nebula.html — a self-updating wrapper. Run from this folder with:
//   node build.js
//
// The file it produces is tiny shell logic plus a baked-in SNAPSHOT of the
// whole site. When someone opens it, it first tries to pull the latest files
// from NEBULA_RAW (your public GitHub folder) and runs those; if there's no
// connection, it falls back to the last good copy it cached, then to the
// snapshot. So you push changes to GitHub once and everyone who already has
// the file gets them next time they open it — no re-sending the file.
//
// Re-run this whenever you change a source file, so the offline snapshot keeps
// up with what's on GitHub.

const fs = require("fs");
const path = require("path");
const dir = __dirname;

// ── Point this at the raw GitHub folder that holds index.html ────────────────
const NEBULA_RAW = "https://raw.githubusercontent.com/drew110321-spec/scavenger/nebula/";

const SHELL = ["index.html", "style.css", "library.js", "wallpaper.js", "ai.js", "app.js"];
const END = "<" + "/script>";

const readText = (f) => fs.readFileSync(path.join(dir, f), "utf8");
const readBuf = (f) => fs.readFileSync(path.join(dir, f));

function isLocal(p) {
  return !!p && !/^[a-z][a-z0-9+.-]*:/i.test(p) && p.indexOf("//") !== 0;
}
function fields(src, name) {
  const clean = String(src).replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  const re = new RegExp(name + ":\\s*\"([^\"]+)\"", "g");
  const out = []; let m;
  while ((m = re.exec(clean))) out.push(m[1]);
  return out;
}
function esc(code) {
  return String(code).split("<" + "/script").join("<\\" + "/script");
}

// pack() must stay byte-for-byte identical to the one in the boot script below,
// so the offline snapshot matches a live fetch exactly.
function pack(text, gameB64, images, boot) {
  const embeds = {};
  let tags = "";
  let n = 0;
  Object.keys(gameB64).forEach(function (url) {
    const id = "nebula-embed-" + n++;
    embeds[url] = id;
    tags += "\n  <script type=\"text/plain\" id=\"" + id + "\">\n" + gameB64[url] + "\n  " + END;
  });
  const patch = "  <script>\n  (function () {\n    var lib = window.LIBRARY || {};\n    var embeds = " + JSON.stringify(embeds) + ";\n    var images = " + JSON.stringify(images) + ";\n    (lib.games || []).concat(lib.ai || []).forEach(function (item) {\n      if (item && embeds[item.url]) item.embed = embeds[item.url];\n      if (item && images[item.image]) item.image = images[item.image];\n    });\n  })();\n  " + END;
  let html = text["index.html"];
  html = html.replace("<head>", "<head>\n  <meta name=\"nebula-boot\" content=\"" + boot + "\">");
  html = html.replace('<link rel="stylesheet" href="style.css">', "<style>\n" + text["style.css"] + "\n</style>");
  html = html.replace("  <script src=\"library.js\">" + END, "  <script>\n" + esc(text["library.js"]) + "\n  " + END + "\n" + patch + tags);
  html = html.replace("  <script src=\"wallpaper.js\">" + END, "  <script>\n" + esc(text["wallpaper.js"]) + "\n  " + END);
  html = html.replace("  <script src=\"ai.js\">" + END, "  <script>\n" + esc(text["ai.js"]) + "\n  " + END);
  html = html.replace("  <script src=\"app.js\">" + END, "  <script>\n" + esc(text["app.js"]) + "\n  " + END);
  return html;
}

// Assemble the snapshot from local files (mirrors the runtime assemble()).
function buildSnapshot() {
  const text = {};
  SHELL.forEach((p) => { text[p] = readText(p); });
  const mimes = { svg: "image/svg+xml", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif" };
  const gameUrls = fields(text["library.js"], "url").filter(isLocal);
  const imageUrls = fields(text["library.js"], "image").filter(isLocal);
  const gameB64 = {};
  gameUrls.forEach((p) => { gameB64[p] = Buffer.from(readText(p), "utf8").toString("base64"); });
  const images = {};
  imageUrls.forEach((p) => {
    const ext = (p.split(".").pop() || "").toLowerCase();
    const mime = mimes[ext] || "application/octet-stream";
    images[p] = "data:" + mime + ";base64," + readBuf(p).toString("base64");
  });
  return pack(text, gameB64, images, "snapshot");
}

// The boot script that ships inside the wrapper. NEBULA_RAW is injected below.
function bootScript() {
  return `  <script>
  // Point this at the raw GitHub folder (the one that contains index.html).
  // Everyone who already has this file then gets whatever you push there.
  var NEBULA_RAW = ${JSON.stringify(NEBULA_RAW)};

  var SHELL = ${JSON.stringify(SHELL)};

  function sourceBase() {
    var raw = String(NEBULA_RAW || "").trim();
    if (raw && raw.indexOf("OWNER/REPO") === -1) return raw.slice(-1) === "/" ? raw : raw + "/";
    if (location.protocol === "http:" || location.protocol === "https:") return location.origin + "/source/";
    return "";
  }

  function isLocal(p) {
    return !!p && !/^[a-z][a-z0-9+.-]*:/i.test(p) && p.indexOf("//") !== 0;
  }

  function fields(src, name) {
    var clean = String(src).replace(/\\/\\*[\\s\\S]*?\\*\\//g, "").replace(/^\\s*\\/\\/.*$/gm, "");
    var re = new RegExp(name + ":\\\\s*\\"([^\\"]+)\\"", "g");
    var out = [], m;
    while ((m = re.exec(clean))) out.push(m[1]);
    return out;
  }

  function utf8ToB64(str) {
    var bytes = new TextEncoder().encode(str);
    var bin = "";
    for (var i = 0; i < bytes.length; i += 0x8000) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return btoa(bin);
  }

  function b64ToUtf8(b64) {
    var bin = atob(String(b64).replace(/\\s+/g, ""));
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  var END = "<" + "/script>";

  function esc(code) {
    return String(code).split("<" + "/script").join("<\\\\" + "/script");
  }

  async function getBuf(base, path) {
    var res = await fetch(base + path + "?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) throw new Error(path + " (" + res.status + ")");
    return new Uint8Array(await res.arrayBuffer());
  }

  async function getText(base, path) {
    return new TextDecoder().decode(await getBuf(base, path));
  }

  function bufToB64(bytes) {
    var bin = "";
    for (var i = 0; i < bytes.length; i += 0x8000) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return btoa(bin);
  }

  async function assemble(base) {
    var text = {};
    await Promise.all(SHELL.map(function (p) {
      return getText(base, p).then(function (t) { text[p] = t; });
    }));
    var gameUrls = fields(text["library.js"], "url").filter(isLocal);
    var imageUrls = fields(text["library.js"], "image").filter(isLocal);
    var gameB64 = {};
    var images = {};
    await Promise.all(gameUrls.map(function (p) {
      return getText(base, p).then(function (t) { gameB64[p] = utf8ToB64(t); });
    }));
    await Promise.all(imageUrls.map(function (p) {
      return getBuf(base, p).then(function (buf) {
        var ext = (p.split(".").pop() || "").toLowerCase();
        var mime = { svg: "image/svg+xml", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif" }[ext] || "application/octet-stream";
        images[p] = "data:" + mime + ";base64," + bufToB64(buf);
      });
    }));
    return pack(text, gameB64, images, "live");
  }

  function pack(text, gameB64, images, boot) {
    var embeds = {};
    var tags = "";
    var n = 0;
    Object.keys(gameB64).forEach(function (url) {
      var id = "nebula-embed-" + n++;
      embeds[url] = id;
      tags += "\\n  <script type=\\"text/plain\\" id=\\"" + id + "\\">\\n" + gameB64[url] + "\\n  " + END;
    });
    var patch = "  <script>\\n  (function () {\\n    var lib = window.LIBRARY || {};\\n    var embeds = " + JSON.stringify(embeds) + ";\\n    var images = " + JSON.stringify(images) + ";\\n    (lib.games || []).concat(lib.ai || []).forEach(function (item) {\\n      if (item && embeds[item.url]) item.embed = embeds[item.url];\\n      if (item && images[item.image]) item.image = images[item.image];\\n    });\\n  })();\\n  " + END;
    var html = text["index.html"];
    html = html.replace("<head>", "<head>\\n  <meta name=\\"nebula-boot\\" content=\\"" + boot + "\\">");
    html = html.replace('<link rel="stylesheet" href="style.css">', "<style>\\n" + text["style.css"] + "\\n</style>");
    html = html.replace("  <script src=\\"library.js\\">" + END, "  <script>\\n" + esc(text["library.js"]) + "\\n  " + END + "\\n" + patch + tags);
    html = html.replace("  <script src=\\"wallpaper.js\\">" + END, "  <script>\\n" + esc(text["wallpaper.js"]) + "\\n  " + END);
    html = html.replace("  <script src=\\"ai.js\\">" + END, "  <script>\\n" + esc(text["ai.js"]) + "\\n  " + END);
    html = html.replace("  <script src=\\"app.js\\">" + END, "  <script>\\n" + esc(text["app.js"]) + "\\n  " + END);
    return html;
  }

  function snapshotHtml() {
    var node = document.getElementById("nebula-snapshot");
    if (!node) return "";
    try { return b64ToUtf8(node.textContent); } catch (e) { return ""; }
  }

  function showError(msg) {
    var boot = document.getElementById("boot");
    boot.innerHTML = "<p class=\\"err\\">" + msg + "</p>";
  }

  function start(html) {
    document.open();
    document.write(html);
    document.close();
  }

  (async function () {
    var base = sourceBase();
    if (base) {
      try {
        var live = await assemble(base);
        try { localStorage.setItem("nebula-live-html", live); } catch (e) {}
        start(live);
        return;
      } catch (e) {}
    }
    var cached = "";
    try { cached = localStorage.getItem("nebula-live-html") || ""; } catch (e) {}
    if (cached) { start(cached); return; }
    var snap = snapshotHtml();
    if (snap) { start(snap); return; }
    showError("Couldn't reach the latest Nebula. Open this file with a connection, or set the GitHub link at the top of it.");
  })();
  ${END}`;
}

const snapshotB64 = Buffer.from(buildSnapshot(), "utf8").toString("base64");

const wrapper = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#05030a">
  <title>Nebula</title>
  <link rel="icon" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+PGRlZnM+PHJhZGlhbEdyYWRpZW50IGlkPSJuIiBjeD0iNDIlIiBjeT0iMzglIiByPSI3MCUiPjxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iI2U3ZGJmZiIvPjxzdG9wIG9mZnNldD0iLjQ1IiBzdG9wLWNvbG9yPSIjYTQ4N2Y2Ii8+PHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjMmUxYzU0Ii8+PC9yYWRpYWxHcmFkaWVudD48L2RlZnM+PHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiByeD0iNyIgZmlsbD0iIzA1MDMwYSIvPjxjaXJjbGUgY3g9IjE1IiBjeT0iMTUiIHI9IjguNSIgZmlsbD0idXJsKCNuKSIvPjxlbGxpcHNlIGN4PSIxNiIgY3k9IjE2IiByeD0iMTMiIHJ5PSI0LjgiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2E0ODdmNiIgc3Ryb2tlLW9wYWNpdHk9Ii42IiBzdHJva2Utd2lkdGg9IjEuMyIgdHJhbnNmb3JtPSJyb3RhdGUoLTI1IDE2IDE2KSIvPjxjaXJjbGUgY3g9IjI3IiBjeT0iOSIgcj0iMS42IiBmaWxsPSIjZmZmIi8+PGNpcmNsZSBjeD0iNiIgY3k9IjIyIiByPSIxIiBmaWxsPSIjZmZmIiBvcGFjaXR5PSIuOCIvPjxjaXJjbGUgY3g9IjI0IiBjeT0iMjUiIHI9Ii44IiBmaWxsPSIjZmZmIiBvcGFjaXR5PSIuNyIvPjwvc3ZnPg==">
  <style>
    html, body { margin: 0; height: 100%; background: #05030a; color: #e7e4f2; font: 15px/1.45 "Segoe UI", system-ui, sans-serif; }
    body { display: grid; place-items: center; }
    .box { text-align: center; padding: 24px; }
    .spin { width: 28px; height: 28px; margin: 0 auto 14px; border-radius: 50%; border: 2px solid rgba(164,135,246,.25); border-top-color: #a487f6; animation: spin .8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    p { margin: 0; color: #b7b0c9; }
    .err { color: #f0a8a2; max-width: 320px; }
  </style>
</head>
<body>
  <div class="box" id="boot">
    <div class="spin"></div>
    <p>Getting the latest Nebula…</p>
  </div>
  <script type="text/plain" id="nebula-snapshot">${snapshotB64}</script>
${bootScript()}
</body>
</html>
`;

fs.writeFileSync(path.join(dir, "Nebula.html"), wrapper);
console.log("Built Nebula.html (" + (Buffer.byteLength(wrapper) / 1024).toFixed(0) + " KB).");
