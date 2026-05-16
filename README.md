# ExpenseIQ

AI powered personal expense tracker

## What It Is

ExpenseIQ is a full stack personal finance app with a React PWA frontend, FastAPI backend, PostgreSQL database, and a Telegram bot for fire and forget expense capture.

## Tech Stack

1. Frontend: React, TypeScript, Vite, deployed on Vercel
2. Backend: FastAPI, Python, deployed on Render
3. Database: Supabase PostgreSQL
4. AI: Anthropic Claude API for expense parsing and insights
5. Bot: Telegram webhook bot for expense capture and queries
6. Uptime: UptimeRobot keeps Render warm to eliminate cold starts

## Features

1. Add expenses via Telegram by typing natural language such as "coffee 2.5 food"
2. Telegram commands: /today, /week, /month, /budget, /categories, /subs, /addsubscription, /removesub, /help
3. Dashboard with spending trends, category breakdown, and AI insights
4. Transactions page with filtering by month, year, and category
5. Budget tracking per category
6. Recurring expense rules
7. CSV and Excel export
8. PWA installable on iPhone and Android via browser

## Architecture

1. Frontend on Vercel, auto deploys on git push
2. Backend on Render free tier, auto deploys on git push
3. Database on Supabase PostgreSQL, connection via port 6543 pooler
4. Telegram webhook registered at /webhook/telegram on the Render backend
5. UptimeRobot pings /health every 5 minutes to keep Render awake

## Local Development

1. Backend uses SQLite by default when no DATABASE_URL is set
2. Frontend connects to localhost:8000
3. start.bat launches all local services

## Production Environment Variables For Render

1. DATABASE_URL
2. ANTHROPIC_API_KEY
3. CORS_ORIGINS
4. TELEGRAM_BOT_TOKEN
5. TELEGRAM_ALLOWED_USER_ID
