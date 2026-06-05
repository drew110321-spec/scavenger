# Full-Blast Alarm Shortcut (60-second lockout)

Tap the home-screen icon → volume slams to 100 % → alarm blares for a
full 60 seconds. The only way to cut it short is to kill the Shortcut
from the control-center widget (you still have to dig for it).

---

## iOS Shortcut — step-by-step

Open the **Shortcuts** app, tap **+**, name it `ALARM`.

| # | Action | Setting |
|---|--------|---------|
| 1 | **Set Volume** | `1.0` (drag slider all the way right) |
| 2 | **Get Current Date** | — (save result → variable **`StartTime`**) |
| 3 | **Repeat** | `60` times |
| 4 | ↳ **Play Sound** | pick any built-in alert, e.g. *Alarm* or *SOS* |
| 5 | ↳ **Wait** | `1` second |
| 6 | *(end Repeat)* | — |

Steps 4-5 loop 60 times = **~60 seconds** of non-stop alarm at full volume.

Add it to your home screen: tap **⋯ → Add to Home Screen → Add**.

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
