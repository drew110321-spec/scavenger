# Full-Blast Alarm Shortcut (60-second lockout)

Tap the home-screen icon → volume slams to 100 % → alarm blares for a
full 60 seconds. The only way to cut it short is to kill the Shortcut
from the control-center widget (you still have to dig for it).

The icon is disguised to look like a Safari web link so nobody suspects it.

---

## Disguise: make it look like a link

When you add the shortcut to your home screen, iOS lets you set a custom
name and icon. Use these to make it look like a browser bookmark.

1. **Name** — use something that reads like a URL or a normal app:
   - `google.com` &nbsp;·&nbsp; `ESPN` &nbsp;·&nbsp; `Weather` &nbsp;·&nbsp; `News` &nbsp;·&nbsp; `BBC`
2. **Icon** — tap *Choose Photo* and use a screenshot of the Safari icon,
   a favicon, or any plain-looking app icon from your camera roll.
   - Easiest: screenshot the real Safari icon on your home screen, crop it
     tight, and use that image. It looks identical to a real link.
3. **Background color** — pick white or the site's brand color so it blends
   in with your other apps.

Result: the icon sits on your home screen looking exactly like a web
bookmark. Nobody taps it by accident — but *you* know what it does.

---

## iOS Shortcut — step-by-step

Open the **Shortcuts** app, tap **+**, name it `google.com` (or your
chosen disguise name).

| # | Action | Setting |
|---|--------|---------|
| 1 | **Set Volume** | `1.0` (drag slider all the way right) |
| 2 | **Get Current Date** | — (save result → variable **`StartTime`**) |
| 3 | **Repeat** | `60` times |
| 4 | ↳ **Play Sound** | pick any built-in alert, e.g. *Alarm* or *SOS* |
| 5 | ↳ **Wait** | `1` second |
| 6 | *(end Repeat)* | — |

Steps 4-5 loop 60 times = **~60 seconds** of non-stop alarm at full volume.

Add it to your home screen:
1. Tap **⋯** (top-right) → **Add to Home Screen**
2. Tap the icon square on the left → **Choose Photo** → pick your fake Safari/link icon
3. Change the name to `google.com` (or whatever disguise you chose)
4. Tap **Add**

---

## Optional: trigger via the server

If you want the shortcut to call the server first (e.g. to log the alarm
or get a spoken warning), insert this **before** step 1:

| # | Action | Setting |
|---|--------|---------|
| 0a | **URL** | `https://<your-server>/alarm` |
| 0b | **Get Contents of URL** | Method: **GET** · Headers: `Authorization: Bearer <SERVER_API_KEY>` |
| 0c | **Get Dictionary Value** | Key `speak` from *Contents of URL* |
| 0d | **Speak Text** | *Dictionary Value* from step 0c |

Then continue with steps 1-6 above.

---

## Tips

- **Louder on wake**: use the **Automation** tab to trigger this shortcut
  on a time or NFC tap so it fires even from the lock screen.
- **Harder to stop**: in the shortcut settings toggle
  *"Show While Running"* **off** — it runs silently in the background and
  the stop button is harder to find.
- **Restore volume after**: add a **Set Volume** `0.5` action after the
  Repeat block so your ears survive.
