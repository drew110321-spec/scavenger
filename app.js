(function () {
  "use strict";

  const lib = window.LIBRARY || {};
  const siteName = lib.siteName || "Nebula";
  const sections = {
    games: { title: "Games", noun: "games", items: lib.games || [] },
    ai: { title: "AI", noun: "AI tools", items: lib.ai || [] }
  };

  /* ---------- Saved state (kept in this browser only) ---------- */

  const ACCENTS = { purple: "#a487f6", violet: "#8f7dff", pink: "#ee84b9", blue: "#71aaf5", teal: "#55c9b8", red: "#f27e74" };
  const WALLPAPERS = [["space", "Space"], ["nebula", "Nebula"], ["stars", "Starfield"], ["dusk", "Horizon"], ["black", "Black"]];
  const DEFAULTS = {
    wallpaper: "space", accent: "purple", transparency: true, iconSize: "medium", motion: true, meteors: true,
    clock24: false, showDate: true, taskbarAlign: "center", brightness: 100, nightLight: false,
    userName: "Guest", lockOnStart: true
  };
  const load = (key, fallback) => {
    try { const v = JSON.parse(localStorage.getItem(key)); return v == null ? fallback : v; } catch (_) { return fallback; }
  };
  const save = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* applied, just not remembered */ }
  };
  let settings = Object.assign({}, DEFAULTS, load("nebula-settings", {}));
  let recent = load("nebula-recent", []);
  if (!Array.isArray(recent)) recent = [];

  /* ---------- Helpers ---------- */

  // h("div", { class: "x", onclick: fn }, child, "text")
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    el.append(...kids.flat().filter((c) => c != null && c !== false));
    return el;
  }
  const $ = (sel) => document.querySelector(sel);
  const clamp = (n, lo, hi) => Math.min(Math.max(n, lo), hi);
  const slug = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const itemId = (item, i) => slug(item.title) || String(i);
  const matches = (item, q) => `${item.title || ""} ${item.description || ""}`.toLowerCase().includes(q);
  const sameDay = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

  function timeAgo(ms) {
    const s = (Date.now() - ms) / 1000;
    if (s < 60) return "Just now";
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return new Date(ms).toLocaleDateString([], { month: "short", day: "numeric" });
  }

  /* ---------- Icons ---------- */

  const line = (body, w = 1.6) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  // Window caption glyphs are drawn on a 10px grid so their 1px lines stay crisp.
  const cap = (body) => `<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">${body}</svg>`;

  const GLOBE = '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a13.5 13.5 0 0 0 0 18a13.5 13.5 0 0 0 0-18"/>';
  const PAD = '<path d="M6.5 7h11a4.5 4.5 0 0 1 4.5 4.5v1a4.5 4.5 0 0 1-8 2.8H10a4.5 4.5 0 0 1-8-2.8v-1A4.5 4.5 0 0 1 6.5 7z"/><path d="M6 11.5h3M7.5 10v3"/><circle cx="15.5" cy="10.8" r=".9" fill="currentColor" stroke="none"/><circle cx="17.6" cy="12.8" r=".9" fill="currentColor" stroke="none"/>';
  const CHAT = '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 3.5V17A2.5 2.5 0 0 1 4 14.5z"/><path d="M8.5 10.5h.01M12 10.5h.01M15.5 10.5h.01" stroke-width="2.6"/>';
  const GEAR_D = "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z";

  const ICONS = {
    games: line(PAD),
    ai: line(CHAT),
    globe: line(GLOBE),
    gear: line(`<path d="${GEAR_D}"/><circle cx="12" cy="12" r="3"/>`),
    logo: line('<path d="M14.5 3.5a8.5 8.5 0 1 0 6 14.5a9 9 0 0 1-6-14.5z" fill="currentColor" stroke="none"/><circle cx="19" cy="5" r="1.2" fill="currentColor" stroke="none"/>'),
    min: cap('<path d="M0 5.5h10"/>'),
    max: cap('<rect x=".5" y=".5" width="9" height="9" rx="1.5"/>'),
    restore: cap('<rect x=".5" y="2.5" width="7" height="7" rx="1.2"/><path d="M2.5 2.5v-.7A1.3 1.3 0 0 1 3.8.5h4.4a1.3 1.3 0 0 1 1.3 1.3v4.4a1.3 1.3 0 0 1-1.3 1.3h-.7"/>'),
    close: cap('<path d="M.5.5l9 9M9.5.5l-9 9"/>'),
    x: line('<path d="M6 6l12 12M18 6L6 18"/>'),
    external: line('<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>'),
    back: line('<path d="M19 12H5M11 6l-6 6 6 6"/>'),
    forward: line('<path d="M5 12h14M13 6l6 6-6 6"/>'),
    reload: line('<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v5h-5"/>'),
    home: line('<path d="M4 11l8-7 8 7"/><path d="M6 9.5V20h12V9.5"/>'),
    plus: line('<path d="M12 5v14M5 12h14"/>'),
    search: line('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>'),
    lock: line('<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>'),
    chevron: line('<path d="M9 6l6 6-6 6"/>'),
    chevronLeft: line('<path d="M15 6l-6 6 6 6"/>'),
    up: line('<path d="M6 15l6-6 6 6"/>'),
    down: line('<path d="M6 9l6 6 6-6"/>'),
    palette: line('<path d="M12 3a9 9 0 1 0 0 18c1 0 1.5-.8 1.5-1.5 0-.4-.2-.8-.4-1.1-.3-.3-.4-.6-.4-1.1 0-.8.7-1.5 1.5-1.5H16a5 5 0 0 0 5-5c0-4.4-4-7.8-9-7.8z"/><circle cx="7.5" cy="11" r="1" fill="currentColor"/><circle cx="10" cy="7" r="1" fill="currentColor"/><circle cx="15" cy="7.5" r="1" fill="currentColor"/>'),
    monitor: line('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>'),
    taskbar: line('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 16h18M7 18h2"/>'),
    clock: line('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    user: line('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
    power: line('<path d="M12 3v8"/><path d="M6.3 6.3a8 8 0 1 0 11.4 0"/>'),
    restart: line('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>'),
    wifi: line('<path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5 12a10.5 10.5 0 0 1 14 0"/><path d="M8.5 15.5a5.5 5.5 0 0 1 7 0"/><circle cx="12" cy="19" r="1" fill="currentColor"/>'),
    wifiOff: line('<path d="M3 3l18 18"/><path d="M8.5 15.5a5.5 5.5 0 0 1 7 0"/><path d="M5 12a10.5 10.5 0 0 1 5-2.7"/><path d="M2 8.5a15 15 0 0 1 4.5-3"/><circle cx="12" cy="19" r="1" fill="currentColor"/>'),
    sun: line('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    night: line('<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>'),
    layers: line('<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
    star: line('<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z"/>'),
    comet: line('<circle cx="16.5" cy="7.5" r="3"/><path d="M14 10L4 20M11.5 6.5L6 12M17.5 12.5L12 18"/>'),
    image: line('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>'),
    apps: line('<rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/>'),
    dot: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.5" fill="currentColor"/></svg>'
  };

  function batteryIcon(level, charging) {
    const w = Math.max(1, Math.round(12 * level));
    return line(`<rect x="2.5" y="7" width="16.5" height="10" rx="2.5"/><path d="M21.5 10.5v3"/><rect x="4.5" y="9" width="${w}" height="6" rx="1" fill="currentColor" stroke="none"/>` +
      (charging ? '<path d="M11.8 8.2l-2.4 4h3.2l-2.4 4" stroke="var(--tray-bg)" stroke-width="1.6"/>' : ""));
  }

  // Full-color app icons, shaped like the thing they are. Gradient ids are unique per copy.
  let uid = 0;
  function appArt(id) {
    const u = `g${++uid}`;
    const grad = (a, b) => `<defs><linearGradient id="${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>`;
    const open = '<svg viewBox="0 0 48 48" aria-hidden="true">';
    if (id === "games") {
      return open + grad("#ae95ff", "#6340d6") +
        `<path d="M15 13h18c6.1 0 10.6 5.6 9.4 11.6l-1.7 8.4c-.7 3.4-3.7 5.9-7.2 5.9-2.4 0-4.6-1.2-5.9-3.2L26.3 33h-4.6l-1.3 2.7c-1.3 2-3.5 3.2-5.9 3.2-3.5 0-6.5-2.5-7.2-5.9l-1.7-8.4C4.4 18.6 8.9 13 15 13z" fill="url(#${u})"/>` +
        '<path d="M9.6 16.2C11 14.2 12.9 13 15 13h18c2.1 0 4 1.2 5.4 3.2" fill="none" stroke="#fff" stroke-opacity=".35"/>' +
        '<path d="M14.5 20.5v3h-3v3h3v3h3v-3h3v-3h-3v-3z" fill="#fff" fill-opacity=".95"/>' +
        '<circle cx="31.6" cy="22.6" r="2.1" fill="#fff" fill-opacity=".95"/><circle cx="35.7" cy="26.8" r="2.1" fill="#fff" fill-opacity=".95"/></svg>';
    }
    if (id === "ai") {
      return open + grad("#98a8ff", "#4a54d6") +
        `<path d="M11 8.5h26a6 6 0 0 1 6 6v15a6 6 0 0 1-6 6H23.5L15 42.5v-7h-4a6 6 0 0 1-6-6v-15a6 6 0 0 1 6-6z" fill="url(#${u})"/>` +
        '<path d="M6.4 11.6A6 6 0 0 1 11 8.5h26a6 6 0 0 1 4.6 3.1" fill="none" stroke="#fff" stroke-opacity=".35"/>' +
        '<circle cx="16" cy="22" r="2.5" fill="#fff"/><circle cx="24" cy="22" r="2.5" fill="#fff"/><circle cx="32" cy="22" r="2.5" fill="#fff"/></svg>';
    }
    if (id === "settings") {
      return open + grad("#c4c8d6", "#6b7088") +
        `<g transform="translate(3 3) scale(1.75)"><path d="${GEAR_D}" fill="url(#${u})"/></g>` +
        '<circle cx="24" cy="24" r="6.2" fill="#2a2733"/><circle cx="24" cy="24" r="6.2" fill="none" stroke="#000" stroke-opacity=".2"/></svg>';
    }
    // Browser: a ringed planet.
    return open +
      `<defs><radialGradient id="${u}" cx=".34" cy=".3" r=".8"><stop offset="0" stop-color="#c4b2ff"/><stop offset=".5" stop-color="#7a55dc"/><stop offset="1" stop-color="#3a2290"/></radialGradient></defs>` +
      '<path d="M3 24a21 6.5 0 0 1 42 0" transform="rotate(-18 24 24)" fill="none" stroke="#d9ccff" stroke-opacity=".7" stroke-width="2.6" stroke-linecap="round"/>' +
      `<circle cx="24" cy="24" r="13" fill="url(#${u})"/>` +
      '<path d="M14.5 20c3.2 1.4 6.6 1 9.6-.5M15.5 28.5c2.8-.9 5.6-.7 8.6.5M27 15.5c1.8.6 3.2 1.6 4.2 3" stroke="#fff" stroke-opacity=".22" stroke-width="1.5" stroke-linecap="round" fill="none"/>' +
      '<path d="M3 24a21 6.5 0 0 0 42 0" transform="rotate(-18 24 24)" fill="none" stroke="#ece5ff" stroke-width="2.6" stroke-linecap="round"/></svg>';
  }

  const APPS = [
    { id: "games", key: "app:games", name: "Games", open: () => openLibrary("games") },
    { id: "ai", key: "app:ai", name: "AI", open: () => openAI() },
    { id: "settings", key: "app:settings", name: "Settings", open: () => openSettings(), desktop: false }
  ];
  const appById = (id) => APPS.find((a) => a.id === id);
  const appTile = (app, size) => h("span", { class: `app-icon sz-${size}`, html: appArt(app.id) });
  const avatar = (size) => h("span", { class: `avatar av-${size}`, html: ICONS.user });

  // Icon for a library item: its image, or its first letter on a flat color.
  function itemArt(item, size) {
    const el = h("span", { class: `tile sz-${size}` });
    if (item.image) {
      el.append(h("img", { src: item.image, alt: "", loading: "lazy" }));
    } else {
      let hue = 0;
      for (const ch of String(item.title)) hue = (hue * 31 + ch.charCodeAt(0)) % 100;
      el.style.background = `linear-gradient(160deg, hsl(${(hue + 235) % 360} 45% 50%), hsl(${(hue + 245) % 360} 50% 34%))`;
      el.textContent = String(item.title || "?").trim().charAt(0).toUpperCase();
    }
    return el;
  }

  function remember(entry) {
    recent = [Object.assign({ at: Date.now() }, entry),
      ...recent.filter((r) => !(r.kind === entry.kind && r.id === entry.id && r.section === entry.section))].slice(0, 8);
    save("nebula-recent", recent);
  }

  /* ---------- Window manager ---------- */

  const desktop = $("#desktop");
  const snapEl = $("#snap");
  const wins = new Map();
  let zTop = 10;
  let cascade = 0;
  let activeKey = null;
  const small = () => innerWidth < 700;

  function openWindow(opts) {
    const existing = wins.get(opts.key);
    if (existing) {
      restore(existing);
      return existing;
    }

    const area = desktop.getBoundingClientRect();
    const width = Math.min(opts.width || 860, area.width - 32);
    const height = Math.min(opts.height || 560, area.height - 32);
    const step = (cascade++ % 6) * 28;
    const left = clamp((area.width - width) / 2 - 70 + step, 0, Math.max(0, area.width - width));
    const top = clamp((area.height - height) / 2 - 60 + step, 0, Math.max(0, area.height - height));

    const w = { key: opts.key, title: opts.title, art: opts.art, onClose: opts.onClose, minimized: false, maximized: false, snapped: null, rest: null };

    w.maxBtn = h("button", { class: "wc", type: "button", title: "Maximize", "aria-label": "Maximize", html: ICONS.max, onclick: () => (w.maximized || w.snapped ? unsnap(w) : setMax(w, true)) });
    const ctrls = h("div", { class: "win-ctrls" },
      opts.popout && h("button", {
        class: "wc", type: "button", title: "Open in a new browser tab", "aria-label": "Open in a new browser tab", html: ICONS.external,
        onclick: () => {
          const out = opts.popout(); if (!out) return;
          const win = window.open("about:blank", "_blank");
          if (!win) return; // popup blocked
          let doc = out.html;
          if (!doc && out.url) {
            doc = '<!doctype html><meta charset="utf-8"><title>Nebula</title>'
              + '<style>html,body{margin:0;height:100%;overflow:hidden;background:#05030a}iframe{border:0;display:block;width:100vw;height:100vh}</style>'
              + '<iframe src="' + String(out.url).replace(/"/g, "&quot;") + '" allow="fullscreen; autoplay; gamepad; clipboard-write; microphone" allowfullscreen></iframe>';
          }
          try { win.document.open(); win.document.write(doc || ""); win.document.close(); } catch (e) {}
        }
      }),
      h("button", { class: "wc", type: "button", title: "Minimize", "aria-label": "Minimize", html: ICONS.min, onclick: () => minimize(w) }),
      w.maxBtn,
      h("button", { class: "wc wc-close", type: "button", title: "Close", "aria-label": "Close", html: ICONS.close, onclick: () => close(w) })
    );
    const bar = h("div", { class: `win-bar${opts.barContent ? " tall" : ""}` },
      h("span", { class: "win-icon" }, opts.art("xs")),
      opts.barContent || h("span", { class: "win-title" }, opts.title),
      ctrls
    );
    w.el = h("section", { class: "win opening", role: "dialog", "aria-label": opts.title },
      bar,
      h("div", { class: "win-body" }, opts.body),
      ["n", "s", "e", "w", "ne", "nw", "se", "sw"].map((d) => h("div", { class: `rz rz-${d}`, "data-dir": d }))
    );
    Object.assign(w.el.style, { left: left + "px", top: top + "px", width: width + "px", height: height + "px" });
    desktop.append(w.el);
    wins.set(w.key, w);

    w.el.addEventListener("pointerdown", () => focus(w), true);
    w.el.addEventListener("animationend", () => w.el.classList.remove("opening"));
    bar.addEventListener("dblclick", (e) => { if (!e.target.closest("button, .b-tab")) (w.maximized ? setMax(w, false) : setMax(w, true)); });
    bar.addEventListener("pointerdown", (e) => startDrag(e, w, bar));
    bar.addEventListener("contextmenu", (e) => {
      if (e.target.closest(".b-tab, input")) return;
      e.preventDefault();
      showMenu(e.clientX, e.clientY, [
        { label: "Restore", icon: ICONS.restore, disabled: !w.maximized && !w.snapped, action: () => unsnap(w) },
        { label: "Minimize", icon: ICONS.min, action: () => minimize(w) },
        { label: "Maximize", icon: ICONS.max, disabled: w.maximized, action: () => setMax(w, true) },
        "sep",
        { label: "Close", icon: ICONS.close, action: () => close(w) }
      ]);
    });
    w.el.querySelectorAll(":scope > .rz").forEach((r) => r.addEventListener("pointerdown", (e) => startResize(e, w, r)));

    if (small()) setMax(w, true);
    focus(w);
    return w;
  }

  function focus(w) {
    if (w) {
      w.el.style.zIndex = ++zTop;
      activeKey = w.key;
    } else {
      activeKey = null;
    }
    for (const x of wins.values()) x.el.classList.toggle("active", x.key === activeKey);
    renderTaskbar();
  }

  function focusTop() {
    let best = null;
    for (const x of wins.values()) if (!x.minimized && (!best || +x.el.style.zIndex > +best.el.style.zIndex)) best = x;
    focus(best);
  }

  function minimize(w) {
    w.minimized = true;
    w.el.classList.add("min");
    if (activeKey === w.key) focusTop();
    else renderTaskbar();
  }

  function restore(w) {
    w.minimized = false;
    w.el.classList.remove("min");
    focus(w);
  }

  function close(w) {
    if (!w || !wins.has(w.key)) return;
    wins.delete(w.key);
    w.el.classList.add("closing");
    setTimeout(() => w.el.remove(), 150);
    if (w.onClose) w.onClose();
    if (activeKey === w.key) focusTop();
    else renderTaskbar();
  }

  function setMax(w, on) {
    if (!on && small()) return;
    if (on && w.snapped) unsnapSize(w);
    w.maximized = on;
    w.el.classList.toggle("max", on);
    syncMaxButton(w);
  }

  function syncMaxButton(w) {
    const restoreable = w.maximized || !!w.snapped;
    w.maxBtn.innerHTML = restoreable ? ICONS.restore : ICONS.max;
    w.maxBtn.title = restoreable ? "Restore" : "Maximize";
    w.maxBtn.setAttribute("aria-label", w.maxBtn.title);
  }

  function snapTo(w, side) {
    const area = desktop.getBoundingClientRect();
    if (!w.snapped) w.rest = { width: w.el.offsetWidth, height: w.el.offsetHeight };
    w.snapped = side;
    const half = Math.round(area.width / 2);
    Object.assign(w.el.style, { left: (side === "left" ? 0 : area.width - half) + "px", top: "0px", width: half + "px", height: area.height + "px" });
    w.el.classList.add("snapped");
    syncMaxButton(w);
  }

  function unsnapSize(w) {
    if (!w.snapped) return;
    w.snapped = null;
    w.el.classList.remove("snapped");
    if (w.rest) Object.assign(w.el.style, { width: w.rest.width + "px", height: w.rest.height + "px" });
    w.rest = null;
    syncMaxButton(w);
  }

  function unsnap(w) {
    if (w.maximized) return setMax(w, false);
    if (!w.snapped) return;
    unsnapSize(w);
    const area = desktop.getBoundingClientRect();
    w.el.style.left = Math.max(0, (area.width - w.el.offsetWidth) / 2) + "px";
    w.el.style.top = Math.max(0, (area.height - w.el.offsetHeight) / 2) + "px";
  }

  function snapZone(ev, area) {
    const x = ev.clientX - area.left, y = ev.clientY - area.top;
    if (y <= 4) return "max";
    if (x <= 4) return "left";
    if (x >= area.width - 5) return "right";
    return null;
  }

  function showSnap(zone, area) {
    snapEl.hidden = !zone;
    if (!zone) return;
    const half = area.width / 2;
    const r = zone === "max" ? [6, 6, area.width - 12, area.height - 12]
      : zone === "left" ? [6, 6, half - 9, area.height - 12]
        : [half + 3, 6, half - 9, area.height - 12];
    Object.assign(snapEl.style, { left: r[0] + "px", top: r[1] + "px", width: r[2] + "px", height: r[3] + "px" });
  }

  function startDrag(e, w, bar) {
    if (e.button !== 0 || small() || e.target.closest("button, input, .b-tab")) return;
    e.preventDefault();
    const area = desktop.getBoundingClientRect();
    let sx = e.clientX, sy = e.clientY, sl = w.el.offsetLeft, st = w.el.offsetTop;
    let moved = false, zone = null;
    bar.setPointerCapture(e.pointerId);
    document.body.classList.add("dragging");

    const move = (ev) => {
      if (!moved) {
        if (Math.hypot(ev.clientX - sx, ev.clientY - sy) < 4) return;
        moved = true;
        if (w.maximized || w.snapped) {
          // Pull the window free, keeping the cursor at the same spot on the title bar.
          const ratio = (sx - area.left - w.el.offsetLeft) / w.el.offsetWidth;
          if (w.maximized) setMax(w, false);
          else unsnapSize(w);
          sl = ev.clientX - area.left - w.el.offsetWidth * ratio;
          st = 0;
          sx = ev.clientX;
          sy = ev.clientY;
        }
      }
      w.el.style.left = clamp(sl + ev.clientX - sx, 80 - w.el.offsetWidth, area.width - 80) + "px";
      w.el.style.top = clamp(st + ev.clientY - sy, 0, area.height - 40) + "px";
      zone = snapZone(ev, area);
      showSnap(zone, area);
    };
    const end = () => {
      bar.removeEventListener("pointermove", move);
      bar.removeEventListener("pointerup", end);
      bar.removeEventListener("pointercancel", end);
      document.body.classList.remove("dragging");
      if (moved && zone === "max") setMax(w, true);
      else if (moved && zone) snapTo(w, zone);
      showSnap(null, area);
    };
    bar.addEventListener("pointermove", move);
    bar.addEventListener("pointerup", end);
    bar.addEventListener("pointercancel", end);
  }

  function startResize(e, w, handle) {
    if (e.button !== 0 || w.maximized) return;
    e.preventDefault();
    if (w.snapped) { w.snapped = null; w.rest = null; w.el.classList.remove("snapped"); syncMaxButton(w); }
    const dir = handle.dataset.dir;
    const s = { x: e.clientX, y: e.clientY, l: w.el.offsetLeft, t: w.el.offsetTop, w: w.el.offsetWidth, h: w.el.offsetHeight };
    handle.setPointerCapture(e.pointerId);
    document.body.classList.add("dragging");

    const move = (ev) => {
      const dx = ev.clientX - s.x, dy = ev.clientY - s.y;
      let l = s.l, t = s.t, width = s.w, height = s.h;
      if (dir.includes("e")) width = Math.max(360, s.w + dx);
      if (dir.includes("s")) height = Math.max(240, s.h + dy);
      if (dir.includes("w")) { width = Math.max(360, s.w - dx); l = s.l + s.w - width; }
      if (dir.includes("n")) { height = Math.max(240, s.h - dy); t = Math.max(0, s.t + s.h - height); height = s.t + s.h - t; }
      Object.assign(w.el.style, { left: l + "px", top: t + "px", width: width + "px", height: height + "px" });
    };
    const end = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", end);
      handle.removeEventListener("pointercancel", end);
      document.body.classList.remove("dragging");
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
  }

  // Clicks inside a game or web page never reach this page, so watch for focus moving into a frame.
  window.addEventListener("blur", () => setTimeout(() => {
    const a = document.activeElement;
    if (!a || a.tagName !== "IFRAME") return;
    closePanels();
    for (const w of wins.values()) if (w.el.contains(a) && w.key !== activeKey) focus(w);
  }));

  window.addEventListener("resize", () => {
    const area = desktop.getBoundingClientRect();
    for (const w of wins.values()) {
      if (small()) { setMax(w, true); continue; }
      if (w.snapped) { snapTo(w, w.snapped); continue; }
      w.el.style.left = clamp(w.el.offsetLeft, 80 - w.el.offsetWidth, area.width - 80) + "px";
      w.el.style.top = clamp(w.el.offsetTop, 0, area.height - 40) + "px";
    }
  });

  /* ---------- Context menus ---------- */

  const menuEl = h("div", { class: "menu", role: "menu", hidden: true });
  document.body.append(menuEl);

  // items: { label, icon?, art?, checked?, disabled?, hint?, action } or "sep"
  function showMenu(x, y, items, opts = {}) {
    menuEl.replaceChildren(...items.map((it) => {
      if (it === "sep") return h("div", { class: "menu-sep", role: "separator" });
      const ico = h("span", { class: "menu-ico", html: it.checked ? ICONS.dot : it.icon || "" });
      if (it.art) ico.append(it.art);
      return h("button", {
        class: "menu-item", type: "button", role: it.checked != null ? "menuitemradio" : "menuitem",
        "aria-checked": it.checked != null ? String(!!it.checked) : null, disabled: !!it.disabled,
        onclick: () => { hideMenu(); it.action(); }
      }, ico, h("span", { class: "menu-label" }, it.label), it.hint && h("span", { class: "menu-hint" }, it.hint));
    }));
    menuEl.hidden = false;
    const r = menuEl.getBoundingClientRect();
    let left = opts.center ? x - r.width / 2 : x;
    let top = opts.above ? y - r.height - 8 : y;
    left = clamp(left, 4, innerWidth - r.width - 4);
    top = clamp(top, 4, innerHeight - r.height - 4);
    menuEl.style.left = left + "px";
    menuEl.style.top = top + "px";
    const first = menuEl.querySelector(".menu-item:not(:disabled)");
    if (first && opts.focus) first.focus();
  }
  function hideMenu() { menuEl.hidden = true; }

  /* ---------- Taskbar ---------- */

  const taskbarEl = $("#taskbar");
  const taskApps = $("#task-apps");

  function renderTaskbar() {
    const entries = APPS.map((a) => ({ key: a.key, name: a.name, art: (s) => appTile(a, s), open: a.open }));
    for (const w of wins.values()) {
      if (!APPS.some((a) => a.key === w.key)) entries.push({ key: w.key, name: w.title, art: w.art });
    }
    taskApps.replaceChildren(...entries.map((en) => {
      const w = wins.get(en.key);
      const active = !!w && !w.minimized && en.key === activeKey;
      const btn = h("button", {
        class: `tb-btn${w ? " running" : ""}${active ? " active" : ""}`, type: "button", title: en.name, "aria-label": en.name,
        onclick: () => {
          if (!w) return en.open();
          if (active) minimize(w);
          else restore(w);
        }
      }, en.art("sm"));
      btn.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const r = btn.getBoundingClientRect();
        const items = [];
        if (en.open) items.push({ label: en.name, art: en.art("xs"), action: en.open });
        if (w) {
          if (items.length) items.push("sep");
          items.push({ label: "Close window", icon: ICONS.x, action: () => close(w) });
        }
        showMenu(r.left + r.width / 2, r.top, items, { above: true, center: true });
      });
      return btn;
    }));
  }

  taskbarEl.addEventListener("contextmenu", (e) => {
    if (e.target.closest("button")) return;
    e.preventDefault();
    showMenu(e.clientX, e.clientY, [{ label: "Taskbar settings", icon: ICONS.gear, action: () => openSettings("taskbar") }], { above: true });
  });

  let peeked = [];
  $("#show-desktop").addEventListener("click", () => {
    const open = [...wins.values()].filter((w) => !w.minimized);
    if (open.length) {
      peeked = open;
      for (const w of open) { w.minimized = true; w.el.classList.add("min"); }
      focus(null);
    } else {
      peeked.filter((w) => wins.has(w.key)).forEach(restore);
      peeked = [];
    }
  });

  /* ---------- Clock ---------- */

  const formatTime = (d) => settings.clock24
    ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
    : d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hourCycle: "h12" }).replace(/\s?[AP]\.?M\.?$/i, "");
  const formatDay = (d) => d.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });

  function tick() {
    const now = new Date();
    $("#clock-time").textContent = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hourCycle: settings.clock24 ? "h23" : "h12" });
    $("#clock-date").textContent = now.toLocaleDateString();
    $("#clock-date").hidden = !settings.showDate;
    $("#clock-btn").title = now.toLocaleDateString([], { weekday: "long", year: "numeric", month: "long", day: "numeric" });
    document.querySelectorAll(".sp-clock, .lock-time").forEach((el) => { el.textContent = formatTime(now); });
    document.querySelectorAll(".sp-date, .lock-date").forEach((el) => { el.textContent = formatDay(now); });
  }
  setInterval(tick, 5000);

  /* ---------- Network and battery ---------- */

  const battery = { known: false, level: 1, charging: true };

  function renderTray() {
    $("#net-ico").innerHTML = navigator.onLine ? ICONS.wifi : ICONS.wifiOff;
    $("#net-ico").title = navigator.onLine ? "Connected" : "No internet";
    const bat = $("#bat-ico");
    bat.hidden = !battery.known;
    if (battery.known) {
      bat.innerHTML = batteryIcon(battery.level, battery.charging);
      bat.title = batteryText();
    }
  }
  function batteryText() {
    if (!battery.known) return "";
    return `${Math.round(battery.level * 100)}%${battery.charging ? " · Charging" : ""}`;
  }
  addEventListener("online", renderTray);
  addEventListener("offline", renderTray);
  if (navigator.getBattery) {
    navigator.getBattery().then((b) => {
      const update = () => {
        // A desktop with no battery reports "full and charging forever", so hide it then.
        battery.known = !(b.level === 1 && b.charging && b.chargingTime === 0);
        battery.level = b.level;
        battery.charging = b.charging;
        renderTray();
      };
      ["levelchange", "chargingchange", "chargingtimechange"].forEach((ev) => b.addEventListener(ev, update));
      update();
    }).catch(() => {});
  }

  /* ---------- Flyouts (Start, quick settings, calendar) ---------- */

  const panels = {};
  let openPanelName = null;

  function togglePanel(name) {
    if (openPanelName === name) closePanels();
    else openPanel(name);
  }
  function openPanel(name) {
    closePanels();
    const p = panels[name];
    if (p.render) p.render();
    p.el.hidden = false;
    p.button.classList.add("open");
    openPanelName = name;
    if (p.onOpen) p.onOpen();
  }
  function closePanels() {
    for (const p of Object.values(panels)) {
      p.el.hidden = true;
      p.button.classList.remove("open");
    }
    openPanelName = null;
    hideMenu();
  }

  document.addEventListener("pointerdown", (e) => {
    if (!menuEl.hidden && !menuEl.contains(e.target)) hideMenu();
    if (!openPanelName) return;
    const p = panels[openPanelName];
    if (!p.el.contains(e.target) && !p.button.contains(e.target) && !menuEl.contains(e.target)) closePanels();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePanels();
  });

  /* Start menu */

  const startEl = $("#start");
  const startBtn = $("#start-btn");
  startBtn.innerHTML = ICONS.logo;
  const startInput = h("input", { type: "search", placeholder: "Search for apps, games and the web", "aria-label": "Search", autocomplete: "off", spellcheck: "false" });
  const startBody = h("div", { class: "start-body" });
  let startView = "home";

  startEl.append(
    h("div", { class: "start-search-wrap" }, h("div", { class: "field start-search" }, h("span", { html: ICONS.search }), startInput)),
    startBody,
    h("div", { class: "start-foot" },
      h("button", { class: "start-user", type: "button", onclick: () => { closePanels(); openSettings("accounts"); } },
        avatar("sm"), h("span", { class: "user-name" }, settings.userName)),
      h("button", {
        class: "start-power", type: "button", title: "Power", "aria-label": "Power", html: ICONS.power,
        onclick: (e) => {
          const r = e.currentTarget.getBoundingClientRect();
          showMenu(r.left + r.width / 2, r.top, [
            { label: "Lock", icon: ICONS.lock, action: lock },
            { label: "Restart", icon: ICONS.restart, action: () => location.reload() }
          ], { above: true, center: true });
        }
      }))
  );

  panels.start = {
    el: startEl,
    button: startBtn,
    render: () => { startInput.value = ""; startView = "home"; renderStart(); },
    onOpen: () => startInput.focus()
  };
  startBtn.addEventListener("click", () => togglePanel("start"));
  startInput.addEventListener("input", renderStart);
  startInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && startInput.value.trim()) {
      const first = startBody.querySelector(".start-row");
      if (first) first.click();
    }
  });

  const allItems = () => Object.entries(sections).flatMap(([key, sec]) => sec.items.map((item, i) => ({ key, sec, item, i })));
  const launch = (fn) => { closePanels(); fn(); };
  const row = (art, title, sub, fn) =>
    h("button", { class: "start-row", type: "button", onclick: () => launch(fn) }, art,
      h("span", { class: "row-text" }, h("span", { class: "row-title" }, title), sub && h("span", { class: "row-sub" }, sub)));
  const startHead = (title, extra) => h("div", { class: "start-head" }, h("h3", { class: "start-h" }, title), extra);
  const moreBtn = (label, icon, after, fn) =>
    h("button", { class: "start-more", type: "button", onclick: fn }, after ? label : h("span", { html: icon }), after ? h("span", { html: icon }) : label);

  function recentEntries() {
    return recent.map((r) => {
      if (r.kind === "app") {
        const a = appById(r.id);
        return a && { art: appTile(a, "md"), title: a.name, sub: timeAgo(r.at), open: a.open };
      }
      const sec = sections[r.section];
      if (!sec) return null;
      const i = sec.items.findIndex((item, n) => itemId(item, n) === r.id);
      if (i === -1) return null;
      const item = sec.items[i];
      return { art: itemArt(item, "md"), title: item.title || "Untitled", sub: timeAgo(r.at), open: () => openItem(r.section, item, i) };
    }).filter(Boolean).slice(0, 6);
  }

  function renderStart() {
    const raw = startInput.value.trim();
    const q = raw.toLowerCase();

    if (q) {
      startBody.replaceChildren(
        startHead("Best matches"),
        h("div", { class: "start-list" },
          APPS.filter((a) => a.name.toLowerCase().includes(q)).map((a) => row(appTile(a, "md"), a.name, "App", a.open)),
          allItems().filter(({ item }) => matches(item, q)).map(({ key, sec, item, i }) =>
            row(itemArt(item, "md"), item.title || "Untitled", sec.title, () => openItem(key, item, i))))
      );
      return;
    }

    if (startView === "all") {
      const entries = [
        ...APPS.map((a) => ({ name: a.name, art: () => appTile(a, "md"), sub: "", open: a.open })),
        ...allItems().map(({ key, sec, item, i }) => ({ name: item.title || "Untitled", art: () => itemArt(item, "md"), sub: sec.title, open: () => openItem(key, item, i) }))
      ].sort((a, b) => a.name.localeCompare(b.name));
      const list = [];
      let letter = "";
      for (const en of entries) {
        const L = en.name.charAt(0).toUpperCase();
        if (L !== letter) { letter = L; list.push(h("div", { class: "all-letter" }, L)); }
        list.push(row(en.art(), en.name, en.sub, en.open));
      }
      startBody.replaceChildren(
        startHead("All apps", moreBtn("Back", ICONS.chevronLeft, false, () => { startView = "home"; renderStart(); })),
        h("div", { class: "start-list" }, list)
      );
      return;
    }

    const recs = recentEntries();
    startBody.replaceChildren(
      startHead("Pinned", moreBtn("All apps", ICONS.chevron, true, () => { startView = "all"; renderStart(); })),
      h("div", { class: "start-grid" }, APPS.map((a) => {
        const b = h("button", { class: "start-app", type: "button", onclick: () => launch(a.open) }, appTile(a, "lg"), h("span", {}, a.name));
        b.addEventListener("contextmenu", (e) => {
          e.preventDefault();
          showMenu(e.clientX, e.clientY, [{ label: "Open", art: appTile(a, "xs"), action: () => launch(a.open) }]);
        });
        return b;
      })),
      startHead("Recommended"),
      recs.length
        ? h("div", { class: "rec-grid" }, recs.map((r) => row(r.art, r.title, r.sub, r.open)))
        : h("p", { class: "start-empty" }, "Apps, games and AI tools you open will show up here.")
    );
  }

  /* Quick settings */

  const qsEl = $("#qs");
  const qsBtn = $("#qs-btn");
  panels.qs = { el: qsEl, button: qsBtn, render: renderQS };
  qsBtn.addEventListener("click", () => togglePanel("qs"));

  function renderQS() {
    const cell = (btn, label) => h("div", { class: "qs-cell" }, btn, h("span", { class: "qs-label" }, label));
    const tile = (key, icon, label) => cell(h("button", {
      class: "qs-tile", type: "button", "data-setting": key, "aria-pressed": String(!!settings[key]), "aria-label": label, html: icon,
      onclick: () => setSetting(key, !settings[key])
    }), label);
    const action = (icon, label, fn) => cell(h("button", { class: "qs-tile", type: "button", "aria-label": label, html: icon, onclick: () => { closePanels(); fn(); } }), label);
    const bright = h("input", {
      type: "range", min: 30, max: 100, value: settings.brightness, "data-setting": "brightness", "aria-label": "Brightness",
      oninput: (e) => setSetting("brightness", +e.currentTarget.value)
    });
    qsEl.replaceChildren(
      h("div", { class: "qs-tiles" },
        tile("nightLight", ICONS.night, "Night light"),
        tile("transparency", ICONS.layers, "Transparency"),
        tile("motion", ICONS.star, "Moving stars"),
        tile("meteors", ICONS.comet, "Shooting stars"),
        tile("clock24", ICONS.clock, "24-hour clock"),
        action(ICONS.lock, "Lock", lock)),
      h("div", { class: "qs-slider" }, h("span", { html: ICONS.sun }), bright),
      h("div", { class: "qs-foot" },
        h("span", { class: "qs-battery" }, battery.known ? h("span", { html: batteryIcon(battery.level, battery.charging) }) : null, batteryText()),
        h("button", { class: "qs-gear", type: "button", title: "All settings", "aria-label": "All settings", html: ICONS.gear, onclick: () => { closePanels(); openSettings(); } }))
    );
  }

  /* Calendar */

  const calEl = $("#cal");
  const clockBtn = $("#clock-btn");
  let calMonth = null;
  panels.cal = { el: calEl, button: clockBtn, render: () => { calMonth = null; renderCal(); } };
  clockBtn.addEventListener("click", () => togglePanel("cal"));

  function renderCal() {
    const now = new Date();
    if (!calMonth) calMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const y = calMonth.getFullYear(), m = calMonth.getMonth();
    const first = new Date(y, m, 1);
    const days = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(y, m, 1 - first.getDay() + i);
      days.push(h("span", { class: `cal-day${d.getMonth() !== m ? " other" : ""}${sameDay(d, now) ? " today" : ""}` }, String(d.getDate())));
    }
    const weekdays = Array.from({ length: 7 }, (_, i) => new Date(2023, 0, 1 + i).toLocaleDateString([], { weekday: "short" }).slice(0, 2));
    const shift = (n) => { calMonth = new Date(y, m + n, 1); renderCal(); };
    calEl.replaceChildren(
      h("div", { class: "cal-top" }, formatDay(now)),
      h("div", { class: "cal-head" },
        h("span", { class: "cal-title" }, calMonth.toLocaleDateString([], { month: "long", year: "numeric" })),
        h("div", { class: "cal-nav" },
          h("button", { type: "button", title: "Previous month", "aria-label": "Previous month", html: ICONS.up, onclick: () => shift(-1) }),
          h("button", { type: "button", title: "Next month", "aria-label": "Next month", html: ICONS.down, onclick: () => shift(1) }))),
      h("div", { class: "cal-grid" }, weekdays.map((wd) => h("span", { class: "cal-wd" }, wd)), days)
    );
  }

  /* ---------- Lock screen ---------- */

  const lockEl = $("#lock");

  function lock() {
    closePanels();
    lockEl.classList.remove("leaving");
    lockEl.hidden = false;
    document.body.classList.add("locked");
    tick();
  }
  function unlock() {
    if (lockEl.hidden || lockEl.classList.contains("leaving")) return;
    lockEl.classList.add("leaving");
    document.body.classList.remove("locked");
    setTimeout(() => {
      lockEl.hidden = true;
      lockEl.classList.remove("leaving");
    }, 450);
  }
  lockEl.addEventListener("click", unlock);
  document.addEventListener("keydown", (e) => {
    if (!lockEl.hidden && !e.repeat) unlock();
  });

  /* ---------- Desktop ---------- */

  const iconsEl = $("#icons");
  const clearSelection = () => iconsEl.querySelectorAll(".selected").forEach((b) => b.classList.remove("selected"));

  for (const a of APPS.filter((app) => app.desktop !== false)) {
    const btn = h("button", { class: "d-icon", type: "button", role: "listitem", "data-app": a.id }, appTile(a, "xl"), h("span", { class: "d-label" }, a.name));
    btn.addEventListener("click", (e) => {
      if (e.ctrlKey || e.metaKey) btn.classList.toggle("selected");
      else { clearSelection(); btn.classList.add("selected"); }
    });
    btn.addEventListener("dblclick", a.open);
    btn.addEventListener("keydown", (e) => { if (e.key === "Enter") a.open(); });
    btn.addEventListener("pointerup", (e) => { if (e.pointerType === "touch") a.open(); });
    iconsEl.append(btn);
  }

  // Drag on empty desktop to draw a selection box.
  desktop.addEventListener("pointerdown", (e) => {
    if (e.target !== desktop && e.target !== iconsEl) return;
    clearSelection();
    if (e.button !== 0 || e.pointerType === "touch") return;
    const area = desktop.getBoundingClientRect();
    const sx = e.clientX - area.left, sy = e.clientY - area.top;
    const box = h("div", { class: "marquee" });
    let shown = false;
    desktop.setPointerCapture(e.pointerId);

    const move = (ev) => {
      const x = clamp(ev.clientX - area.left, 0, area.width), y = clamp(ev.clientY - area.top, 0, area.height);
      const l = Math.min(sx, x), t = Math.min(sy, y), bw = Math.abs(x - sx), bh = Math.abs(y - sy);
      if (!shown) {
        if (bw + bh < 4) return;
        shown = true;
        desktop.append(box);
      }
      Object.assign(box.style, { left: l + "px", top: t + "px", width: bw + "px", height: bh + "px" });
      const sel = { left: l + area.left, top: t + area.top, right: l + bw + area.left, bottom: t + bh + area.top };
      iconsEl.querySelectorAll(".d-icon").forEach((ic) => {
        const r = ic.getBoundingClientRect();
        ic.classList.toggle("selected", r.left < sel.right && r.right > sel.left && r.top < sel.bottom && r.bottom > sel.top);
      });
    };
    const end = () => {
      desktop.removeEventListener("pointermove", move);
      desktop.removeEventListener("pointerup", end);
      desktop.removeEventListener("pointercancel", end);
      box.remove();
    };
    desktop.addEventListener("pointermove", move);
    desktop.addEventListener("pointerup", end);
    desktop.addEventListener("pointercancel", end);
  });

  desktop.addEventListener("contextmenu", (e) => {
    if (e.target.closest(".win")) return;
    e.preventDefault();
    const icon = e.target.closest(".d-icon");
    if (icon) {
      const a = appById(icon.dataset.app);
      clearSelection();
      icon.classList.add("selected");
      showMenu(e.clientX, e.clientY, [{ label: "Open", art: appTile(a, "xs"), action: a.open }]);
      return;
    }
    const size = (value, label) => ({ label, checked: settings.iconSize === value, action: () => setSetting("iconSize", value) });
    showMenu(e.clientX, e.clientY, [
      size("large", "Large icons"),
      size("medium", "Medium icons"),
      size("small", "Small icons"),
      "sep",
      { label: "Refresh", icon: ICONS.reload, action: refreshDesktop },
      "sep",
      { label: "Display settings", icon: ICONS.monitor, action: () => openSettings("system") },
      { label: "Personalize", icon: ICONS.palette, action: () => openSettings("personalization") }
    ]);
  });

  function refreshDesktop() {
    iconsEl.style.visibility = "hidden";
    setTimeout(() => { iconsEl.style.visibility = ""; }, 120);
  }

  /* ---------- Games / AI apps ---------- */

  function openLibrary(key) {
    const app = appById(key);
    remember({ kind: "app", id: key });
    openWindow({ key: app.key, title: sections[key].title, art: (s) => appTile(app, s), body: libraryView(key), width: 880, height: 580 });
  }

  function libraryView(key) {
    const sec = sections[key];
    const search = h("input", { type: "search", placeholder: `Search ${sec.title}`, "aria-label": `Search ${sec.title}`, autocomplete: "off" });
    const grid = h("div", { class: "lib-grid" });
    const count = sec.items.length;

    const render = () => {
      const q = search.value.trim().toLowerCase();
      const list = sec.items.map((item, i) => ({ item, i })).filter(({ item }) => !q || matches(item, q));
      grid.classList.toggle("is-empty", !list.length);
      if (list.length) {
        grid.replaceChildren(...list.map(({ item, i }) =>
          h("button", { class: "lib-card", type: "button", title: item.title, onclick: () => openItem(key, item, i) },
            itemArt(item, "cover"),
            h("span", { class: "lib-name" }, item.title || "Untitled"),
            item.description && h("span", { class: "lib-desc" }, item.description))));
      } else if (count) {
        grid.replaceChildren(h("div", { class: "lib-empty" }, h("strong", {}, "No matches"), h("span", {}, `Nothing in ${sec.title} matches that search.`)));
      } else {
        grid.replaceChildren(h("div", { class: "lib-empty" },
          h("span", { class: "lib-empty-icon" }, appTile(appById(key), "xxl")),
          h("strong", {}, `No ${sec.noun} yet`),
          h("span", { html: `Add ${sec.noun} in <code>library.js</code> and they'll show up here.` })));
      }
    };
    search.addEventListener("input", render);
    render();

    return h("div", { class: "lib" },
      h("header", { class: "lib-head" },
        h("h2", { class: "lib-title" }, sec.title),
        h("span", { class: "lib-count" }, `${count} ${count === 1 ? "item" : "items"}`),
        h("div", { class: "field lib-search" }, h("span", { html: ICONS.search }), search)),
      grid);
  }

  // A game/app may be packed into this file as base64 in a <script type="text/plain">
  // (its id is on item.embed). Open it with srcdoc so it runs same-origin and its
  // saved data stays in this browser. A plain url is loaded as-is.
  function embeddedHtml(item) {
    if (!item || !item.embed) return "";
    if (item._html != null) return item._html;
    const node = document.getElementById(item.embed);
    let html = "";
    if (node) {
      try {
        const bin = atob(String(node.textContent).replace(/\s+/g, ""));
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        html = new TextDecoder().decode(bytes);
      } catch (e) { html = ""; }
    }
    item._html = html;
    return html;
  }

  function openItem(key, item, i) {
    remember({ kind: "item", section: key, id: itemId(item, i) });
    const embedded = embeddedHtml(item);
    const frame = embedded
      ? h("iframe", { class: "app-frame", srcdoc: embedded, title: item.title || "App", allow: "fullscreen; autoplay; gamepad; clipboard-write; microphone", allowfullscreen: true })
      : h("iframe", { class: "app-frame", src: item.url, title: item.title || "App", allow: "fullscreen; autoplay; gamepad; clipboard-write; microphone", allowfullscreen: true });
    openWindow({
      key: `item:${key}:${itemId(item, i)}`,
      title: item.title || "Untitled",
      art: (s) => itemArt(item, s),
      body: frame,
      popout: () => embedded ? { html: embedded } : { url: item.url },
      width: 960,
      height: 620
    });
  }

  /* ---------- Settings ---------- */

  const SETTINGS_PAGES = [
    { id: "system", name: "System", icon: ICONS.monitor, rows: [
      { key: "brightness", label: "Brightness", desc: "Dim the whole screen", icon: ICONS.sun, type: "range", min: 30, max: 100 },
      { key: "nightLight", label: "Night light", desc: "Warmer colors that are easier on your eyes at night", icon: ICONS.night, type: "toggle" },
      { key: "iconSize", label: "Desktop icon size", icon: ICONS.apps, type: "select", options: [["small", "Small"], ["medium", "Medium"], ["large", "Large"]] },
      { key: "motion", label: "Moving stars", desc: "Stars drift and twinkle in the background", icon: ICONS.star, type: "toggle" },
      { key: "meteors", label: "Shooting stars", desc: "Every so often, one streaks across the sky", icon: ICONS.comet, type: "toggle" }
    ] },
    { id: "personalization", name: "Personalization", icon: ICONS.palette, preview: true, rows: [
      { key: "wallpaper", label: "Background", desc: "Pick a wallpaper for your desktop and lock screen", icon: ICONS.image, type: "wallpaper" },
      { key: "accent", label: "Accent color", desc: "Used for highlights, switches and the Start button", icon: ICONS.palette, type: "swatches" },
      { key: "transparency", label: "Transparency effects", desc: "Windows and surfaces appear translucent", icon: ICONS.layers, type: "toggle" }
    ] },
    { id: "taskbar", name: "Taskbar", icon: ICONS.taskbar, rows: [
      { key: "taskbarAlign", label: "Taskbar alignment", icon: ICONS.taskbar, type: "select", options: [["center", "Center"], ["left", "Left"]] },
      { key: "showDate", label: "Show date", desc: "Under the time in the corner of the taskbar", icon: ICONS.clock, type: "toggle" }
    ] },
    { id: "time", name: "Time & language", icon: ICONS.clock, rows: [
      { key: "clock24", label: "24-hour time", desc: "Show 17:30 instead of 5:30 PM", icon: ICONS.clock, type: "toggle" }
    ] },
    { id: "accounts", name: "Accounts", icon: ICONS.user, rows: [
      { key: "userName", label: "Your name", desc: "Shown in Start and Settings", icon: ICONS.user, type: "text" },
      { key: "lockOnStart", label: "Lock screen on startup", desc: "Show the lock screen when the site opens", icon: ICONS.lock, type: "toggle" }
    ] }
  ];

  function openSettings(pageId) {
    const app = appById("settings");
    remember({ kind: "app", id: "settings" });
    const existing = wins.get(app.key);
    if (existing) {
      restore(existing);
      if (pageId) existing.goTo(pageId);
      return;
    }
    const view = settingsView(pageId || "system");
    const w = openWindow({ key: app.key, title: "Settings", art: (s) => appTile(app, s), body: view.el, width: 900, height: 600 });
    w.goTo = view.show;
  }

  function setSetting(key, value) {
    settings[key] = value;
    save("nebula-settings", settings);
    applySettings();
  }

  function applySettings() {
    const body = document.body;
    body.dataset.icons = settings.iconSize;
    body.dataset.taskbar = settings.taskbarAlign;
    body.classList.toggle("glass", !!settings.transparency);
    document.documentElement.style.setProperty("--accent", ACCENTS[settings.accent] || ACCENTS.purple);
    $("#dim").style.opacity = String(((100 - clamp(+settings.brightness || 100, 30, 100)) / 100) * 0.9);
    $("#night").hidden = !settings.nightLight;
    Wallpaper.set({ wallpaper: settings.wallpaper, moving: settings.motion, meteors: settings.meteors });
    document.querySelectorAll(".user-name").forEach((el) => { el.textContent = settings.userName; });
    document.querySelectorAll(".pv-img").forEach((img) => { img.src = Wallpaper.thumbURL(settings.wallpaper, 384, 216); });
    document.querySelectorAll(".sp-bg").forEach((el) => { el.style.backgroundImage = `url(${Wallpaper.thumbURL(settings.wallpaper, 1280, 720)})`; });
    syncControls();
    tick();
  }

  // Keep every on-screen control (Settings, quick settings) showing the current value.
  function syncControls() {
    document.querySelectorAll("[data-setting]").forEach((el) => {
      const v = settings[el.dataset.setting];
      if (el.matches(".qs-tile")) el.setAttribute("aria-pressed", String(!!v));
      else if (el.matches("[role=switch]")) {
        el.setAttribute("aria-checked", String(!!v));
        const label = el.parentElement.querySelector(".toggle-label");
        if (label) label.textContent = v ? "On" : "Off";
      } else if (el.matches("select, input[type=range]")) {
        if (document.activeElement !== el) el.value = v;
      } else if (el.matches("[role=radiogroup]")) {
        el.querySelectorAll("[role=radio]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.value === String(v))));
      } else if (el.matches(".range-val")) {
        el.textContent = v;
      }
    });
  }

  function settingsView(startPage) {
    const nav = h("nav", { class: "set-nav", "aria-label": "Settings" });
    const page = h("div", { class: "set-page" });
    const search = h("input", { type: "search", placeholder: "Find a setting", "aria-label": "Find a setting", autocomplete: "off" });
    let current = startPage;

    function show(id) {
      current = SETTINGS_PAGES.some((p) => p.id === id) ? id : "system";
      search.value = "";
      nav.querySelectorAll(".set-nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === current));
      const p = SETTINGS_PAGES.find((x) => x.id === current);
      page.replaceChildren(...[h("h2", { class: "set-title" }, p.name), p.preview && previewBox(), h("div", { class: "set-group" }, p.rows.map(settingRow))].filter(Boolean));
      page.scrollTop = 0;
    }

    function showResults(q) {
      nav.querySelectorAll(".set-nav-btn").forEach((b) => b.classList.remove("active"));
      const hits = SETTINGS_PAGES.flatMap((p) => p.rows.filter((r) => `${r.label} ${r.desc || ""} ${p.name}`.toLowerCase().includes(q)));
      page.replaceChildren(h("h2", { class: "set-title" }, "Search results"),
        hits.length ? h("div", { class: "set-group" }, hits.map(settingRow)) : h("p", { class: "set-empty" }, "No settings match that search."));
    }

    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      if (q) showResults(q);
      else show(current);
    });

    nav.append(
      h("div", { class: "set-user" }, avatar("lg"),
        h("div", { class: "set-user-text" }, h("div", { class: "set-user-name user-name" }, settings.userName), h("div", { class: "set-user-sub" }, "Local account"))),
      h("div", { class: "field set-search" }, search, h("span", { html: ICONS.search })),
      ...SETTINGS_PAGES.map((p) => h("button", { class: "set-nav-btn", type: "button", "data-page": p.id, onclick: () => show(p.id) }, h("span", { html: p.icon }), p.name)),
      h("button", {
        class: "set-reset", type: "button",
        onclick: () => {
          settings = Object.assign({}, DEFAULTS);
          save("nebula-settings", settings);
          applySettings();
          show(current);
        }
      }, "Reset all settings")
    );

    show(startPage);
    return { el: h("div", { class: "settings" }, nav, page), show };
  }

  function previewBox() {
    return h("div", { class: "pv" },
      h("img", { class: "pv-img", alt: "", src: Wallpaper.thumbURL(settings.wallpaper, 384, 216) }),
      h("div", { class: "pv-win" }, h("div", { class: "pv-bar" })),
      h("div", { class: "pv-taskbar" }, h("span", { class: "pv-dot" }), h("span", { class: "pv-dot" }), h("span", { class: "pv-dot" })));
  }

  // One setting: icon, label and description on the left, its control on the right.
  function settingRow(row) {
    const value = settings[row.key];
    let control;

    if (row.type === "toggle") {
      control = h("div", { class: "toggle-wrap" },
        h("span", { class: "toggle-label" }, value ? "On" : "Off"),
        h("button", {
          class: "toggle", type: "button", role: "switch", "data-setting": row.key, "aria-checked": String(!!value), "aria-label": row.label,
          onclick: () => setSetting(row.key, !settings[row.key])
        }, h("span", { class: "toggle-knob" })));
    } else if (row.type === "select") {
      const sel = h("select", { class: "select", "data-setting": row.key, "aria-label": row.label, onchange: (e) => setSetting(row.key, e.currentTarget.value) },
        row.options.map(([v, text]) => h("option", { value: v }, text)));
      sel.value = value;
      control = sel;
    } else if (row.type === "range") {
      control = h("div", { class: "range-wrap" },
        h("input", { type: "range", min: row.min, max: row.max, value, "data-setting": row.key, "aria-label": row.label, oninput: (e) => setSetting(row.key, +e.currentTarget.value) }),
        h("span", { class: "range-val", "data-setting": row.key }, String(value)));
    } else if (row.type === "text") {
      const input = h("input", { type: "text", value, maxlength: 32, "aria-label": row.label, spellcheck: "false", autocomplete: "off" });
      input.addEventListener("change", () => setSetting(row.key, input.value.trim() || DEFAULTS[row.key]));
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
      control = h("div", { class: "field text-field" }, input);
    } else if (row.type === "swatches") {
      control = h("div", { class: "swatches", role: "radiogroup", "aria-label": row.label, "data-setting": row.key },
        Object.entries(ACCENTS).map(([name, hex]) => {
          const nice = name.charAt(0).toUpperCase() + name.slice(1);
          return h("button", {
            class: "swatch", type: "button", role: "radio", title: nice, "aria-label": nice, "data-value": name,
            "aria-checked": String(value === name), style: `--c: ${hex}`, onclick: () => setSetting(row.key, name)
          });
        }));
    } else if (row.type === "wallpaper") {
      control = h("div", { class: "wallpapers", role: "radiogroup", "aria-label": row.label, "data-setting": row.key },
        WALLPAPERS.map(([id, text]) => h("button", {
          class: "wp", type: "button", role: "radio", "data-value": id, "aria-checked": String(value === id), onclick: () => setSetting(row.key, id)
        }, h("img", { class: "wp-thumb", alt: "", src: Wallpaper.thumbURL(id, 176, 110) }), h("span", { class: "wp-label" }, text))));
    }

    return h("div", { class: `set-row${row.type === "wallpaper" ? " wide" : ""}` },
      h("span", { class: "set-row-ico", html: row.icon }),
      h("div", { class: "set-text" }, h("div", { class: "set-label" }, row.label), row.desc && h("div", { class: "set-desc" }, row.desc)),
      h("div", { class: "set-control" }, control));
  }

  /* ---------- AI app ---------- */

  function openAI() {
    const app = appById("ai");
    remember({ kind: "app", id: "ai" });
    const existing = wins.get(app.key);
    if (existing) { restore(existing); return; }
    openWindow({ key: app.key, title: "AI", art: (s) => appTile(app, s), body: window.NebulaAI.createView(), width: 940, height: 660 });
  }

  /* ---------- Start up ---------- */

  document.title = siteName;
  renderTray();
  renderTaskbar();
  applySettings();
  if (settings.lockOnStart) lock();
  // Skip fade-ins on first paint so the desktop doesn't flash before the lock screen.
  requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.remove("booting")));
})();
