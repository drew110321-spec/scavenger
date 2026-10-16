// The AI app: several built-in assistants plus your own custom ones, all powered
// by Google Gemini. Each visitor pastes their own free API key (Settings), kept
// only in their browser. Nothing here is sent anywhere except Google's API.
window.NebulaAI = (function () {
  "use strict";

  const STORE = "nebula-ai";       // non-secret settings (model, customs)
  const KEY_STORE = "nebula-ai-key"; // the API key, kept on its own and never shown
  // Fallback list used until the real one is fetched from the key. Newest first.
  const FALLBACK_MODELS = [
    ["gemini-3.8-flash", "Gemini 3.8 Flash — fast"],
    ["gemini-3.7-flash", "Gemini 3.7 Flash"],
    ["gemini-4-argon", "Gemini 4 Argon — most capable"],
    ["gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite — fastest"]
  ];
  const DEFAULTS = { model: "gemini-3.8-flash", customs: [], persist: true };

  const BUILTINS = [
    { id: "orbit", name: "Orbit", tagline: "All-round assistant", emoji: "🪐", accent: "#a487f6",
      system: "You are Orbit, a friendly, upbeat general-purpose assistant living inside a games-and-apps desktop. Give clear, genuinely helpful, concise answers in plain language. Use markdown (headings, lists, code blocks) when it makes the answer easier to read." },
    { id: "tutor", name: "Tutor", tagline: "Homework & explanations", emoji: "📚", accent: "#55c9b8",
      system: "You are Tutor, a patient, encouraging teacher. Explain things step by step in simple language. For maths, show every step and the final answer clearly. Give a short example, and finish by checking the learner understands. Never give just an answer with no reasoning." },
    { id: "coder", name: "Coder", tagline: "Code help & debugging", emoji: "💻", accent: "#71aaf5",
      system: "You are Coder, an expert programming assistant. Give correct, working code in fenced code blocks tagged with the language, followed by a short, clear explanation. Point out bugs, edge cases and cleaner approaches. Be precise." },
    { id: "writer", name: "Writer", tagline: "Essays, stories & rewrites", emoji: "✍️", accent: "#ee84b9",
      system: "You are Writer, a skilled, versatile writing partner. Help draft, improve and rewrite essays, stories, messages and scripts. Match the tone and length the user asks for, keep the writing natural and human, and offer a quick note on what you changed when you edit." },
    { id: "spark", name: "Spark", tagline: "Brainstorm & ideas", emoji: "💡", accent: "#f5b14b",
      system: "You are Spark, an energetic brainstorming partner. Generate lots of creative, concrete ideas, grouped into clear lists. Build on the user's direction, mix safe and bold options, and suggest a sensible next step." },
    { id: "guide", name: "Game Guide", tagline: "Tips, tricks & walkthroughs", emoji: "🎮", accent: "#ff6a4a",
      system: "You are Game Guide, a knowledgeable, friendly gaming helper. Give practical tips, strategies, controls and walkthrough help for video games. Keep spoilers light unless asked, and format steps as short numbered lists." }
  ];

  /* ---------- Storage ---------- */
  let cfg, rawBlob = {};
  try { rawBlob = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (_) { rawBlob = {}; }
  cfg = Object.assign({}, DEFAULTS, rawBlob);
  if (!Array.isArray(cfg.customs)) cfg.customs = [];

  // A key set in library.js (aiKey) is the shared default on every device. It may
  // be pasted raw, or lightly obfuscated as base64 so it isn't plain text in the file.
  function decodeBuiltin(v) {
    v = String(v || "").trim();
    if (!v) return v;
    // Raw keys: classic "AIza..." and newer "AQ." Gemini keys are used as-is.
    if (v.startsWith("AIza") || v.startsWith("AQ.")) return v;
    // Only treat as base64 if it is pure base64 and decodes to a real key.
    if (/^[A-Za-z0-9+/]+={0,2}$/.test(v) && v.length % 4 === 0) {
      try { const d = atob(v); if (d.startsWith("AIza") || d.startsWith("AQ.")) return d; } catch (_) { /* not base64 */ }
    }
    return v;
  }
  const builtinKey = decodeBuiltin((window.LIBRARY || {}).aiKey);

  // A per-device key (localStorage = remembered, sessionStorage = this session only)
  // overrides the shared one. Neither is ever rendered to the page.
  let deviceKey = "";
  try { deviceKey = localStorage.getItem(KEY_STORE) || sessionStorage.getItem(KEY_STORE) || ""; } catch (_) { /* blocked */ }
  if (!deviceKey && rawBlob.key) { deviceKey = rawBlob.key; } // migrate an older saved key
  delete cfg.key;

  let apiKey = deviceKey || builtinKey;        // the key actually used for requests
  const usingBuiltin = () => !deviceKey && !!builtinKey;

  function saveCfg() { try { localStorage.setItem(STORE, JSON.stringify({ model: cfg.model, customs: cfg.customs, persist: cfg.persist })); } catch (_) { /* not remembered */ } }
  function saveKey(key, persist) {
    deviceKey = key; apiKey = deviceKey || builtinKey; cfg.persist = persist; saveCfg();
    try {
      localStorage.removeItem(KEY_STORE); sessionStorage.removeItem(KEY_STORE);
      if (key) (persist ? localStorage : sessionStorage).setItem(KEY_STORE, key);
    } catch (_) { /* applied in memory only */ }
  }
  function clearKey() {
    deviceKey = ""; apiKey = builtinKey;
    try { localStorage.removeItem(KEY_STORE); sessionStorage.removeItem(KEY_STORE); } catch (_) { /* ignore */ }
  }
  saveCfg(); // drop any migrated key out of the settings blob

  let modelList = FALLBACK_MODELS.slice();
  // Ask Gemini which models this key can actually use, so the list is always current.
  async function fetchModels() {
    if (!apiKey) return;
    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000&key=${encodeURIComponent(apiKey)}`);
      if (!res.ok) return;
      const j = await res.json();
      const list = (j.models || [])
        .filter((m) => (m.supportedGenerationMethods || []).includes("generateContent") && /\/gemini/i.test(m.name))
        .map((m) => { const id = m.name.replace(/^models\//, ""); return [id, m.displayName || id]; });
      list.sort((a, b) => b[0].localeCompare(a[0], undefined, { numeric: true, sensitivity: "base" }));
      if (list.length) {
        modelList = list;
        if (!modelList.some(([id]) => id === cfg.model)) { cfg.model = modelList[0][0]; saveCfg(); }
      }
    } catch (_) { /* keep fallback list */ }
  }

  // Conversations are kept in memory for the life of the page, keyed by assistant id.
  const convos = {};
  const assistants = () => BUILTINS.concat(cfg.customs);

  /* ---------- Tiny DOM helper ---------- */
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

  const ICON = {
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12l16-8-6 16-3-6-7-2z"/></svg>',
    clip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5l-8.5 8.5a5 5 0 0 1-7-7l9-9a3.3 3.3 0 0 1 4.7 4.7l-9 9a1.6 1.6 0 0 1-2.3-2.3l8.3-8.3"/></svg>',
    gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 4 13.6H4a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 5 7.5l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 10 4.6V4a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.5 1h.1a2 2 0 0 1 0 4H21a1.6 1.6 0 0 0-1.5 1z"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/></svg>',
    back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>',
    edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
    fresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/><circle cx="12" cy="12" r="9"/></svg>'
  };

  /* ---------- Markdown (escaped, then safe formatting) ---------- */
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  function inline(s) {
    return s
      .replace(/`([^`]+)`/g, (m, c) => `<code>${c}</code>`)
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
      .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<i>$2</i>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }
  function markdown(src) {
    const fences = [];
    src = String(src).replace(/```(\w*)\n?([\s\S]*?)```/g, (m, lang, code) => {
      fences.push({ lang, code: code.replace(/\n$/, "") });
      return `\u0001${fences.length - 1}\u0001`;
    });
    const lines = src.split("\n");
    let html = "", list = null;
    const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
    for (const raw of lines) {
      const fence = raw.match(/^\u0001(\d+)\u0001$/);
      if (fence) {
        closeList();
        const f = fences[+fence[1]];
        html += `<div class="ai2-code"><button class="ai2-copy" type="button">Copy</button>${f.lang ? `<span class="ai2-lang">${esc(f.lang)}</span>` : ""}<pre><code>${esc(f.code)}</code></pre></div>`;
        continue;
      }
      const line = raw.replace(/\s+$/, "");
      if (!line.trim()) { closeList(); continue; }
      let m;
      if ((m = line.match(/^(#{1,4})\s+(.*)$/))) { closeList(); const lv = Math.min(m[1].length + 2, 6); html += `<h${lv}>${inline(esc(m[2]))}</h${lv}>`; continue; }
      if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; } html += `<li>${inline(esc(m[1]))}</li>`; continue; }
      if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) { if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; } html += `<li>${inline(esc(m[1]))}</li>`; continue; }
      closeList();
      html += `<p>${inline(esc(line))}</p>`;
    }
    closeList();
    return html;
  }

  /* ---------- Gemini API (streaming) ---------- */
  async function streamGemini(contents, system, onText, signal) {
    const model = cfg.model || DEFAULTS.model;
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:streamGenerateContent?alt=sse&key=${encodeURIComponent(apiKey)}`;
    const body = { contents, generationConfig: { temperature: 0.9, maxOutputTokens: 2048 } };
    if (system) body.systemInstruction = { parts: [{ text: system }] };

    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
    if (!res.ok) {
      let msg = `Request failed (${res.status})`;
      try { const j = await res.json(); if (j.error && j.error.message) msg = j.error.message; } catch (_) { /* keep status */ }
      if (res.status === 400 && /api key/i.test(msg)) msg = "That API key was rejected. Check it in Settings.";
      throw new Error(msg);
    }

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "", full = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (!data || data === "[DONE]") continue;
        try {
          const j = JSON.parse(data);
          const cand = j.candidates && j.candidates[0];
          const parts = cand && cand.content && cand.content.parts;
          if (parts) for (const p of parts) if (p.text) { full += p.text; onText(full); }
          if (cand && cand.finishReason === "SAFETY") throw new Error("The response was blocked by Gemini's safety filter. Try rewording.");
        } catch (e) { if (e.message && e.message.indexOf("safety") >= 0) throw e; /* else ignore partial parse */ }
      }
    }
    return full;
  }

  /* ---------- The view ---------- */
  function createView() {
    let current = assistants()[0];
    let pending = [];       // images staged for the next message: {mime, data, name}
    let busy = false;
    let controller = null;

    const sideList = h("div", { class: "ai2-list" });
    const side = h("aside", { class: "ai2-side" },
      h("div", { class: "ai2-side-h" }, "Assistants"),
      sideList,
      h("button", { class: "ai2-new-ast", type: "button", onclick: () => openEditor() }, h("span", { html: ICON.plus }), "New assistant"),
      h("button", { class: "ai2-side-settings", type: "button", onclick: () => showSettings() }, h("span", { html: ICON.gear }), "API key & model"));

    const headBadge = h("span", { class: "ai2-badge" });
    const headName = h("b", {});
    const headTag = h("span", { class: "ai2-sub" });
    const fillModel = (sel) => {
      const opts = modelList.slice();
      if (!opts.some(([id]) => id === cfg.model)) opts.unshift([cfg.model, cfg.model + " (custom)"]);
      sel.replaceChildren(...opts.map(([v, label]) => h("option", { value: v }, label)));
      sel.value = cfg.model;
    };
    const modelSel = h("select", { class: "ai2-model", "aria-label": "Model", onchange: (e) => { cfg.model = e.currentTarget.value; saveCfg(); } });
    fillModel(modelSel);
    const head = h("header", { class: "ai2-head" },
      headBadge,
      h("div", { class: "ai2-head-txt" }, headName, headTag),
      modelSel,
      h("button", { class: "ai2-ghost", type: "button", title: "New chat", "aria-label": "New chat", html: ICON.fresh, onclick: newChat }),
      h("button", { class: "ai2-ghost", type: "button", title: "Settings", "aria-label": "Settings", html: ICON.gear, onclick: () => showSettings() }));

    const log = h("div", { class: "ai2-log" });
    const clips = h("div", { class: "ai2-clips" });
    const input = h("textarea", { class: "ai2-input", rows: 1, placeholder: "Message your assistant…", "aria-label": "Message" });
    const fileInput = h("input", { type: "file", accept: "image/*", multiple: true, hidden: true, onchange: onFiles });
    const sendBtn = h("button", { class: "ai2-send", type: "button", title: "Send", "aria-label": "Send", html: ICON.send, onclick: send });
    const composer = h("div", { class: "ai2-composer" }, clips,
      h("div", { class: "ai2-crow" },
        h("button", { class: "ai2-attach", type: "button", title: "Attach image", "aria-label": "Attach image", html: ICON.clip, onclick: () => fileInput.click() }),
        fileInput, input, sendBtn));
    const main = h("div", { class: "ai2-main" }, head, log, composer);

    input.addEventListener("input", autoGrow);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
    log.addEventListener("click", (e) => {
      const c = e.target.closest(".ai2-copy");
      if (!c) return;
      const code = c.parentElement.querySelector("code");
      if (code) { navigator.clipboard && navigator.clipboard.writeText(code.textContent); c.textContent = "Copied"; setTimeout(() => (c.textContent = "Copy"), 1200); }
    });

    function autoGrow() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 150) + "px"; }

    /* Assistant list + switching */
    function renderList() {
      sideList.replaceChildren(...assistants().map((a) => {
        const btn = h("button", { class: `ai2-ast${a.id === current.id ? " on" : ""}`, type: "button", onclick: () => select(a) },
          h("span", { class: "ai2-badge sm", style: `--c:${a.accent}` }, a.emoji),
          h("span", { class: "ai2-ast-txt" }, h("b", {}, a.name), h("span", {}, a.tagline)));
        if (a.custom) {
          btn.append(h("span", { class: "ai2-ast-edit", title: "Edit", role: "button", "aria-label": "Edit assistant", html: ICON.edit,
            onclick: (e) => { e.stopPropagation(); openEditor(a); } }));
        }
        return btn;
      }));
    }

    function select(a) {
      current = a;
      headBadge.style.setProperty("--c", a.accent);
      headBadge.textContent = a.emoji;
      headName.textContent = a.name;
      headTag.textContent = a.tagline;
      renderList();
      renderLog();
    }

    function newChat() { convos[current.id] = []; renderLog(); }

    /* Messages */
    function renderLog() {
      if (!apiKey) { renderSetup(); return; }
      const msgs = convos[current.id] || [];
      if (!msgs.length) {
        log.replaceChildren(h("div", { class: "ai2-welcome" },
          h("span", { class: "ai2-badge lg", style: `--c:${current.accent}` }, current.emoji),
          h("h2", {}, current.name),
          h("p", {}, current.tagline),
          h("p", { class: "ai2-welcome-sub" }, "Ask anything to get started.")));
        return;
      }
      log.replaceChildren(...msgs.map(msgNode));
      scrollDown();
    }

    function msgNode(m) {
      if (m.role === "you") {
        const node = h("div", { class: "ai2-msg you" });
        if (m.images && m.images.length) {
          node.append(h("div", { class: "ai2-shots" }, m.images.map((im) => h("img", { src: `data:${im.mime};base64,${im.data}`, alt: im.name || "image" }))));
        }
        if (m.text) node.append(h("div", { class: "ai2-text" }, m.text));
        return node;
      }
      if (m.role === "error") return h("div", { class: "ai2-msg err" }, m.text);
      const body = h("div", { class: "ai2-body" });
      if (m.text) body.innerHTML = markdown(m.text);
      else body.append(h("span", { class: "ai2-typing" }, h("i"), h("i"), h("i")));
      m._body = body;
      return h("div", { class: "ai2-msg ai" }, h("span", { class: "ai2-badge sm", style: `--c:${current.accent}` }, current.emoji), body);
    }

    function scrollDown() { log.scrollTop = log.scrollHeight; }

    async function send() {
      const text = input.value.trim();
      if (busy || (!text && !pending.length)) return;
      if (!apiKey) { showSettings(); return; }
      const msgs = convos[current.id] || (convos[current.id] = []);
      msgs.push({ role: "you", text, images: pending.slice() });
      input.value = ""; pending = []; renderClips(); autoGrow();
      const aiMsg = { role: "ai", text: "" };
      msgs.push(aiMsg);
      renderLog();
      busy = true; sendBtn.disabled = true;

      const contents = msgs.slice(0, -1).map((m) => ({
        role: m.role === "you" ? "user" : "model",
        parts: [].concat(
          (m.images || []).map((im) => ({ inlineData: { mimeType: im.mime, data: im.data } })),
          m.text ? [{ text: m.text }] : [])
      }));

      controller = new AbortController();
      try {
        await streamGemini(contents, current.system, (full) => {
          aiMsg.text = full;
          if (aiMsg._body) { aiMsg._body.innerHTML = markdown(full); scrollDown(); }
        }, controller.signal);
        if (!aiMsg.text) { aiMsg.text = "_(No response — try again.)_"; if (aiMsg._body) aiMsg._body.innerHTML = markdown(aiMsg.text); }
      } catch (e) {
        aiMsg.role = "error";
        aiMsg.text = (e && e.message) || "Something went wrong reaching Gemini.";
        renderLog();
      } finally {
        busy = false; sendBtn.disabled = false; controller = null;
      }
    }

    /* Image attachments */
    function onFiles(e) {
      const files = Array.from(e.target.files || []);
      e.target.value = "";
      for (const f of files) {
        if (pending.length >= 4) break;
        if (!f.type.startsWith("image/")) continue;
        const reader = new FileReader();
        reader.onload = () => {
          const url = reader.result;
          const comma = url.indexOf(",");
          pending.push({ mime: f.type, data: url.slice(comma + 1), name: f.name, url });
          renderClips();
        };
        reader.readAsDataURL(f);
      }
    }
    function renderClips() {
      clips.replaceChildren(...pending.map((im, i) =>
        h("div", { class: "ai2-clip" },
          h("img", { src: im.url, alt: im.name }),
          h("button", { type: "button", title: "Remove", "aria-label": "Remove", onclick: () => { pending.splice(i, 1); renderClips(); } }, "×"))));
    }

    /* Settings panel. The key is shown only while you're entering a new one. */
    const LOCKF = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5zm-3 8V7a3 3 0 0 1 6 0v3H9z"/></svg>';

    function showSettings(replacing) {
      const showInput = replacing || !apiKey;
      const body = h("div", { class: "ai2-set-body" });

      body.append(h("label", { class: "ai2-label" }, "Gemini API key"));
      if (showInput) {
        const keyInput = h("input", { class: "ai2-field", type: "password", placeholder: "Paste your Gemini API key", autocomplete: "off", spellcheck: "false" });
        const persist = h("input", { type: "checkbox" });
        persist.checked = cfg.persist !== false;
        body.append(
          keyInput,
          h("label", { class: "ai2-check" }, persist, h("span", {}, "Remember this key on this device")),
          h("p", { class: "ai2-note" }, "Leave this unticked to keep the key only until the browser closes — best on a shared computer. Get a free key at ",
            h("a", { href: "https://aistudio.google.com/apikey", target: "_blank", rel: "noopener" }, "aistudio.google.com/apikey"),
            ". It is stored only in this browser and is never shown again."),
          h("div", { class: "ai2-set-actions" },
            h("button", { class: "ai2-primary", type: "button", onclick: () => {
              const k = keyInput.value.trim();
              if (!k) { keyInput.focus(); return; }
              saveKey(k, persist.checked);
              renderLog();
              fetchModels().then(() => fillModel(modelSel));
            } }, "Save key"),
            apiKey && h("button", { class: "ai2-ghost-btn", type: "button", onclick: () => showSettings(false) }, "Cancel")));
        setTimeout(() => keyInput.focus(), 0);
      } else if (usingBuiltin()) {
        body.append(
          h("div", { class: "ai2-keystatus" },
            h("span", { class: "ai2-lock", html: LOCKF }),
            h("span", {}, "Using the shared key built into the site — it works on every device and stays hidden.")),
          h("div", { class: "ai2-set-actions" },
            h("button", { class: "ai2-ghost-btn", type: "button", onclick: () => showSettings(true) }, "Use a different key here")));
      } else {
        let remembered = false;
        try { remembered = localStorage.getItem(KEY_STORE) != null; } catch (_) { /* ignore */ }
        body.append(
          h("div", { class: "ai2-keystatus" },
            h("span", { class: "ai2-lock", html: LOCKF }),
            h("span", {}, remembered ? "Using a key saved on this device, kept hidden." : "Using a key set for this session only, kept hidden.")),
          h("div", { class: "ai2-set-actions" },
            h("button", { class: "ai2-ghost-btn", type: "button", onclick: () => showSettings(true) }, "Replace key"),
            h("button", { class: "ai2-danger", type: "button", onclick: () => { clearKey(); showSettings(false); } }, builtinKey ? "Use the shared key" : "Remove key")));
      }

      // Model picker — list comes from the key, with a custom option and a refresh.
      const modelPick = h("select", { class: "ai2-field", onchange: (e) => {
        if (e.currentTarget.value === "__custom__") { customWrap.hidden = false; customIn.focus(); modelPick.value = cfg.model; return; }
        cfg.model = e.currentTarget.value; saveCfg(); fillModel(modelSel); customWrap.hidden = true;
      } });
      const buildPick = () => {
        const opts = modelList.slice();
        if (!opts.some(([id]) => id === cfg.model)) opts.unshift([cfg.model, cfg.model + " (custom)"]);
        modelPick.replaceChildren(...opts.map(([v, l]) => h("option", { value: v }, l)), h("option", { value: "__custom__" }, "Other model…"));
        modelPick.value = cfg.model;
      };
      const customIn = h("input", { class: "ai2-field", type: "text", placeholder: "e.g. gemini-4-argon", spellcheck: "false", autocomplete: "off" });
      const customWrap = h("div", { class: "ai2-custom", hidden: true }, customIn,
        h("button", { class: "ai2-ghost-btn", type: "button", onclick: () => {
          const v = customIn.value.trim(); if (!v) return;
          cfg.model = v; saveCfg(); buildPick(); fillModel(modelSel); customWrap.hidden = true;
        } }, "Use"));
      buildPick();
      const refresh = h("button", { class: "ai2-link", type: "button", onclick: () => {
        if (!apiKey) { showSettings(true); return; }
        refresh.textContent = "Refreshing…";
        fetchModels().then(() => { buildPick(); fillModel(modelSel); refresh.textContent = "Refresh list"; });
      } }, "Refresh list");

      body.append(
        h("div", { class: "ai2-label-row" }, h("label", { class: "ai2-label" }, "Model"), refresh),
        modelPick, customWrap,
        h("p", { class: "ai2-note" }, "The list comes from your key, so it stays current. ", h("b", {}, "Gemini 3.8 Flash"), " is a good free pick; ", h("b", {}, "Gemini 4 Argon"), " is the most capable."));

      log.replaceChildren(h("div", { class: "ai2-settings" },
        h("div", { class: "ai2-set-head" },
          h("button", { class: "ai2-ghost", type: "button", title: "Back", "aria-label": "Back", html: ICON.back, onclick: () => renderLog() }),
          h("h2", {}, "AI settings")),
        body));
    }

    function renderSetup() {
      log.replaceChildren(h("div", { class: "ai2-setup" },
        h("span", { class: "ai2-badge lg", style: `--c:${current.accent}` }, current.emoji),
        h("h2", {}, "Connect Gemini to start"),
        h("p", {}, "The assistants run on Google Gemini, which has a free tier. Add a key once and every assistant works."),
        h("ol", { class: "ai2-steps" },
          h("li", {}, "Open ", h("a", { href: "https://aistudio.google.com/apikey", target: "_blank", rel: "noopener" }, "aistudio.google.com/apikey"), " and sign in with a Google account."),
          h("li", {}, "Click ", h("b", {}, "Create API key"), " and copy it."),
          h("li", {}, "Paste it below.")),
        h("button", { class: "ai2-primary", type: "button", onclick: () => showSettings() }, "Add API key")));
    }

    /* Custom assistant editor */
    function openEditor(existing) {
      const nameI = h("input", { class: "ai2-field", type: "text", maxlength: 24, value: existing ? existing.name : "", placeholder: "e.g. Study Buddy" });
      const emojiI = h("input", { class: "ai2-field ai2-emoji", type: "text", maxlength: 2, value: existing ? existing.emoji : "✨", "aria-label": "Emoji" });
      const tagI = h("input", { class: "ai2-field", type: "text", maxlength: 40, value: existing ? existing.tagline : "", placeholder: "Short description" });
      const sysI = h("textarea", { class: "ai2-field ai2-area", rows: 5, placeholder: "How should it behave? e.g. You are a calm study coach who…" }, existing ? existing.system : "");
      const colors = ["#a487f6", "#55c9b8", "#71aaf5", "#ee84b9", "#f5b14b", "#ff6a4a", "#7ee081", "#d0d4dc"];
      let accent = existing ? existing.accent : colors[0];
      const swatches = h("div", { class: "ai2-swatches" }, colors.map((c) =>
        h("button", { type: "button", class: `ai2-swatch${c === accent ? " on" : ""}`, style: `--c:${c}`, "aria-label": "Color", onclick: (e) => {
          accent = c; swatches.querySelectorAll(".ai2-swatch").forEach((b) => b.classList.remove("on")); e.currentTarget.classList.add("on");
        } })));
      const err = h("p", { class: "ai2-err-text" });

      const save = () => {
        const name = nameI.value.trim();
        const system = sysI.value.trim();
        if (!name) { err.textContent = "Give it a name."; return; }
        if (!system) { err.textContent = "Add some instructions for how it should behave."; return; }
        const data = { name, emoji: emojiI.value.trim() || "✨", tagline: tagI.value.trim() || "Custom assistant", system, accent, custom: true };
        if (existing) { Object.assign(existing, data); if (current.id === existing.id) select(existing); }
        else { data.id = "c" + Date.now().toString(36); cfg.customs.push(data); select(data); }
        saveCfg(); renderList(); renderLog();
      };

      const panel = h("div", { class: "ai2-settings" },
        h("div", { class: "ai2-set-head" },
          h("button", { class: "ai2-ghost", type: "button", title: "Back", "aria-label": "Back", html: ICON.back, onclick: () => renderLog() }),
          h("h2", {}, existing ? "Edit assistant" : "New assistant")),
        h("div", { class: "ai2-set-body" },
          h("div", { class: "ai2-row2" },
            h("div", {}, h("label", { class: "ai2-label" }, "Icon"), emojiI),
            h("div", { class: "ai2-grow" }, h("label", { class: "ai2-label" }, "Name"), nameI)),
          h("label", { class: "ai2-label" }, "Description"), tagI,
          h("label", { class: "ai2-label" }, "Color"), swatches,
          h("label", { class: "ai2-label" }, "Instructions (its personality & job)"), sysI,
          err,
          h("div", { class: "ai2-set-actions" },
            existing && h("button", { class: "ai2-danger", type: "button", onclick: () => {
              cfg.customs = cfg.customs.filter((c) => c.id !== existing.id);
              saveCfg();
              if (current.id === existing.id) current = assistants()[0];
              select(current); renderList();
            } }, "Delete"),
            h("button", { class: "ai2-primary", type: "button", onclick: save }, existing ? "Save changes" : "Create"))));
      log.replaceChildren(panel);
      nameI.focus();
    }

    renderList();
    select(current);
    if (apiKey) fetchModels().then(() => fillModel(modelSel));
    return h("div", { class: "ai2" }, side, main);
  }

  return { createView };
})();
