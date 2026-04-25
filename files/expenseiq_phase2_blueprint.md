# EXPENSEIQ — PHASE 2 DEPLOYMENT BLUEPRINT
# PWA + Render + Supabase + Vercel + Telegram Bot
# Goal: Full app on phone + fire-and-forget Telegram capture + zero laptop dependency
# Cost: $0/month permanently

---

> HOW TO USE THIS DOCUMENT
> Same as the original blueprint. Every phase has exact Copilot prompts.
> Work phase by phase. Never skip. Each phase has a VERIFY step before moving on.
> If a VERIFY step fails — stop and fix before continuing. This is the guardrail.

---

## ARCHITECTURE

```
Supabase     PostgreSQL database (free, always on, data never lost)
Render       FastAPI backend (free, sleeps after 15min idle, wakes on request)
Render       Telegram bot worker (free, same sleep behavior)
Vercel       React frontend (free, always on, auto-deploys from GitHub)
iPhone       PWA installed from Vercel URL via Safari
Telegram     Fire and forget expense capture, processes in background
```

## COST BREAKDOWN
```
Supabase        $0/month   500MB PostgreSQL, never sleeps, data permanent
Render          $0/month   2 free services (backend + bot)
Vercel          $0/month   frontend hosting, always on
Anthropic API   $0.50-1    only when you click Generate Insights
Telegram Bot    $0          always free
TOTAL           $0-1/month
```

## IMPORTANT — SLEEP BEHAVIOR
```
Render free tier sleeps after 15 minutes of no activity.
Wake time: 30 seconds on first request after idle.

What this means for you:
- Telegram: type expense, hit send, move on with your day.
  Confirmation arrives within 30-60 seconds. You do not need to wait.
- Opening app after hours idle: 30 second load on first open.
  After that everything is instant for the rest of the day.
- During active use (multiple messages per day): server stays warm, instant.

Upgrade to Render paid ($7/month) anytime for zero sleep behavior.
```

## PHASES
```
Phase 1  Database setup on Supabase                      ~15 mins
Phase 2  Backend migration + hardening + Render deploy   ~30 mins
Phase 3  Frontend update + Vercel deployment             ~15 mins
Phase 4  PWA installation on iPhone                      ~5 mins
Phase 5  Telegram bot build + Render deployment          ~30 mins
Phase 6  Mobile UI polish                                ~20 mins
Phase 7  Full system test + error boundaries             ~20 mins
```

Total: roughly 2 hours. Do not rush. Verify each phase before continuing.

---

## PHASE 1 — DATABASE SETUP ON SUPABASE

### Why Supabase
Supabase gives you a free PostgreSQL database that is always on and never loses
data. Render's filesystem resets on redeploy which would wipe SQLite data.
Supabase data persists forever on the free tier.

### Step 1A — Create Supabase project
1. Go to supabase.com and sign up with GitHub
2. Click New Project
3. Name: expenseiq
4. Set a strong database password and save it somewhere safe
5. Region: eu-central-1 (closest to Jordan)
6. Click Create new project — takes about 2 minutes
7. Once ready: go to Project Settings → Database
8. Scroll to Connection string → select URI tab
9. Copy the string — looks like:
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
10. Replace [YOUR-PASSWORD] with your actual password
11. Save this — it is your DATABASE_URL for every service

### Step 1B — Install PostgreSQL driver
Run in terminal:
```
cd C:\Users\Omar\expense-tracker\backend
.venv\Scripts\activate
pip install psycopg2-binary==2.9.9
pip freeze > requirements.txt
```

### Step 1C — COPILOT PROMPT — Update database.py
```
Update backend/database.py to support PostgreSQL (Supabase in production)
and SQLite (local development). Replace the entire file.

1. Imports:
   from sqlmodel import create_engine, Session, SQLModel
   from dotenv import load_dotenv
   import os
   load_dotenv()

2. Read DATABASE_URL from environment:
   database_url = os.getenv("DATABASE_URL", "sqlite:///../data/expenses.db")

3. Fix Supabase URL prefix — Supabase gives "postgres://" but SQLAlchemy
   needs "postgresql://":
   if database_url.startswith("postgres://"):
       database_url = database_url.replace("postgres://", "postgresql://", 1)

4. Create engine based on type:
   if database_url.startswith("sqlite"):
       engine = create_engine(
           database_url,
           connect_args={"check_same_thread": False}
       )
   else:
       engine = create_engine(
           database_url,
           pool_pre_ping=True,
           pool_size=5,
           max_overflow=10,
           pool_recycle=300
       )
   pool_recycle=300 prevents stale connections after Render wakes from sleep.

5. Keep get_session() and create_db_and_tables() exactly unchanged.

No other files change. SQLModel handles both databases transparently.
```

### VERIFY PHASE 1
```
cd backend
.venv\Scripts\activate
uvicorn main:app --reload
```
Open http://localhost:8000/health
Must return: {"status":"ok","version":"1.0.0"}
Phase 1 complete if health check passes locally.

---

## PHASE 2 — BACKEND HARDENING + RENDER DEPLOYMENT

### Step 2A — COPILOT PROMPT — Harden backend for production
```
Make production-hardening changes to the ExpenseIQ backend.
Do not change any business logic. Only add safety and resilience.

1. In backend/main.py:
   Read CORS origins from CORS_ORIGINS environment variable
   (comma-separated). Split and strip whitespace.
   Always include http://localhost:5173 as fallback.
   Add allow_origin_regex="https://.*\.vercel\.app" to also allow
   all Vercel preview URLs automatically.

   Add global exception handler @app.exception_handler(Exception):
   Logs error with traceback using Python logging module.
   Returns JSON {"detail": "Internal server error"} with status 500.
   Never expose raw Python errors to the client.

   Wrap process_recurring_expenses() in startup in try/except.
   Log any error but never crash the server on startup failure.

2. In backend/routers/insights.py:
   At the top of /chat and /generate endpoints:
   if not os.getenv("ANTHROPIC_API_KEY"):
       raise HTTPException(503, "AI service not configured")

3. In backend/routers/analytics.py:
   Wrap all database queries in try/except.
   On exception: log it, return HTTP 500 {"detail": "Analytics query failed"}.

4. Create backend/routers/health.py with APIRouter(prefix="/health", tags=["health"]):
   GET /detailed returns:
   {
     "status": "ok",
     "database": "connected" or "error: {message}",
     "ai_service": "configured" or "not configured",
     "version": "1.0.0"
   }
   Test database: run db.exec(text("SELECT 1")) inside try/except.
   Import text from sqlalchemy.
   Check AI: bool(os.getenv("ANTHROPIC_API_KEY"))
   Add this router to main.py includes list.
```

### Step 2B — COPILOT PROMPT — Create Render config files
```
Create deployment configuration files for Render at the ROOT of
expense-tracker (not inside backend or frontend folders).

1. Create render.yaml:

services:
  - type: web
    name: expenseiq-backend
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: CORS_ORIGINS
        sync: false
      - key: BACKEND_URL
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_ALLOWED_USER_ID
        sync: false

  - type: worker
    name: expenseiq-telegram-bot
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: python telegram_bot.py
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: BACKEND_URL
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_ALLOWED_USER_ID
        sync: false

2. Update .gitignore at ROOT to ensure these are excluded:
   .env
   .env.local
   *.db
   __pycache__
   .venv
   node_modules
   dist
```

### Step 2C — Push to GitHub
```
cd C:\Users\Omar\expense-tracker
git add .
git commit -m "feat: Supabase PostgreSQL + production hardening + Render config"
git push
```

### Step 2D — Deploy backend to Render
1. Go to render.com and sign up with GitHub
2. Click New → Web Service
3. Connect repo: omarovski-27/expense_iq
4. Settings:
   Name: expenseiq-backend
   Root Directory: backend
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   Instance Type: Free
5. Add environment variables:
   DATABASE_URL → your Supabase connection string
   ANTHROPIC_API_KEY → your Anthropic key
   CORS_ORIGINS → http://localhost:5173 (update after Vercel)
6. Click Create Web Service
7. Build takes 3-5 minutes first time
8. Render gives you: https://expenseiq-backend.onrender.com
9. Copy this URL

### VERIFY PHASE 2
Open in browser (first load may take 30 seconds):
https://expenseiq-backend.onrender.com/health
Must return: {"status":"ok","version":"1.0.0"}

https://expenseiq-backend.onrender.com/health/detailed
Must return: database "connected" and ai_service "configured"

If database shows error: recheck DATABASE_URL in Render environment variables.
Phase 2 complete when both endpoints pass.

---

## PHASE 3 — FRONTEND UPDATE + VERCEL DEPLOYMENT

### Step 3A — COPILOT PROMPT — Update frontend for production
```
Update ExpenseIQ frontend for production deployment on Vercel.

1. Update frontend/src/api/client.ts:
   Change baseURL to:
   const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api"

   Update error interceptor messages:
   Network error (no response): toast.error("Cannot reach server. It may be
     waking up. Try again in 30 seconds.")
   503 status: toast.error("AI service temporarily unavailable.")
   500 status: toast.error("Server error. Please try again.")
   All other errors: keep existing behavior.

2. Create frontend/.env.production:
   VITE_API_URL=https://expenseiq-backend.onrender.com/api
   Replace with your actual Render URL.

3. Keep frontend/.env.local:
   VITE_API_URL=http://localhost:8000/api

4. Update frontend/vite.config.ts — add inside defineConfig alongside
   existing plugins, do not remove anything:
   build: {
     rollupOptions: {
       output: {
         manualChunks: {
           vendor: ["react", "react-dom", "react-router-dom"],
           charts: ["recharts"],
           ui: ["lucide-react"]
         }
       }
     }
   }
```

### Step 3B — COPILOT PROMPT — Add PWA support
```
Add PWA support to ExpenseIQ frontend.

First run this in the frontend folder terminal:
npm install vite-plugin-pwa --save-dev

Then make these changes:

1. Update frontend/vite.config.ts:
   Add import at top: import { VitePWA } from "vite-plugin-pwa"
   Add VitePWA to plugins array (keep all existing plugins):
   VitePWA({
     registerType: "autoUpdate",
     includeAssets: ["favicon.ico", "icon-192.png", "icon-512.png"],
     manifest: {
       name: "ExpenseIQ",
       short_name: "ExpenseIQ",
       description: "AI-powered personal expense tracker",
       theme_color: "#111827",
       background_color: "#111827",
       display: "standalone",
       orientation: "portrait",
       start_url: "/",
       scope: "/",
       icons: [
         {
           src: "/icon-192.png",
           sizes: "192x192",
           type: "image/png",
           purpose: "any maskable"
         },
         {
           src: "/icon-512.png",
           sizes: "512x512",
           type: "image/png",
           purpose: "any maskable"
         }
       ]
     },
     workbox: {
       globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
       runtimeCaching: [
         {
           urlPattern: /^https:\/\/.*\.onrender\.com\/api\/.*/i,
           handler: "NetworkFirst",
           options: {
             cacheName: "api-cache",
             expiration: { maxEntries: 50, maxAgeSeconds: 300 },
             networkTimeoutSeconds: 35
           }
         }
       ]
     }
   })
   networkTimeoutSeconds is 35 to account for Render wake time.

2. Update frontend/index.html inside head tag:
   <meta name="theme-color" content="#111827">
   <meta name="apple-mobile-web-app-capable" content="yes">
   <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
   <meta name="apple-mobile-web-app-title" content="ExpenseIQ">
   <link rel="apple-touch-icon" href="/icon-192.png">
   <meta name="viewport" content="width=device-width, initial-scale=1.0,
     maximum-scale=1.0, user-scalable=no">

3. Create frontend/public/icon-192.png and icon-512.png:
   Dark background #111827 with centered amber dollar sign #F59E0B.
   If PNG generation not possible: create icon.svg with same design,
   reference it in manifest with type "image/svg+xml" and sizes "any".
```

### Step 3C — Deploy to Vercel
1. Go to vercel.com and sign up with GitHub
2. Click Add New Project → Import omarovski-27/expense_iq
3. Settings:
   Framework Preset: Vite
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: dist
4. Add environment variable:
   VITE_API_URL = https://expenseiq-backend.onrender.com/api
5. Click Deploy — takes 2-3 minutes
6. Vercel gives you: https://expenseiq.vercel.app
7. Copy this URL

### Step 3D — Update Render CORS
Render → expenseiq-backend → Environment → update CORS_ORIGINS:
```
https://expenseiq.vercel.app,http://localhost:5173
```
Render auto-redeploys.

### Step 3E — Push changes
```
cd C:\Users\Omar\expense-tracker
git add .
git commit -m "feat: PWA support + production API config + Vercel ready"
git push
```
Every future git push auto-deploys to Vercel automatically.

### VERIFY PHASE 3
1. Open https://expenseiq.vercel.app on laptop
2. DevTools → Network → confirm API calls go to onrender.com not localhost
3. Open on iPhone Safari → full app loads
4. Add test expense from phone → appears on laptop
Phase 3 complete when cross-device sync confirmed.

---

## PHASE 4 — INSTALL ON IPHONE (2 minutes)

1. Open Safari on iPhone (must be Safari, not Chrome)
2. Go to: https://expenseiq.vercel.app
3. First load may take 30 seconds — Render waking up — this is normal
4. Tap Share button (box with arrow, bottom of screen)
5. Tap Add to Home Screen
6. Name: ExpenseIQ → tap Add
7. Icon appears on home screen
8. Open it — full screen, dark theme, no browser bar

### VERIFY PHASE 4
Open from home screen → add expense → check on laptop → must appear.
Phase 4 complete.

---

## PHASE 5 — TELEGRAM BOT

### Step 5A — Create bot (3 minutes, no code)
1. Open Telegram → search @BotFather → tap Start
2. Send: /newbot
3. Name: ExpenseIQ
4. Username: expenseiq_omar_bot
5. BotFather sends token: 7234567890:AAFxxx... → copy it

### Step 5B — Get your Telegram user ID
1. Search @userinfobot on Telegram
2. Send any message
3. It replies with your numeric ID like 123456789 → copy it

### Step 5C — Add to local .env
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_ALLOWED_USER_ID=123456789
BACKEND_URL=https://expenseiq-backend.onrender.com
```

### Step 5D — Install dependencies
```
cd backend
.venv\Scripts\activate
pip install python-telegram-bot==20.7 httpx==0.27.0
pip freeze > requirements.txt
```

### Step 5E — COPILOT PROMPT — Build Telegram bot
```
Create backend/telegram_bot.py for ExpenseIQ.

Use python-telegram-bot version 20.7 (async).
Load config from .env using python-dotenv.

CONFIGURATION at module level:
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

If TELEGRAM_BOT_TOKEN is empty or None: print error message and sys.exit(1).

SECURITY:
Every single handler must check as first line:
if update.effective_user.id != ALLOWED_USER_ID:
    await update.message.reply_text("Unauthorized.")
    return
No exceptions to this rule.

HTTP HELPER — async def call_backend(method, path, data=None):
Use httpx.AsyncClient with timeout=40 (accounts for Render wake time)
Full URL: f"{BACKEND_URL}/api{path}"
On httpx.ConnectError: raise Exception("Backend unavailable — may be waking up")
On httpx.TimeoutException: raise Exception("Request timed out — try again shortly")
Return response.json()

CATEGORY CACHE:
Module-level dict _category_cache = {"data": [], "timestamp": 0}
async def get_categories():
  if time.time() - _category_cache["timestamp"] > 300 (5 min TTL):
    categories = await call_backend("GET", "/categories")
    _category_cache["data"] = categories
    _category_cache["timestamp"] = time.time()
  return _category_cache["data"]

async def find_category_id(text):
  categories = await get_categories()
  text_lower = text.lower()
  for cat in categories:
    if text_lower in cat["name"].lower() or cat["name"].lower() in text_lower:
      return cat["id"], cat["name"]
  for cat in categories:
    if cat["name"].lower() == "other":
      return cat["id"], "Other"
  return categories[0]["id"], categories[0]["name"]

MESSAGE PARSER — async def parse_expense(text):
Clean the text: strip, replace commas with periods in numbers.
Remove currency symbols: JD, jd, $, €, £ using regex.
Split into tokens by whitespace.

Try to identify amount token: first token that is a valid float > 0.
Try to identify category: check each non-amount token against category names.
Remaining tokens become merchant name.

Return dict: {amount, merchant, category_id, category_name}
or None if no valid amount found.

MESSAGE HANDLER (handles all non-command text):
1. Security check
2. Call parse_expense(message text)
3. If None: reply with format help
4. POST to /api/expenses:
   {amount, description: merchant or "Expense", category_id,
    merchant: merchant or "", date: today YYYY-MM-DD,
    is_recurring: false, notes: ""}
5. On success:
   "Added: {merchant} — {amount} JD ({category_name})
    {today as 'Sat, Apr 25 2026'}
    
    /today to see all expenses today"
6. On backend error: "Could not save — server may be waking up. Try again shortly."
7. On parse error: format help message

COMMANDS:

/start:
  "ExpenseIQ ready.
   
   Send expenses like:
   netflix 14.7 bills
   lunch 8.5 food
   petrol 20 transport
   
   /help for all commands"

/help:
  "Formats:
   merchant amount category: netflix 14.7 bills
   amount category: 8.5 food
   merchant amount: coffee 2.5
   amount only: 14.7 (category defaults to Other)
   
   Commands:
   /today — expenses today
   /month — this month summary
   /budget — budget status
   /categories — list all categories"

/today:
  GET /api/expenses?month={M}&year={Y}&limit=200
  Filter where date field == today string
  If empty: "No expenses today yet."
  Else format numbered list with total at bottom
  Separator line using dashes between list and total

/month:
  GET /api/analytics/summary?month={M}&year={Y}
  Format as clean multi-line summary with month name and year
  Include: total, daily average, mom change, budget used percent
  On error: "Could not load summary."

/budget:
  GET /api/budgets/status?month={M}&year={Y}
  Format each category as one line: name, spent/limit, percent, status word
  Status: OK (under 70%), WARNING (70-90%), OVER (above 90%)
  If no budgets: "No budgets set. Configure them in the app."

/categories:
  GET /api/categories
  Reply comma-separated list of category names

ALL ERROR HANDLING:
Every handler wrapped in outer try/except.
Connection refused: "Server is starting up, try again in 30 seconds."
Timeout: "Request timed out. Server waking up. Try again shortly."
Any other: log full traceback, reply "Something went wrong. Try again."
Bot must never crash. All exceptions caught.

STARTUP:
After application starts: send message to ALLOWED_USER_ID:
"ExpenseIQ bot online.
 Backend: {BACKEND_URL}
 /help for commands."

Entry point:
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("today", today_handler))
    application.add_handler(CommandHandler("month", month_handler))
    application.add_handler(CommandHandler("budget", budget_handler))
    application.add_handler(CommandHandler("categories", categories_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, expense_handler))
    application.run_polling(allowed_updates=Update.ALL_TYPES)
```

### Step 5F — COPILOT PROMPT — Update start.bat
```
Replace the entire content of start.bat at the root of expense-tracker:

@echo off
title ExpenseIQ Launcher
echo Starting ExpenseIQ...
echo.
start "ExpenseIQ Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn main:app --reload --port 8000"
echo Backend starting...
timeout /t 3 /nobreak > nul
start "ExpenseIQ Telegram Bot" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && python telegram_bot.py"
echo Telegram bot starting...
timeout /t 4 /nobreak > nul
start "ExpenseIQ Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host"
echo Frontend starting...
timeout /t 5 /nobreak > nul
start "" "http://localhost:5173"
echo.
echo All services started.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo Bot:      Running in Telegram Bot window
echo.
pause
```

### Step 5G — Deploy bot to Render
1. Render → New → Background Worker
2. Connect omarovski-27/expense_iq
3. Settings:
   Name: expenseiq-telegram-bot
   Root Directory: backend
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python telegram_bot.py
   Instance Type: Free
4. Environment variables:
   DATABASE_URL → Supabase URL
   BACKEND_URL → https://expenseiq-backend.onrender.com
   TELEGRAM_BOT_TOKEN → your token
   TELEGRAM_ALLOWED_USER_ID → your numeric ID
5. Click Create Background Worker

### Step 5H — Push and deploy
```
cd C:\Users\Omar\expense-tracker
git add .
git commit -m "feat: Telegram bot + updated start.bat"
git push
```

### VERIFY PHASE 5
1. Telegram → your bot → /start → ready message received
2. Send: "netflix 14.7 bills" → move on, wait up to 60 seconds → confirmation arrives
3. Open ExpenseIQ on phone → Netflix expense appears in dashboard
4. Send: /today → lists the expense
5. Send: /budget → returns budget status
6. Send nonsense "xkcd zzz" → helpful format error, bot does not crash
Phase 5 complete when all pass.

---

## PHASE 6 — MOBILE UI POLISH

### Step 6A — COPILOT PROMPT — Mobile responsive layout
```
Improve ExpenseIQ for mobile screens (375-430px wide).
Use only Tailwind responsive prefixes (md:, lg:).
Never use JavaScript window.innerWidth.
Desktop layout must remain completely unchanged.

1. frontend/src/components/layout/Layout.tsx:
   Sidebar: add "hidden md:flex" class to hide on mobile.
   Add bottom navigation bar — visible only on mobile (flex md:hidden):
     fixed bottom-0 left-0 right-0 z-50
     bg-gray-950 border-t border-gray-800 h-16
     flex justify-around items-center px-2
   5 nav items using NavLink: Dashboard, Transactions, Insights, Budgets, Settings
   Each item: flex-col items-center gap-0.5 px-3 py-2
   Icon size 22px from lucide-react, label text-xs below
   Active: text-amber-400, inactive: text-gray-500
   Add pb-16 md:pb-0 to main content wrapper to prevent bottom nav overlap.

2. frontend/src/pages/Dashboard.tsx:
   KPI grid: "grid grid-cols-2 md:grid-cols-4"
   Chart row: "flex flex-col md:flex-row"
   Floating add button position: "bottom-20 right-4 md:bottom-6 md:right-6"

3. frontend/src/pages/Transactions.tsx:
   On mobile: show card list (block md:hidden), hide table (hidden md:block)
   Each expense card:
     bg-gray-800 rounded-xl p-4 mb-3 flex justify-between items-start border border-gray-700
     Left side: merchant or description in text-white font-medium,
       category badge + date in text-gray-400 text-sm below
     Right side: amount in text-amber-400 font-bold,
       edit and delete icon buttons below in text-gray-500

4. AddExpenseModal and EditExpenseModal:
   On mobile: bottom sheet instead of centered modal.
   Outer wrapper: "fixed inset-0 z-50 flex items-end md:items-center justify-center"
   Inner panel: "w-full md:w-auto md:max-w-md rounded-t-2xl md:rounded-xl bg-gray-800"
   Add drag handle at top (mobile only):
     "w-10 h-1 bg-gray-600 rounded-full mx-auto mt-3 mb-2 md:hidden"
   Max height mobile: "max-h-[90vh] overflow-y-auto"

5. All form inputs across the app:
   Add text-base class to all input and select elements to ensure
   minimum 16px font size — prevents iOS Safari auto-zoom on focus.
   Add touch-action: manipulation via style prop or Tailwind class
   on all buttons: "touch-manipulation" if available, else inline style.
   Minimum button height: h-11 (44px) on all interactive elements.
```

### VERIFY PHASE 6
1. Open app on iPhone from home screen
2. Bottom nav visible with 5 icons — all navigate correctly
3. Add Expense opens as bottom sheet from bottom of screen
4. No zoom on input focus
5. Open on laptop — sidebar visible, desktop layout unchanged
Phase 6 complete when both views correct.

---

## PHASE 7 — FULL SYSTEM TEST + ERROR BOUNDARIES

### Step 7A — COPILOT PROMPT — Error boundaries
```
Add React Error Boundaries to prevent white screen crashes in ExpenseIQ.

1. Create frontend/src/components/ErrorBoundary.tsx:
   Class component extending React.Component<
     {children: React.ReactNode},
     {hasError: boolean; error: Error | null}
   >

   state = { hasError: false, error: null }

   static getDerivedStateFromError(error: Error) {
     return { hasError: true, error }
   }

   componentDidCatch(error: Error, info: React.ErrorInfo) {
     console.error("ExpenseIQ Error:", error, info)
   }

   render() {
     if (this.state.hasError) {
       return (
         <div className="bg-gray-800 rounded-xl p-8 m-6 text-center border border-red-800">
           AlertCircle icon from lucide-react, size 48, className text-red-400
           <h2 className="text-white text-xl font-bold mt-4">Something went wrong</h2>
           <p className="text-gray-400 text-sm mt-2">{this.state.error?.message}</p>
           <button
             onClick={() => window.location.reload()}
             className="bg-amber-500 text-black px-6 py-2 rounded-lg mt-6 font-medium"
           >
             Reload Page
           </button>
         </div>
       )
     }
     return this.props.children
   }

2. In frontend/src/App.tsx:
   Import ErrorBoundary.
   Wrap each route individually so one broken page cannot crash the app:
   <Route path="/" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
   Apply to all 5 routes.

3. In frontend/src/api/client.ts after creating the axios instance:
   window.addEventListener("unhandledrejection", (event) => {
     console.error("Unhandled promise rejection:", event.reason)
     event.preventDefault()
   })
```

### Complete System Test Checklist
Run every item. Do not skip any.

CORE FEATURES
- [ ] Add expense from laptop → appears on iPhone instantly
- [ ] Add expense from iPhone → appears on laptop instantly
- [ ] Telegram "lunch 8.5 food" → fires and forgets → expense appears in app
- [ ] Edit expense → reflects on both devices
- [ ] Delete expense → removed on both devices
- [ ] Bulk CSV import → all rows appear
- [ ] Export CSV → correct file downloads
- [ ] Export Excel → 3 sheets with correct data

AI FEATURES
- [ ] Generate AI report → Claude responds with insights
- [ ] AI chat "how much this month?" → correct answer
- [ ] Dismiss insight → removed from page

BUDGETS AND RECURRING
- [ ] Set budget → progress bar updates
- [ ] Active toggle → circle RIGHT when active, LEFT when inactive
- [ ] Recurring monthly total → correct sum of active rules

SETTINGS
- [ ] Change currency to JD → reflects everywhere instantly
- [ ] Change back to $ → reflects everywhere instantly

TELEGRAM
- [ ] /start → ready message
- [ ] /today → correct list and total
- [ ] /month → correct summary
- [ ] /budget → correct per-category status
- [ ] /categories → full list
- [ ] /help → format examples shown
- [ ] Nonsense text → helpful error, bot does not crash
- [ ] Wrong user → Unauthorized reply

MOBILE PWA
- [ ] Opens full screen from home screen icon
- [ ] Bottom nav works on all 5 pages
- [ ] Add expense opens as bottom sheet
- [ ] No zoom on input focus on iPhone
- [ ] Desktop layout unchanged on laptop

### Final commit after all checks pass
```
cd C:\Users\Omar\expense-tracker
git add .
git commit -m "feat: Phase 2 complete — PWA + Render + Supabase + Telegram + mobile UI"
git push
```

Vercel auto-deploys frontend.
Render auto-deploys backend and bot.

---

## ENVIRONMENT VARIABLES REFERENCE

### Render — expenseiq-backend
```
DATABASE_URL              postgresql://postgres:...@db.supabase.co:5432/postgres
ANTHROPIC_API_KEY         your key
CORS_ORIGINS              https://expenseiq.vercel.app,http://localhost:5173
BACKEND_URL               https://expenseiq-backend.onrender.com
TELEGRAM_BOT_TOKEN        from BotFather
TELEGRAM_ALLOWED_USER_ID  your numeric Telegram ID
```

### Render — expenseiq-telegram-bot
```
DATABASE_URL              same Supabase URL
BACKEND_URL               https://expenseiq-backend.onrender.com
TELEGRAM_BOT_TOKEN        same token
TELEGRAM_ALLOWED_USER_ID  same ID
```

### Vercel — frontend
```
VITE_API_URL              https://expenseiq-backend.onrender.com/api
```

### Local backend/.env
```
DATABASE_URL              leave empty (uses local SQLite)
ANTHROPIC_API_KEY         your key
TELEGRAM_BOT_TOKEN        your token
TELEGRAM_ALLOWED_USER_ID  your ID
BACKEND_URL               http://localhost:8000
CORS_ORIGINS              http://localhost:5173
```

---

## FINAL RESULT

```
Daily flow:
  Lunch        open Telegram, type "lunch 8.5 food", send, put phone away
  Coffee       "coffee 2.5 food", send, done
  Petrol       "petrol 20 transport", send, done

Evening or weekend:
  Open ExpenseIQ from home screen icon
  Dashboard shows everything
  Generate AI report
  Check budgets

Monthly:
  Open on laptop for big screen view
  Export Excel report
  Review AI insights

Zero laptop dependency. Zero manual server starts. Total cost $0-1/month.
```

---

ExpenseIQ Phase 2 Blueprint v2.0 — Render + Supabase + Vercel + Telegram
