# 💰 EXPENSEIQ — Complete Implementation Blueprint
**Stack:** React + TypeScript + FastAPI + SQLite + Claude AI  
**Toolchain:** VSCode + GitHub Copilot + GitHub  
**Target:** Full-stack, locally-run, GitHub-ready, app-quality expense tracker

---

> **HOW TO USE THIS DOCUMENT**  
> This is your master build guide. Each phase has exact prompts to paste into GitHub Copilot Chat (Ctrl+Alt+I in VSCode).  
> Work phase by phase. Do not skip ahead. Each phase builds on the last.

---

## TABLE OF CONTENTS
1. [Tech Stack](#tech-stack)
2. [Folder Structure](#folder-structure)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Frontend Architecture](#frontend-architecture)
6. [AI Integration Spec](#ai-integration-spec)
7. [Phase-by-Phase Build Guide](#phases)
8. [Copilot Prompts — Ready to Paste](#copilot-prompts)
9. [Environment Setup](#environment-setup)

---

## 1. TECH STACK

### Backend
| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime |
| fastapi | 0.111.0 | REST API framework |
| sqlmodel | 0.0.18 | ORM (Pydantic + SQLAlchemy) |
| uvicorn | 0.29.0 | ASGI server |
| anthropic | 0.25.0 | Claude AI SDK |
| pandas | 2.2.0 | Data manipulation + export |
| openpyxl | 3.1.2 | Excel file generation |
| python-dotenv | 1.0.0 | .env file loading |
| schedule | 1.2.1 | Recurring expense scheduler |

### Frontend
| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.3.0 | UI framework |
| typescript | 5.4.0 | Type safety |
| vite | 5.2.0 | Dev server + build tool |
| tailwindcss | 3.4.0 | Utility-first styling |
| @shadcn/ui | latest | Component library |
| recharts | 2.12.0 | Charts (line, bar, pie, area) |
| axios | 1.6.0 | HTTP client |
| react-router-dom | 6.23.0 | Client-side routing |
| react-hot-toast | 2.4.1 | Toast notifications |
| date-fns | 3.6.0 | Date utilities |
| lucide-react | 0.379.0 | Icon set |

---

## 2. FOLDER STRUCTURE

```
expense-tracker/
├── backend/
│   ├── main.py                    ← FastAPI app entry point
│   ├── database.py                ← SQLite engine + session
│   ├── models.py                  ← SQLModel table definitions
│   ├── schemas.py                 ← Request/response Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── expenses.py            ← CRUD for expenses
│   │   ├── categories.py          ← CRUD for categories
│   │   ├── budgets.py             ← Budget management
│   │   ├── recurring.py           ← Recurring expense rules
│   │   ├── insights.py            ← AI insights endpoints
│   │   ├── analytics.py           ← Dashboard data endpoints
│   │   └── exports.py             ← CSV/Excel download endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── expense_service.py     ← Expense business logic
│   │   ├── analytics_service.py   ← Aggregations + spike detection
│   │   ├── recurring_service.py   ← Recurring engine (checks + creates)
│   │   ├── ai_service.py          ← Claude API calls
│   │   └── export_service.py      ← CSV/Excel generation
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                ← Router setup
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Layout.tsx     ← Sidebar + main wrapper
│   │   │   │   ├── Sidebar.tsx    ← Left nav
│   │   │   │   └── Header.tsx     ← Top bar with page title
│   │   │   ├── charts/
│   │   │   │   ├── SpendingTrendChart.tsx    ← 6-month line chart
│   │   │   │   ├── CategoryDonutChart.tsx    ← Pie breakdown
│   │   │   │   ├── MonthlyBarChart.tsx       ← Side-by-side month bars
│   │   │   │   └── BudgetProgressBar.tsx     ← Per-category bars
│   │   │   ├── expenses/
│   │   │   │   ├── ExpenseTable.tsx          ← Sortable paginated table
│   │   │   │   ├── AddExpenseModal.tsx       ← Add form in modal
│   │   │   │   ├── EditExpenseModal.tsx      ← Edit form in modal
│   │   │   │   └── ExpenseFilters.tsx        ← Filter bar
│   │   │   └── ai/
│   │   │       ├── InsightCard.tsx           ← Single insight display
│   │   │       ├── AIChat.tsx                ← Chat panel
│   │   │       └── MonthlyReport.tsx         ← Narrative report display
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   ├── Insights.tsx
│   │   │   ├── Budgets.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/
│   │   │   ├── useExpenses.ts
│   │   │   ├── useBudgets.ts
│   │   │   └── useInsights.ts
│   │   ├── api/
│   │   │   ├── client.ts          ← Axios instance
│   │   │   ├── expenses.ts
│   │   │   ├── categories.ts
│   │   │   ├── budgets.ts
│   │   │   ├── analytics.ts
│   │   │   └── insights.ts
│   │   └── types/
│   │       └── index.ts           ← All TypeScript interfaces
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── data/
│   └── expenses.db                ← Auto-created on first run
├── diagrams/
│   └── architecture.excalidraw    ← System diagram
├── .env                           ← API keys (gitignored)
├── .gitignore
└── README.md
```

---

## 3. DATABASE SCHEMA

### Table: expenses
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| amount | FLOAT | NOT NULL, must be > 0 |
| description | TEXT | NOT NULL |
| category_id | INTEGER | FK → categories.id |
| merchant | TEXT | nullable |
| date | DATE | NOT NULL |
| is_recurring | BOOLEAN | DEFAULT FALSE |
| recurring_id | INTEGER | FK → recurring_rules.id, nullable |
| notes | TEXT | nullable |
| created_at | DATETIME | DEFAULT NOW |
| updated_at | DATETIME | DEFAULT NOW |

### Table: categories
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | NOT NULL UNIQUE |
| color | TEXT | NOT NULL (hex e.g. "#FF6B35") |
| icon | TEXT | NOT NULL (emoji e.g. "🍔") |
| created_at | DATETIME | DEFAULT NOW |

### Table: budgets
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| category_id | INTEGER | FK → categories.id |
| monthly_limit | FLOAT | NOT NULL, > 0 |
| month | INTEGER | NOT NULL (1–12) |
| year | INTEGER | NOT NULL |
| created_at | DATETIME | DEFAULT NOW |

### Table: recurring_rules
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | NOT NULL |
| amount | FLOAT | NOT NULL, > 0 |
| category_id | INTEGER | FK → categories.id |
| frequency | TEXT | NOT NULL: "daily" / "weekly" / "monthly" / "yearly" |
| next_due_date | DATE | NOT NULL |
| last_run_date | DATE | nullable |
| is_active | BOOLEAN | DEFAULT TRUE |
| created_at | DATETIME | DEFAULT NOW |

### Table: ai_insights
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| type | TEXT | "outlier" / "spike" / "summary" / "recommendation" |
| title | TEXT | NOT NULL |
| content | TEXT | NOT NULL |
| severity | TEXT | "info" / "warning" / "critical" |
| month | INTEGER | nullable |
| year | INTEGER | nullable |
| is_dismissed | BOOLEAN | DEFAULT FALSE |
| created_at | DATETIME | DEFAULT NOW |

---

## 4. API ENDPOINTS

### /api/expenses
```
GET    /api/expenses              Query params: month, year, category_id, search, limit(50), offset(0)
POST   /api/expenses              Body: {amount, description, category_id, merchant, date, is_recurring, recurring_id, notes}
GET    /api/expenses/{id}         Returns single expense
PUT    /api/expenses/{id}         Updates any field
DELETE /api/expenses/{id}         Deletes expense
POST   /api/expenses/bulk-import  Multipart file upload (CSV)
```

### /api/categories
```
GET    /api/categories            Returns all categories
POST   /api/categories            Body: {name, color, icon}
PUT    /api/categories/{id}       Updates name/color/icon
DELETE /api/categories/{id}       Query param: reassign_to_id (required if expenses exist)
```

### /api/budgets
```
GET    /api/budgets               Query params: month, year
POST   /api/budgets               Body: {category_id, monthly_limit, month, year}
PUT    /api/budgets/{id}          Updates monthly_limit
GET    /api/budgets/status        Returns budget + actual spend + % used for current month
```

### /api/recurring
```
GET    /api/recurring             Returns all recurring rules
POST   /api/recurring             Creates new rule
PUT    /api/recurring/{id}        Updates rule (amount, frequency, next_due_date, is_active)
DELETE /api/recurring/{id}        Deletes rule
POST   /api/recurring/run         Manually triggers recurring check → creates due expenses
```

### /api/insights
```
GET    /api/insights              Query params: month, year, type, limit
POST   /api/insights/generate     Body: {month, year} → calls Claude, stores results
POST   /api/insights/chat         Body: {question} → returns AI text response
GET    /api/insights/spikes       Query params: month, year
GET    /api/insights/monthly-report  Returns AI narrative for current month
DELETE /api/insights/{id}/dismiss Updates is_dismissed = True
```

### /api/analytics
```
GET    /api/analytics/summary            month, year params → KPI totals
GET    /api/analytics/trends             Returns 6 months of {month, year, total}
GET    /api/analytics/category-breakdown month, year → [{category, amount, percentage}]
GET    /api/analytics/merchant-breakdown month, year → [{merchant, amount, count}]
GET    /api/analytics/daily-heatmap      month, year → [{date, amount}] for heatmap
GET    /api/analytics/mom-comparison     month, year → per-category % change vs prior month
```

### /api/exports
```
GET    /api/exports/csv     Query params: month, year, category_id → StreamingResponse
GET    /api/exports/excel   Query params: month, year → .xlsx with 3 sheets
```

---

## 5. FRONTEND ARCHITECTURE

### Dashboard (/) — data sources + layout
**Fetches from:** /analytics/summary, /analytics/trends, /analytics/category-breakdown, /budgets/status, /expenses?limit=10, /insights?limit=3

**Layout:**
```
[ KPI Card ]  [ KPI Card ]  [ KPI Card ]  [ KPI Card ]
[   SpendingTrendChart (60%)   ]  [ CategoryDonutChart (40%) ]
[          BudgetProgressBar (per category)                  ]
[ RecentTransactions (60%) ]  [ AI Insight Cards (40%)       ]
                    [+ Floating Add Button]
```

**KPI Cards:**
- Total This Month (with MoM % arrow badge — green down, red up)
- Budget Used % (green <70%, amber 70–90%, red >90%)
- Daily Average (total / days elapsed this month)
- Top Category (icon + name + amount)

### Transactions (/transactions)
**Layout:**
```
[ Filter Bar: date range | category | search | amount range | Clear ]
[ Add Expense ]  [ Import CSV ]  [ Export CSV ]  [ Export Excel ]
[ Sortable Table: Date | Merchant | Description | Category | Amount | Recurring | Actions ]
[ Pagination: 25 per page ]
```

**Modals:**
- AddExpenseModal: amount*, description*, category*, merchant, date* (default today), is_recurring toggle, if recurring → frequency dropdown, notes
- EditExpenseModal: same fields pre-filled
- DeleteConfirmDialog: "Delete this expense? This cannot be undone." with Cancel / Delete buttons

### Insights (/insights)
**Layout:**
```
[ Generate Report Button ]  [ Last Generated: X mins ago ]
[ Monthly Narrative Card — full-width AI text ]
[ Spending Spikes Grid — cards with severity color + dismiss button ]
[ Recommendations — 3 cards with $ savings estimate + Mark Done ]
[ AI Chat Panel — right side or bottom drawer ]
[ Top Merchants Table ]
```

### Budgets (/budgets)
**Layout:**
```
[ Month/Year selector ]
[ Budget Status Grid — one card per category ]
  Each card: icon + name | limit (inline editable) | spent | circular progress | status badge | projected month-end
[ Recurring Expense Manager — table with toggle, edit, delete ]
[ Month Summary bar: Budgeted | Spent | Remaining | Net ]
```

### Settings (/settings)
**Sections:**
- Category Manager: list with color swatch + emoji + edit/delete
- Data Management: Export All, Import CSV, Backup DB
- Appearance: Dark/Light toggle, currency symbol input
- About: version, tech stack credits

---

## 6. AI INTEGRATION SPEC

### Claude System Prompt (paste into ai_service.py)
```
You are a personal finance analyst AI embedded in an expense tracker app.
You receive structured expense data and must return ONLY valid JSON — no preamble, 
no explanation, no markdown code blocks. Just the raw JSON object.

Analyze the data and return this exact structure:
{
  "summary": "2-3 sentence narrative of this month's spending behavior",
  "spikes": [
    {
      "category": "category name",
      "current_spend": 0.0,
      "rolling_avg": 0.0,
      "percentage_above": 0.0,
      "severity": "warning|critical",
      "explanation": "one sentence plain English explanation"
    }
  ],
  "recommendations": [
    {
      "title": "short action title",
      "description": "specific actionable advice with $ estimate",
      "estimated_savings": 0.0
    }
  ],
  "insights": [
    {
      "type": "outlier|spike|summary|recommendation",
      "title": "short title",
      "content": "2-3 sentence insight",
      "severity": "info|warning|critical"
    }
  ]
}

Rules:
- Be specific with numbers and percentages
- Be direct, not preachy
- If no spikes exist, return empty array
- severity "critical" = 60%+ above average, "warning" = 30–60% above
```

### Spike Detection Algorithm (analytics_service.py)
```
For each category:
  1. Get current month's total spend for that category
  2. Fetch the 3 previous months' totals for same category
  3. Calculate rolling_avg = sum(prev_3_months) / 3
  4. If rolling_avg == 0: skip (not enough history)
  5. percentage_above = ((current - rolling_avg) / rolling_avg) * 100
  6. If percentage_above >= 60: severity = "critical"
  7. If percentage_above >= 30: severity = "warning"
  8. Also: flag any single expense > 2x the category's average single transaction
```

### AI Chat Context Builder (ai_service.py)
```
Each /insights/chat call sends:
- System: "You are a personal finance assistant. Answer questions about the user's 
  expenses based on the data provided. Be concise and specific."
- User message includes:
  1. Last 3 months: [{month, year, category, total}]
  2. Current month transactions: [{date, description, category, amount, merchant}]
  3. Budget limits: [{category, limit, spent}]
  4. The user's question
```

---

## 7. PHASES — BUILD ORDER

```
Phase 0 │ Setup + Structure         │ Day 1      │ Folders, venv, React app, git init
Phase 1 │ Backend Foundation        │ Days 2–3   │ DB, models, CRUD for expenses + categories
Phase 2 │ Frontend Shell            │ Days 4–5   │ Routing, layout, API client, type definitions
Phase 3 │ Core Features             │ Days 6–8   │ Dashboard charts, Transactions table, Budgets page
Phase 4 │ AI Layer                  │ Days 9–10  │ Insights engine, spike detection, AI chat
Phase 5 │ Exports + Recurring       │ Days 11–12 │ CSV/Excel export, recurring engine, Settings page
Phase 6 │ Polish + README + GitHub  │ Day 13     │ Skeletons, empty states, keyboard shortcuts, README
```

---

## 8. COPILOT PROMPTS — READY TO PASTE

> Open VSCode. Press **Ctrl+Alt+I** to open Copilot Chat.  
> For file creation: open Copilot **Edits** (Ctrl+Shift+I), attach relevant files, paste the prompt.

---

### PHASE 0 — SETUP

**PROMPT 0A — Create project structure (paste in terminal, not Copilot):**
```
Open PowerShell in your Desktop folder and run:

mkdir expense-tracker
cd expense-tracker
mkdir backend backend\routers backend\services data diagrams
mkdir frontend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install fastapi==0.111.0 sqlmodel==0.0.18 uvicorn==0.29.0 anthropic==0.25.0 pandas==2.2.0 openpyxl==3.1.2 python-dotenv==1.0.0 schedule==1.2.1
pip freeze > requirements.txt
cd ..\frontend
npm create vite@latest . -- --template react-ts
npm install
npm install tailwindcss@3.4.0 postcss autoprefixer axios react-router-dom recharts react-hot-toast date-fns lucide-react
npx tailwindcss init -p
cd ..
git init
```

**PROMPT 0B — .gitignore (paste into Copilot Chat):**
```
Create a .gitignore file at the root of the expense-tracker project that excludes:
.env, .venv, __pycache__, *.pyc, node_modules, dist, data/*.db, .DS_Store
```

**PROMPT 0C — .env file:**
```
Create a .env file at the root with:
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=../data/expenses.db
```

---

### PHASE 1 — BACKEND FOUNDATION

**PROMPT 1A — database.py:**
```
You are building an expense tracker backend with FastAPI and SQLModel.

Create backend/database.py that:
1. Imports SQLModel, create_engine, Session
2. Loads DATABASE_URL from .env using python-dotenv (default: ../data/expenses.db)
3. Creates a SQLite engine with connect_args={"check_same_thread": False}
4. Defines a get_session() generator function as a FastAPI dependency using yield
5. Defines create_db_and_tables() that calls SQLModel.metadata.create_all(engine)
```

**PROMPT 1B — models.py:**
```
You are building an expense tracker backend with FastAPI and SQLModel.

Create backend/models.py with SQLModel table models for these 5 tables:

Table: Category (Table=True)
- id: Optional[int] = Field(default=None, primary_key=True)
- name: str (unique=True, index=True)
- color: str (hex color, e.g. "#FF6B35")
- icon: str (emoji)
- created_at: datetime = Field(default_factory=datetime.utcnow)
- Relationship: expenses → list["Expense"]

Table: RecurringRule (Table=True)
- id: Optional[int] = Field(default=None, primary_key=True)
- name: str
- amount: float = Field(gt=0)
- category_id: Optional[int] = Field(foreign_key="category.id")
- frequency: str (Literal["daily", "weekly", "monthly", "yearly"])
- next_due_date: date
- last_run_date: Optional[date] = None
- is_active: bool = True
- created_at: datetime = Field(default_factory=datetime.utcnow)

Table: Expense (Table=True)
- id: Optional[int] = Field(default=None, primary_key=True)
- amount: float = Field(gt=0)
- description: str
- category_id: Optional[int] = Field(foreign_key="category.id")
- merchant: Optional[str] = None
- date: date
- is_recurring: bool = False
- recurring_id: Optional[int] = Field(default=None, foreign_key="recurringrule.id")
- notes: Optional[str] = None
- created_at: datetime = Field(default_factory=datetime.utcnow)
- updated_at: datetime = Field(default_factory=datetime.utcnow)
- Relationship: category → Optional[Category]

Table: Budget (Table=True)
- id: Optional[int] = Field(default=None, primary_key=True)
- category_id: int = Field(foreign_key="category.id")
- monthly_limit: float = Field(gt=0)
- month: int = Field(ge=1, le=12)
- year: int
- created_at: datetime = Field(default_factory=datetime.utcnow)
- Unique constraint on (category_id, month, year)

Table: AIInsight (Table=True)
- id: Optional[int] = Field(default=None, primary_key=True)
- type: str (Literal["outlier", "spike", "summary", "recommendation"])
- title: str
- content: str
- severity: Optional[str] = "info" (Literal["info", "warning", "critical"])
- month: Optional[int] = None
- year: Optional[int] = None
- is_dismissed: bool = False
- created_at: datetime = Field(default_factory=datetime.utcnow)

Also create non-table read/create schemas:
- CategoryCreate, CategoryRead
- ExpenseCreate, ExpenseRead (include category: Optional[CategoryRead])
- BudgetCreate, BudgetRead
- RecurringRuleCreate, RecurringRuleRead
- AIInsightRead
```

**PROMPT 1C — main.py:**
```
You are building an expense tracker with FastAPI.

Create backend/main.py that:
1. Creates a FastAPI app with title="ExpenseIQ API", version="1.0.0"
2. Adds CORS middleware allowing origins: ["http://localhost:5173"], all methods, all headers
3. Imports and includes routers from routers/expenses, categories, budgets, recurring, insights, analytics, exports — all with prefix="/api"
4. On startup (lifespan event): calls create_db_and_tables(), then seeds default categories if categories table is empty
5. Default categories to seed:
   [("Food", "#FF6B35", "🍔"), ("Transport", "#4ECDC4", "🚗"), ("Shopping", "#45B7D1", "🛍️"),
    ("Entertainment", "#96CEB4", "🎬"), ("Health", "#FFEAA7", "💊"), ("Bills", "#DDA0DD", "📋"),
    ("Travel", "#98D8C8", "✈️"), ("Education", "#F7DC6F", "📚"), ("Personal", "#BB8FCE", "💈"), ("Other", "#AED6F1", "📦")]
6. GET /health returns {"status": "ok", "version": "1.0.0"}
7. App runs on port 8000 when executed directly with uvicorn
```

**PROMPT 1D — routers/expenses.py:**
```
You are building an expense tracker. backend/models.py has Expense, ExpenseCreate, ExpenseRead.
backend/database.py has get_session().

Create backend/routers/expenses.py with an APIRouter(prefix="/expenses", tags=["expenses"]):

GET / 
- Query params: month: Optional[int], year: Optional[int], category_id: Optional[int], 
  search: Optional[str], limit: int = 50, offset: int = 0
- Filter by month/year if provided (use extract from sqlalchemy)
- Filter by category_id if provided
- Search in description and merchant fields if search string provided
- Return List[ExpenseRead] with category relationship loaded

POST /
- Body: ExpenseCreate
- Creates and returns ExpenseRead

GET /{id}
- Returns ExpenseRead or 404

PUT /{id}  
- Body: ExpenseCreate (all fields optional, use model_dump exclude_unset)
- Updates updated_at to now
- Returns ExpenseRead or 404

DELETE /{id}
- Deletes and returns {"message": "Expense deleted"}

POST /bulk-import
- Accepts UploadFile (CSV)
- Expected CSV columns: amount, description, category, merchant, date, notes
- Matches category by name (case-insensitive), uses "Other" category if not found
- date format: YYYY-MM-DD or MM/DD/YYYY
- Skips rows with missing amount or description
- Returns {"imported": count, "skipped": count}
```

**PROMPT 1E — routers/categories.py:**
```
You are building an expense tracker. backend/models.py has Category, CategoryCreate, CategoryRead and Expense.

Create backend/routers/categories.py with APIRouter(prefix="/categories", tags=["categories"]):

GET /
- Returns all categories ordered by name: List[CategoryRead]

POST /
- Body: CategoryCreate
- Returns CategoryRead or 400 if name already exists

PUT /{id}
- Body: CategoryCreate (all optional)
- Returns CategoryRead or 404

DELETE /{id}
- Query param: reassign_to_id: Optional[int]
- If category has expenses AND reassign_to_id not provided: return 400 with message "Category has expenses. Provide reassign_to_id to reassign them."
- If reassign_to_id provided: update all expenses with this category_id to use reassign_to_id
- Then delete and return {"message": "Category deleted"}
- Do not allow deleting last category
```

---

### PHASE 2 — FRONTEND SHELL

**PROMPT 2A — types/index.ts:**
```
Create frontend/src/types/index.ts with TypeScript interfaces:

export interface Category {
  id: number; name: string; color: string; icon: string; created_at: string;
}
export interface Expense {
  id: number; amount: number; description: string; category_id: number;
  category?: Category; merchant?: string; date: string; is_recurring: boolean;
  recurring_id?: number; notes?: string; created_at: string; updated_at: string;
}
export interface Budget {
  id: number; category_id: number; monthly_limit: number; month: number; year: number;
}
export interface BudgetStatus {
  category: Category; monthly_limit: number; spent: number; percentage: number;
  remaining: number; projected_month_end: number; status: "on_track" | "warning" | "over_budget";
}
export interface RecurringRule {
  id: number; name: string; amount: number; category_id: number; category?: Category;
  frequency: "daily" | "weekly" | "monthly" | "yearly"; next_due_date: string;
  last_run_date?: string; is_active: boolean;
}
export interface AIInsight {
  id: number; type: "outlier" | "spike" | "summary" | "recommendation";
  title: string; content: string; severity: "info" | "warning" | "critical";
  month?: number; year?: number; is_dismissed: boolean; created_at: string;
}
export interface AnalyticsSummary {
  total_this_month: number; mom_change_percent: number; budget_used_percent: number;
  daily_average: number; top_category: { name: string; icon: string; amount: number } | null;
}
export interface SpendingTrend { month: number; year: number; total: number; label: string; }
export interface CategoryBreakdown { category: Category; amount: number; percentage: number; }
export interface SpikeResult {
  category: string; current_spend: number; rolling_avg: number;
  percentage_above: number; severity: "warning" | "critical"; explanation: string;
}
export interface MerchantBreakdown { merchant: string; amount: number; count: number; }
```

**PROMPT 2B — api/client.ts:**
```
Create frontend/src/api/client.ts:

1. Create an Axios instance with baseURL: "http://localhost:8000/api"
2. Add a response interceptor: on error, use react-hot-toast to show toast.error(error.response?.data?.detail || "Something went wrong")
3. Export the instance as default

Create frontend/src/api/expenses.ts that exports:
- getExpenses(params: {month?,year?,category_id?,search?,limit?,offset?}) → Promise<Expense[]>
- createExpense(data: Omit<Expense, 'id'|'created_at'|'updated_at'|'category'>) → Promise<Expense>
- updateExpense(id, data) → Promise<Expense>
- deleteExpense(id) → Promise<void>
- bulkImport(file: File) → Promise<{imported:number, skipped:number}>

Create frontend/src/api/analytics.ts that exports:
- getSummary(month, year) → Promise<AnalyticsSummary>
- getTrends() → Promise<SpendingTrend[]>
- getCategoryBreakdown(month, year) → Promise<CategoryBreakdown[]>
- getMerchantBreakdown(month, year) → Promise<MerchantBreakdown[]>

Create frontend/src/api/categories.ts: full CRUD matching backend endpoints
Create frontend/src/api/budgets.ts: getBudgets, getBudgetStatus, createBudget, updateBudget
Create frontend/src/api/insights.ts: getInsights, generateInsights, chatWithAI, getSpikes, dismissInsight
```

**PROMPT 2C — Layout + Routing:**
```
You are building ExpenseIQ, a dark-themed expense tracker.

Create frontend/src/App.tsx with React Router v6 routes:
/ → Dashboard, /transactions → Transactions, /insights → Insights, /budgets → Budgets, /settings → Settings
All routes wrapped in a Layout component.

Create frontend/src/components/layout/Layout.tsx:
- Fixed left sidebar (240px wide), scrollable main content on the right
- Dark background: sidebar bg-gray-950, main bg-gray-900
- Renders <Sidebar /> on left, <Header /> on top of main, children below

Create frontend/src/components/layout/Sidebar.tsx:
- "💰 ExpenseIQ" branding at top (white text, amber accent on the emoji)
- Nav links using react-router-dom NavLink:
  Dashboard (LayoutDashboard icon), Transactions (Receipt), Insights (Brain), Budgets (Target), Settings (Settings2)
- Active link: bg-amber-500/10 text-amber-400 border-r-2 border-amber-400
- Inactive: text-gray-400 hover:text-white hover:bg-gray-800
- All icons from lucide-react, size 18px
- "Powered by Claude AI" credit at bottom in small gray text

Create frontend/src/components/layout/Header.tsx:
- Shows current page title (derive from pathname)
- Shows current date on the right: "Friday, April 24, 2026"
- Dark bg-gray-950, border-b border-gray-800, h-16, px-6
```

---

### PHASE 3 — CORE FEATURES

**PROMPT 3A — Dashboard page:**
```
You are building ExpenseIQ. All types are in types/index.ts. API functions in api/*.ts.

Create frontend/src/pages/Dashboard.tsx:

Fetch on mount (current month/year):
- getSummary(month, year) for KPI cards
- getTrends() for line chart
- getCategoryBreakdown(month, year) for donut chart
- getBudgetStatus(month, year) from /api/budgets/status
- getExpenses({month, year, limit: 10}) for recent table
- getInsights({limit: 3}) for insight cards

SECTION 1 — KPI Row (4 cards, side by side, full width):
  Card 1: "Total This Month" — total_this_month formatted as currency + MoM badge (green arrow down if positive saving, red arrow up if overspending)
  Card 2: "Budget Used" — budget_used_percent as large % number, color: text-green-400 (<70), text-amber-400 (70-90), text-red-400 (>90)
  Card 3: "Daily Average" — daily_average formatted as currency
  Card 4: "Top Category" — top_category.icon + name + amount

SECTION 2 — Two columns:
  Left (60%): SpendingTrendChart component
  Right (40%): CategoryDonutChart component

SECTION 3 — Full width: BudgetProgressBar component (receives budgetStatus array)

SECTION 4 — Two columns:
  Left (60%): Recent Transactions table (date, merchant|description, category badge, amount)
  Right (40%): 3 AI InsightCard components

Floating "+" button bottom-right → opens AddExpenseModal on click

Use loading skeletons (gray animate-pulse divs matching card shapes) while fetching.
All cards: bg-gray-800 rounded-xl p-5 border border-gray-700
Dark theme throughout, amber accent color (#F59E0B).
```

**PROMPT 3B — Charts:**
```
You are building ExpenseIQ dark theme charts using Recharts.

Create frontend/src/components/charts/SpendingTrendChart.tsx:
- Receives: data: SpendingTrend[]
- Recharts AreaChart with gradient fill (amber to transparent)
- X axis: month labels, Y axis: $ amounts formatted
- Custom dark tooltip (bg-gray-800 border-gray-600 text-white)
- Title: "Spending Trend" with subtitle "Last 6 months"
- Height: 250px

Create frontend/src/components/charts/CategoryDonutChart.tsx:
- Receives: data: CategoryBreakdown[]
- Recharts PieChart (donut, innerRadius=60, outerRadius=90)
- Each slice colored by category.color
- Center label showing total amount
- Legend below with category icon + name + amount
- Custom tooltip showing category + amount + percentage

Create frontend/src/components/charts/BudgetProgressBar.tsx:
- Receives: data: BudgetStatus[]
- One row per category: icon + name | progress bar | spent/limit | status badge
- Progress bar: green (<70%), amber (70-90%), red (>90%), using div with percentage width
- Status badge: "On Track" (green), "Warning" (amber), "Over Budget" (red)
```

**PROMPT 3C — Transactions page:**
```
You are building ExpenseIQ. All types in types/index.ts.

Create frontend/src/pages/Transactions.tsx:

STATE: filters (month, year, category_id, search, minAmount, maxAmount), 
       page (current page), showAddModal, showEditModal, selectedExpense

FILTER BAR:
- Month/Year selector (dropdowns)
- Category dropdown (populated from getCategories())  
- Search input with 300ms debounce (use useCallback + setTimeout)
- "Clear Filters" button
- Total count display: "Showing X expenses"

ACTION BAR (below filters):
- "Add Expense" button (opens AddExpenseModal)
- "Import CSV" button (triggers file input click → calls bulkImport)
- "Export CSV" button → window.open('/api/exports/csv?month=...&year=...')
- "Export Excel" button → window.open('/api/exports/excel?month=...&year=...')

TABLE (25 rows per page, sortable columns):
Columns: Date | Merchant | Description | Category | Amount | ↻ (if recurring) | Edit icon | Delete icon
- Date: formatted as "Apr 24" or "Apr 24, 2026" 
- Category: colored badge using category.color + category.icon
- Amount: right-aligned, formatted currency
- Recurring icon: lucide-react RefreshCw icon, amber color, shown only if is_recurring=true
- Edit: Pencil icon → opens EditExpenseModal with selectedExpense
- Delete: Trash2 icon → shows inline confirmation row before deleting

PAGINATION: Previous | Page X of Y | Next buttons

AddExpenseModal and EditExpenseModal:
- Modal overlay with backdrop blur
- Fields: Amount*, Description*, Category* (dropdown), Merchant, Date* (input type=date), Is Recurring (toggle switch), Frequency (shown if recurring), Notes (textarea)
- Save / Cancel buttons
- On save: calls createExpense or updateExpense, refreshes list, closes modal, shows success toast
```

**PROMPT 3D — Budgets page and routers:**
```
Create backend/routers/budgets.py with:
- GET /api/budgets?month=&year= → list budgets for that period
- POST /api/budgets → create budget (upsert: if category+month+year exists, update it)
- PUT /api/budgets/{id} → update monthly_limit
- GET /api/budgets/status?month=&year= → for each category with a budget:
  return {category, monthly_limit, spent (sum of expenses for that category+month+year), 
  percentage (spent/limit*100), remaining (limit-spent), 
  projected_month_end (spent / days_elapsed * days_in_month),
  status: "on_track"|"warning"|"over_budget"}

Create frontend/src/pages/Budgets.tsx:
- Month/Year selector at top
- Budget Status Grid: cards (2-3 per row) for each category that has a budget
  Each card: colored left border (category.color), category icon+name, 
  circular progress ring (CSS only, not Recharts), budget amount (click to edit inline),
  spent amount, X days remaining, "Projected: $X" text, status badge
- Recurring Expense Manager section below grid:
  Table: Name | Amount | Category | Frequency | Next Due | Active toggle | Edit | Delete
  "Add Recurring" button → opens AddRecurringModal
  Modal fields: name, amount, category (dropdown), frequency (dropdown), start date
- Summary bar at bottom: Total Budgeted | Total Spent | Remaining | Over/Under badge
```

---

### PHASE 4 — AI LAYER

**PROMPT 4A — ai_service.py:**
```
You are building an expense tracker with FastAPI and Claude AI.
Load ANTHROPIC_API_KEY from .env using python-dotenv.

Create backend/services/ai_service.py with these async functions:

1. async def generate_monthly_insights(month: int, year: int, db: Session) -> list[AIInsight]:
   - Query all expenses for the given month/year with categories joined
   - Group totals by category
   - For each category, get totals from the 3 previous months to compute rolling average
   - Build a data dict:
     {
       "month": month, "year": year,
       "categories": [{"name": ..., "icon": ..., "current_total": ..., "rolling_avg_3mo": ...}],
       "total_spend": ..., "transaction_count": ..., "largest_expense": {"amount": ..., "description": ...},
       "top_merchant": {"name": ..., "total": ...}
     }
   - Call claude-sonnet-4-20250514 with the system prompt below and this data as user message
   - Parse the JSON response (strip any code fences first)
   - Delete existing non-dismissed insights for same month/year
   - Create and save new AIInsight records from spikes + insights arrays in the response
   - Return the saved insights

   System prompt (use this exactly):
   [PASTE THE SYSTEM PROMPT FROM SECTION 6 OF THIS BLUEPRINT]

2. async def chat_with_finances(question: str, db: Session) -> str:
   - Get current month/year
   - Get last 3 months category totals as [{month, year, category, total}]
   - Get current month transactions as [{date, amount, description, category, merchant}] (max 50)
   - Get budget status for current month
   - Call Claude with:
     system: "You are a personal finance assistant answering questions based on provided expense data. Be concise and specific with numbers."
     user: f"Expense data:\n{json.dumps(context)}\n\nQuestion: {question}"
   - Return the text response

3. def detect_spikes(month: int, year: int, db: Session) -> list[dict]:
   - Implement the spike detection algorithm from Section 6
   - Return list of dicts with: category, current_spend, rolling_avg, percentage_above, severity, explanation
   - "explanation" should be a plain-language string like "Food spending is 45% above your 3-month average of $320"
```

**PROMPT 4B — routers/insights.py:**
```
You are building an expense tracker. backend/services/ai_service.py has generate_monthly_insights, chat_with_finances, detect_spikes.

Create backend/routers/insights.py with APIRouter(prefix="/insights", tags=["insights"]):

GET /
- Query params: month: Optional[int], year: Optional[int], type: Optional[str], limit: int = 20
- Returns stored non-dismissed insights, most recent first

POST /generate
- Body: {"month": int, "year": int}
- Calls generate_monthly_insights, returns list of AIInsight

POST /chat
- Body: {"question": str}
- Calls chat_with_finances, returns {"response": str}

GET /spikes
- Query params: month: Optional[int] (default current), year: Optional[int] (default current)
- Calls detect_spikes, returns list of spike dicts

GET /monthly-report
- Query params: month, year
- Filters insights where type="summary" for that month/year
- Returns the most recent summary insight content, or generates one if none exists

DELETE /{id}/dismiss
- Sets is_dismissed=True on the insight
- Returns {"message": "Insight dismissed"}
```

**PROMPT 4C — Insights page:**
```
You are building ExpenseIQ. Create frontend/src/pages/Insights.tsx:

STATE: currentMonth, currentYear, report (AIInsight|null), spikes (SpikeResult[]), 
       insights (AIInsight[]), chatMessages ([{role, content}]), chatInput, isGenerating, isChatLoading

SECTION 1 — Top bar:
"Generate AI Report" button (amber, with Sparkles lucide icon) → calls generateInsights({month, year}) → sets isGenerating=true, shows spinner
"Last generated: X" timestamp if insights exist

SECTION 2 — Monthly Narrative card (full width):
- bg-gray-800 card with purple/indigo left border
- Brain icon + "Monthly Summary" title
- Displays report.content as formatted text
- If no report: shows "Click Generate AI Report to analyze your finances" placeholder

SECTION 3 — Spending Spikes (grid of cards):
For each spike (from getSpikes()):
- Card with left border color: amber for "warning", red for "critical"
- Category name + percentage badge ("↑ 45% above average")
- spike.explanation text
- "Dismiss" button (X icon, gray, small)

SECTION 4 — Recommendations (3 cards in a row):
Filter insights where type="recommendation", show top 3
- bg-gray-800 card with green left border
- Lightbulb icon + insight.title
- insight.content text
- If estimated_savings parseable: "💰 Save up to $X/month" badge

SECTION 5 — AI Chat (full width panel at bottom):
- Chat bubble UI: user messages right-aligned (amber bg), AI messages left-aligned (gray bg)
- Input bar at bottom with Send button
- On send: adds user message, calls chatWithAI(question), adds AI response
- Example prompts shown when chat is empty: 3 clickable chips
  "How much did I spend on food last month?" | "What's my biggest recurring expense?" | "Am I on track with my budget?"

SECTION 6 — Top Merchants table (below spikes):
Calls getMerchantBreakdown(month, year) → table: Rank | Merchant | Total | # Transactions
```

---

### PHASE 5 — EXPORTS + RECURRING + SETTINGS

**PROMPT 5A — export_service.py:**
```
Create backend/services/export_service.py with:

1. def export_to_csv(expenses: list, categories: list) -> io.StringIO:
   - Use pandas DataFrame
   - Columns: Date, Merchant, Description, Category, Amount, Notes, Is Recurring
   - Map category_id to category name using the categories list
   - Return StringIO object with CSV content

2. def export_to_excel(expenses: list, budgets: list, categories: list, month: int, year: int) -> io.BytesIO:
   - Use openpyxl Workbook
   - Sheet 1 "Transactions": styled table with headers (bold, bg=#1F4E79, white text)
     Columns: Date, Merchant, Description, Category, Amount, Notes
     Alternating row colors: white and #F2F9FF
   - Sheet 2 "Summary": category totals table
     Columns: Category, Total Spent, % of Total, Budget Limit, Status (Over/Under)
   - Sheet 3 "Overview": 
     Title "ExpenseIQ Monthly Report — [Month Year]"
     Total spend, number of transactions, avg per day, top category
   - Return BytesIO

Create backend/routers/exports.py with:
- GET /csv: query params month, year, category_id → calls export_to_csv → returns StreamingResponse with content-disposition: attachment; filename="expenses_YYYY_MM.csv"
- GET /excel: query params month, year → calls export_to_excel → returns StreamingResponse with filename="expenseiq_report_YYYY_MM.xlsx"
```

**PROMPT 5B — recurring_service.py:**
```
Create backend/services/recurring_service.py with:

def process_recurring_expenses(db: Session) -> int:
  """Check all active recurring rules. For each rule where next_due_date <= today:
  1. Create a new Expense record:
     amount=rule.amount, description=rule.name, category_id=rule.category_id,
     date=rule.next_due_date, is_recurring=True, recurring_id=rule.id
  2. Update rule.last_run_date = rule.next_due_date
  3. Advance rule.next_due_date based on frequency:
     daily: +1 day, weekly: +7 days, monthly: +1 month, yearly: +1 year
  4. If new next_due_date is still <= today, keep advancing until it's in the future
  5. Save changes
  Returns count of expenses created"""

Call this function from main.py on startup lifespan event, AFTER create_db_and_tables().
Also call it from POST /api/recurring/run endpoint.
```

**PROMPT 5C — Settings page:**
```
Create frontend/src/pages/Settings.tsx:

SECTION 1 — Category Manager:
- Fetch all categories on mount
- Render each as a row: colored dot (category.color) | emoji | name | Edit button | Delete button
- Edit opens inline edit form (name input, color input type=color, emoji input)
- Delete: if category has expenses, shows a select dropdown "Reassign expenses to:" before confirming
- "Add Category" form at bottom: name, color picker, emoji input, Add button

SECTION 2 — Data Management:
- "Export All Data" button → GET /api/exports/csv (no month filter, all time)
- "Export Excel Report" button → GET /api/exports/excel (current month)
- "Import CSV" button → file input, calls bulkImport, shows result toast
- Last backup timestamp display

SECTION 3 — Preferences:
- Currency symbol input (default "$"), saves to localStorage
- Date format toggle: MM/DD/YYYY vs DD/MM/YYYY

SECTION 4 — About:
- "ExpenseIQ v1.0.0"
- Stack: React 18 · FastAPI · SQLite · Claude AI
- GitHub link placeholder
```

---

### PHASE 6 — POLISH + README + GITHUB

**PROMPT 6A — Polish:**
```
Add the following improvements to the ExpenseIQ frontend:

1. LOADING SKELETONS: In Dashboard.tsx, while data is loading, show skeleton placeholders:
   - KPI cards: 4 gray animate-pulse rounded-xl divs (h-28)
   - Charts: 2 gray animate-pulse rounded-xl divs
   - Table rows: 10 thin gray animate-pulse divs

2. EMPTY STATES: When expenses list is empty, show:
   - Large emoji (📭) centered
   - "No expenses yet" heading
   - "Add your first expense to get started" subtext
   - "Add Expense" button (amber)

3. KEYBOARD SHORTCUTS (add to App.tsx useEffect):
   - 'n' key (not in input) → opens AddExpenseModal
   - 'Escape' → closes any open modal
   - '/' key (not in input) → focuses the search input on Transactions page

4. RESPONSIVE SIDEBAR: At window width < 768px:
   - Sidebar collapses to 56px wide, showing only icons
   - "ExpenseIQ" text hidden
   - Nav labels hidden
   - Hover shows label in tooltip

5. NUMBER FORMATTING: Create a utility function formatCurrency(amount: number, symbol = "$"): string
   that returns "$1,234.56" format. Use throughout the app.

6. CHART TOOLTIPS: All Recharts charts should use a custom dark tooltip component:
   bg-gray-800, border border-gray-700, rounded-lg, p-3, text-white text-sm
```

**PROMPT 6B — README.md (paste into Copilot, ask it to create the file):**
```
Generate a professional README.md for ExpenseIQ at the project root.

Include these sections:
1. Title: "# 💰 ExpenseIQ" with tagline "A powerful, AI-driven personal expense tracker"
2. Badges row: Python 3.11 | FastAPI | React 18 | TypeScript | SQLite | Powered by Claude AI
   Use shields.io badge format with flat style, dark background colors
3. ## Features — use emoji bullet points covering all features from this blueprint
4. ## Tech Stack — two-column table: Backend and Frontend
5. ## Getting Started — Prerequisites + Installation steps (separate for backend and frontend)
6. ## Running the App:
   Terminal 1 (backend): cd backend && .venv\Scripts\activate && uvicorn main:app --reload
   Terminal 2 (frontend): cd frontend && npm run dev
   Then open: http://localhost:5173
7. ## Environment Variables — table with ANTHROPIC_API_KEY and DATABASE_URL
8. ## Project Structure — the exact folder tree from this blueprint
9. ## API Documentation — link to http://localhost:8000/docs (FastAPI auto-docs)
10. ## License: MIT
```

**PROMPT 6C — GitHub Setup (run in terminal):**
```
cd expense-tracker
git add .
git commit -m "feat: initial ExpenseIQ implementation"

Then:
1. Go to github.com → New Repository
2. Name it: expenseiq
3. Description: "AI-powered personal expense tracker built with React, FastAPI, SQLite, and Claude AI"
4. Set to Public
5. Do NOT initialize with README (you already have one)
6. Copy the remote URL and run:
   git remote add origin https://github.com/YOUR_USERNAME/expenseiq.git
   git branch -M main
   git push -u origin main
```

---

## 9. ENVIRONMENT SETUP

### One-Time Setup Checklist
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] VSCode installed with GitHub Copilot extension
- [ ] GitHub Copilot Chat extension (Ctrl+Alt+I)
- [ ] draw.io VSCode extension: `hediet.vscode-drawio`
- [ ] Anthropic API key from console.anthropic.com
- [ ] Git installed + GitHub account

### Running the App (every session)
```
Terminal 1 — Backend:
cd C:\Users\YourName\Desktop\expense-tracker\backend
.venv\Scripts\activate
uvicorn main:app --reload --port 8000

Terminal 2 — Frontend:
cd C:\Users\YourName\Desktop\expense-tracker\frontend
npm run dev
```

Open browser: http://localhost:5173  
API docs: http://localhost:8000/docs

---

*ExpenseIQ Blueprint v1.0 — Built for GitHub Copilot handoff*
