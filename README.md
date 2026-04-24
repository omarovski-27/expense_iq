# 💰 ExpenseIQ

> A powerful, AI-driven personal expense tracker

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.0-20232A?style=flat&logo=react&logoColor=61DAFB)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4.0-3178C6?style=flat&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Claude AI](https://img.shields.io/badge/Powered%20by-Claude%20AI-CC785C?style=flat&logo=anthropic&logoColor=white)](https://anthropic.com)

---

## ✨ Features

- 📊 **Dashboard** — KPI cards (total spend, budget used %, daily average, top category), 6-month spending trend chart, category donut breakdown, and live AI insight cards
- 💸 **Expense Tracking** — Full CRUD with sortable/paginated table, category badges, recurring indicators, bulk CSV import, and inline delete confirmation
- 🤖 **AI Insights** — Monthly narrative reports, spending spike detection (warning/critical), actionable recommendations, and a conversational AI chat powered by Claude
- 📈 **Analytics** — Spending trends over 6 months, per-category breakdowns, top merchant table, and month-over-month comparisons
- 💼 **Budget Management** — Per-category monthly budgets with circular progress rings, inline limit editing, projected month-end spend, and status badges
- 🔁 **Recurring Expenses** — Rule-based recurring engine (daily/weekly/monthly/yearly) with auto-creation on startup, active toggle, and manual run trigger
- 📤 **Exports** — Download filtered expenses as CSV or a styled 3-sheet Excel report (Transactions, Summary, Overview)
- ⚙️ **Settings** — Category manager (add/edit/delete with expense reassignment), CSV import, data export, currency symbol preference, date format toggle
- ⌨️ **Keyboard Shortcuts** — `n` to add expense, `/` to focus search, `Esc` to close modals
- 📱 **Responsive Sidebar** — Collapses to icon-only at < 768px with hover tooltips

---

## 🛠 Tech Stack

### Backend

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.111.0 | REST API framework |
| SQLModel | 0.0.18 | ORM (Pydantic + SQLAlchemy) |
| uvicorn | 0.29.0 | ASGI server |
| anthropic | 0.86.0+ | Claude AI SDK |
| pandas | 2.2.0 | Data manipulation + CSV export |
| openpyxl | 3.1.2 | Excel file generation |
| python-dotenv | 1.0.0 | `.env` file loading |
| python-dateutil | 2.9.0 | Recurring date arithmetic |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| React | 18.3.0 | UI framework |
| TypeScript | 5.4.0 | Type safety |
| Vite | 5.2.0 | Dev server + build tool |
| Tailwind CSS | 3.4.0 | Utility-first styling |
| Recharts | 2.12.0 | Charts (area, donut) |
| Axios | 1.6.0 | HTTP client |
| React Router | 6.23.0 | Client-side routing |
| react-hot-toast | 2.4.1 | Toast notifications |
| date-fns | 3.6.0 | Date utilities |
| lucide-react | 0.379.0 | Icon set |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- An [Anthropic API key](https://console.anthropic.com)

### Backend Setup

```bash
cd expense-tracker/backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd expense-tracker/frontend
npm install
```

---

## ▶️ Running the App

Open **two terminals** from the project root:

**Terminal 1 — Backend**
```bash
cd backend
.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## 🔑 Environment Variables

Create a `.env` file at the project root (`expense-tracker/.env`):

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required for AI features) | `sk-ant-api03-...` |
| `DATABASE_URL` | Path to the SQLite database file | `../data/expenses.db` |

```env
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=../data/expenses.db
```

> ⚠️ The `.env` file is gitignored. Never commit your API key.

---

## 📁 Project Structure

```
expense-tracker/
├── backend/
│   ├── main.py                    ← FastAPI app entry point
│   ├── database.py                ← SQLite engine + session
│   ├── models.py                  ← SQLModel table definitions
│   ├── routers/
│   │   ├── expenses.py            ← CRUD for expenses
│   │   ├── categories.py          ← CRUD for categories
│   │   ├── budgets.py             ← Budget management
│   │   ├── recurring.py           ← Recurring expense rules
│   │   ├── insights.py            ← AI insights endpoints
│   │   ├── analytics.py           ← Dashboard data endpoints
│   │   └── exports.py             ← CSV/Excel download endpoints
│   ├── services/
│   │   ├── ai_service.py          ← Claude API calls
│   │   ├── export_service.py      ← CSV/Excel generation
│   │   └── recurring_service.py   ← Recurring engine
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                ← Router setup + keyboard shortcuts
│   │   ├── components/
│   │   │   ├── layout/            ← Layout, Sidebar, Header
│   │   │   ├── charts/            ← SpendingTrendChart, CategoryDonutChart, BudgetProgressBar
│   │   │   ├── expenses/          ← AddExpenseModal, EditExpenseModal
│   │   │   └── ai/                ← InsightCard
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   ├── Insights.tsx
│   │   │   ├── Budgets.tsx
│   │   │   └── Settings.tsx
│   │   ├── api/                   ← Axios API clients
│   │   ├── types/                 ← TypeScript interfaces
│   │   └── utils/
│   │       └── formatCurrency.ts  ← Shared currency formatter
│   └── package.json
├── data/
│   └── expenses.db                ← Auto-created on first run
├── .env                           ← API keys (gitignored)
├── .gitignore
└── README.md
```

---

## 📖 API Documentation

FastAPI generates interactive docs automatically. With the backend running, visit:

- **Swagger UI** → http://localhost:8000/docs
- **ReDoc** → http://localhost:8000/redoc
- **Health check** → http://localhost:8000/health

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/expenses` | List expenses with filters |
| `POST` | `/api/expenses` | Create expense |
| `POST` | `/api/expenses/bulk-import` | Import CSV |
| `GET` | `/api/analytics/summary` | KPI totals |
| `GET` | `/api/analytics/trends` | 6-month trend data |
| `POST` | `/api/insights/generate` | Generate AI report |
| `POST` | `/api/insights/chat` | Chat with AI about finances |
| `GET` | `/api/exports/csv` | Download CSV export |
| `GET` | `/api/exports/excel` | Download Excel report |
| `POST` | `/api/recurring/run` | Trigger recurring expenses |

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

*Built with React, FastAPI, SQLite, and Claude AI · ExpenseIQ v1.0.0*
