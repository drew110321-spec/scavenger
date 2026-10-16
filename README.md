# Nebula

A Windows 11-style desktop in the browser, with a black and purple space theme. It holds games and a set of AI assistants.
The Games app is yours to fill; the AI app has built-in assistants ready to go.

---

## 🔁 How to update everyone (the important part)

`Nebula.html` is one file you hand out. It pulls its code from this branch on every open, so **you fix things here once and everyone gets it next time they open their file — no re-sending.**

**Update source (baked into the file):**
```
https://raw.githubusercontent.com/drew110321-spec/scavenger/nebula/
```

**To push a change to everyone:**
1. Edit a source file on the **`nebula`** branch of this repo (`library.js`, `app.js`, `ai.js`, etc.) and commit it.
2. That's it — every copy of `Nebula.html` picks it up on next open.

**Re-run `node build.js`** only to refresh the *offline* snapshot (what people see with no connection), or if you change the wrapper/boot logic itself. Everyday content changes don't need it.

**If the Orbit game's AI stops working** (its keys aren't yours and can't be rotated), just edit `orbit/index.html` here and push — the fix reaches everyone the same way.

> Obfuscation on the keys is a speed bump, not real secrecy. Anything in a public repo is effectively public.

---

## Open it

Double-click `index.html`. There's no install or build step.

## What's in the shell

- **Lock screen** with the time and date. Click or press a key to unlock. You can turn it off in Settings › Accounts.
- **Space wallpapers** painted by code (nebula clouds, a lit planet, stars with halos), with twinkling and shooting stars on top.
- **Desktop** with app icons. Double-click to open, tap on phones, drag on empty space to select, right-click for icon size and settings.
- **Windows** you can drag, resize, minimize, maximize, and snap: drag to the top edge to fill the screen, or to the left or right edge for half.
  Right-click a title bar for the window menu.
- **Taskbar** with Start, pinned and open apps, quick settings (Wi-Fi and battery status) and a clock.
  - **Start**: search, pinned apps, All apps, recently opened ("Recommended"), your name, and Lock or Restart.
  - **Quick settings**: night light, transparency, moving and shooting stars, 24-hour clock, lock, and brightness.
  - **Clock**: click it for a calendar.
- **Games** app that lists the games you've added, with search.
- **AI** app with built-in assistants (Orbit, Tutor, Coder, Writer, Spark, Game Guide) plus any you create yourself. See "The AI app" below.
- **Settings** with these pages:
  - System: brightness, night light, icon size, star effects
  - Personalization: wallpaper, accent color, transparency
  - Taskbar: alignment, date
  - Time & language: 24-hour time
  - Accounts: your name, lock screen on startup

  Choices are saved in each visitor's own browser. "Reset all settings" puts everything back.

## Add a game

1. Put its files in a folder inside this one, for example `games/snake/`.
   (Skip this if it's already hosted at a web link, like a GitHub Pages page.)
2. Open `library.js` and add an entry to `games`:

```js
games: [
  { title: "Snake", url: "games/snake/index.html", image: "icons/snake.svg", description: "Classic snake" }
],
```

Only `title` and `url` are required. Save and refresh. It shows up in the Games app, in Start search and All apps, and opens in its own window.

A game has to be **playable at the url** — a page in this folder or a full web link. A bare GitHub repo link won't work; it needs a live page.
Some sites refuse to load inside another site and show a blank page — that's their choice and can't be overridden here; use the open-in-new-tab button in the title bar.

## The AI app

The AI app runs on Google Gemini, which has a free tier. There are two ways to give it a key.

**Option A — one shared key for every device (no typing).** Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and paste it into `aiKey` in `library.js`:

```js
aiKey: "AIza...your key...",
```

Every device that opens the site then uses it automatically — nothing to set up per device. This is what "the key stays between devices" means: the key travels with the site's files.
Trade-off: anyone who opens the page source can read it, so use a free key you can replace, and keep the site's files private if you can (a public GitHub repo may get the key auto-disabled by Google's scanners — a private repo or Netlify Drop avoids that). You can paste the key base64-encoded instead of raw to keep it out of plain text.

**Option B — each person adds their own key.** Leave `aiKey` as `""`. Then each person opens the AI app, clicks **Add API key**, and pastes their own. Most private, but it's per device.

Either way, a person can still set their own key on their device (**Settings › Use a different key here**), which overrides the shared one just for them.

Then every assistant works — ask questions, get code, attach images, and so on.
You can make your own assistants with **New assistant**, each with its own personality and color.

**The key is kept private:** once saved it's hidden and never shown again — Settings only offers **Replace key** or **Remove key**. When you add it, you choose:

- **Remember this key on this device** (ticked): stays until you remove it.
- Unticked: kept only until the browser closes — best on a shared Chromebook.

**Models:** it defaults to **Gemini 3.8 Flash** (fast, free tier). The model list is pulled from your key so it stays current; pick **Gemini 4 Argon** for the most capable, or type any model name. Use **Refresh list** after Google adds new ones.

Heads-up: on a static site the key still lives in the browser, so someone who really knows where to look could find it in browser storage. Don't use a key tied to anything important, give each person their own, and a locked-down school/work network may block the AI service.

## Files

- `index.html`: page layout
- `style.css`: all styling
- `app.js`: desktop, windows, taskbar, Start, apps and settings
- `wallpaper.js`: the wallpapers and star animation
- `ai.js`: the AI app (assistants + Gemini)
- `library.js`: your games

## Rename it

Change `siteName` in `library.js`.

## Send it as one self-updating file

`Nebula.html` is the whole site squeezed into a single file **and** a thin wrapper that updates itself. When someone opens it, it first tries to pull the latest files from the GitHub folder set in `NEBULA_RAW` (top of `build.js`) and runs those; if there's no connection it falls back to the last good copy it cached, and then to a baked-in snapshot. **So you push a change to GitHub once and everyone who already has the file gets it next time they open it — no re-sending the file.**

Current update source:

```
https://raw.githubusercontent.com/drew110321-spec/scavenger/nebula/
```

- The source files live on the **`nebula` branch** of the public `scavenger` repo. Push a change there and every copy of `Nebula.html` updates on next open.
- Rebuild the file after any change by running `node build.js` in this folder. That refreshes the offline snapshot so people with no connection still get a recent version. (You only need to re-send `Nebula.html` if you change the wrapper itself or want the offline copy current — normal content changes just go to GitHub.)
- What travels in the one file: the desktop, Settings, and the AI assistants (with the key). Local-folder games like ORBIT are pulled from GitHub live, and are also baked into the snapshot for offline use.
- **The key:** it's stored base64-obfuscated in `library.js` (not plain text), which stops GitHub's secret scanners and casual snooping. It is **not** truly secret — anyone determined can still decode it from the file. Use a free key you can replace, and rotate it if it ever gets abused.

**Getting it to people — important for school Chromebooks:** a managed Chromebook often blocks opening a downloaded `.html` file (and local files in general). The reliable way is to put it online and share the link:

- Drag `Nebula.html` (or the whole folder) onto [app.netlify.com/drop](https://app.netlify.com/drop) — you get a web link in seconds, free, no account needed.
- Or use GitHub Pages / Cloudflare Pages.

Over a link (https) the AI is most reliable too. A double-click file works where local files are allowed, but a link is the safer bet for Chromebooks.

## Put it online

It's plain static files, so any static host works (GitHub Pages, Netlify Drop, Cloudflare Pages). Upload the whole folder — or just `Nebula.html` on its own.
