# Quick capture without Telegram

Three ways to log an expense with no VPN, all hitting one endpoint, `POST /api/ingest`.
It runs the same parser as the Telegram bot, so `coffee 2.5 food` works everywhere.

| Channel | Best for | Needs |
|---|---|---|
| iOS Shortcut (Siri / Action Button / Back Tap) | Fastest capture, no app open | Device key |
| Installed web app (`/quick`) | Typing, category chips, undo, notifications | Device key, Home Screen install |
| Bank SMS automation | Card spend with zero typing | *Pending: parser tuned to your bank's SMS* |

---

## 1. One-time backend setup

1. **Make a device key** (any long random string):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. **Make push keys:**
   ```bash
   cd backend && python gen_vapid_keys.py
   ```
3. **Render → expenseiq-backend → Environment**, add:
   - `INGEST_API_KEY` = the device key
   - `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` = from step 2
   - `VAPID_SUBJECT` = `mailto:<your email>`
4. **GitHub → repo Settings → Secrets and variables → Actions**, add `INGEST_API_KEY` (same value).
   This powers the daily subscription-charge workflow.
5. Deploy. Check: `curl -X POST https://expense-iq-ypan.onrender.com/api/ingest -H "X-API-Key: <key>" -H "Content-Type: application/json" -d '{"text":"test 0.01"}'`
   then send `{"text":"undo"}` to remove it.

Treat the key like a password. Anyone holding it can read and change all your expenses.

**The whole app needs this key.** Every `/api/*` route answers `401` without it, so the
dashboard asks for it too (see section 4). If `INGEST_API_KEY` is not set on Render, every
route answers `503` and the app shows nothing, so set it **before** deploying this version.

---

## 2. iOS Shortcut: "Log expense"

Shortcuts app → **+** → name it **Log expense**, then add these actions in order:

1. **Dictate Text** (or **Ask for Input** → Text, if you'd rather type).
2. **Get Contents of URL**
   - URL: `https://expense-iq-ypan.onrender.com/api/ingest`
   - Method: **POST**
   - Headers: `X-API-Key` = *your key*
   - Request Body: **JSON**, one field: `text` (Text) = *Dictated Text* (the variable from step 1)
3. **Get Dictionary Value**: Key `message` from *Contents of URL*.
4. **Show Notification**: *Dictionary Value*.

Trigger it any of these ways:
- **Siri:** "Hey Siri, log expense," then say "shawarma three point five food."
- **Action Button** (iPhone 15 Pro and later): Settings → Action Button → Shortcut → Log expense.
- **Back Tap** (any recent iPhone): Settings → Accessibility → Touch → Back Tap → Double Tap → Log expense.

What you can say or type:
- `coffee 2.5 food` · `8.5 transport` · `netflix 7` (no category means Other)
- Add `yesterday` anywhere to backdate: `taxi 4 yesterday`
- `undo` removes the last quick-added expense (within 15 minutes)

The confirmation includes your running total for the day.

Optional second Shortcut, **Undo expense**: the same Shortcut without step 1, with the body `text` = `undo`.

---

## 3. Installed web app

1. On iPhone, open the Vercel URL **in Safari** → Share → **Add to Home Screen**.
2. Open it from the Home Screen icon. It starts on the quick-add screen.
3. Tap the settings icon, paste your device key, and tap **Save**. The key is stored on this device only.
4. Tap **Turn on notifications**, then **Send test**.
   iOS only allows web push for apps opened from the Home Screen.

Notifications fire when a subscription is auto-charged. That happens on the daily GitHub
Actions run (09:07 Amman) or on a cold start.

---

## 4. Dashboard (any browser)

The first time you open the dashboard on a device it shows one screen: **Enter your device
key**. Paste the same key and tap **Save**. It is stored on that device only. If the key on
Render changes, the dashboard shows the screen again with "That device key was not accepted".
CSV and Excel exports download with the key, so they work the same way.

---

## Notes and limits

- **Cold starts:** if Render is asleep, the first request takes about 30s. The Shortcut waits.
  The web app shows "Waking the server up". The keep-warm workflow makes this rare.
- **Telegram still works** if you're on a VPN. Nothing was removed.
- **What stays open without the key:** `/health` (uptime pings), `/webhook/telegram` (the bot
  only answers your Telegram user id) and `GET /api/notify/vapid-public-key` (a public value
  push needs). Everything else under `/api` needs the key. `backend/tests/test_auth.py` walks
  every route, so a new route added without the key fails the tests.
- **Telegram webhook secret (not yet on):** the webhook does not check Telegram's
  `X-Telegram-Bot-Api-Secret-Token` header, so anyone who learns the URL can post fake updates
  (they still have to fake your user id). Fix when convenient: add `TELEGRAM_WEBHOOK_SECRET`
  on Render, reject requests whose header doesn't match, and re-register the webhook with
  `secret_token` (that call needs a VPN).
