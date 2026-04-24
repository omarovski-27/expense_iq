import json
import re
from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from anthropic import Anthropic
from dotenv import load_dotenv
from sqlmodel import Session, select
from sqlalchemy import func

from database import get_session  # noqa — available for callers
from models import AIInsight, Budget, Category, Expense

load_dotenv()

_client = Anthropic()  # Reads ANTHROPIC_API_KEY from environment automatically

# ─────────────────────────────────────────────────────────────────────────────
# System prompt (Section 6 of blueprint)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a personal finance analyst AI embedded in an expense tracker app.
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
- severity "critical" = 60%+ above average, "warning" = 30–60% above"""


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _category_totals_for_month(month: int, year: int, db: Session) -> dict[int, float]:
    """Return {category_id: total_spent} for a given month/year."""
    month_str = f"{month:02d}"
    year_str = str(year)
    rows = db.exec(
        select(Expense.category_id, func.sum(Expense.amount).label("total"))
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
        .group_by(Expense.category_id)
    ).all()
    return {row[0]: float(row[1]) for row in rows if row[0] is not None}


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if Claude wraps its response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 1. generate_monthly_insights
# ─────────────────────────────────────────────────────────────────────────────

async def generate_monthly_insights(month: int, year: int, db: Session) -> list[AIInsight]:
    month_str = f"{month:02d}"
    year_str = str(year)

    # ── Fetch all expenses for this month ───────────────────────────────────
    expenses = db.exec(
        select(Expense)
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
    ).all()

    # ── Group totals by category ────────────────────────────────────────────
    current_totals: dict[int, float] = defaultdict(float)
    for exp in expenses:
        if exp.category_id:
            current_totals[exp.category_id] += exp.amount

    # ── Fetch all categories ────────────────────────────────────────────────
    categories = {c.id: c for c in db.exec(select(Category)).all()}

    # ── Rolling average: 3 previous months ──────────────────────────────────
    base = date(year, month, 1)
    prev_months = [base - relativedelta(months=i) for i in range(1, 4)]

    rolling_totals: dict[int, list[float]] = defaultdict(list)
    for d in prev_months:
        totals = _category_totals_for_month(d.month, d.year, db)
        for cat_id, total in totals.items():
            rolling_totals[cat_id].append(total)

    def rolling_avg(cat_id: int) -> float:
        vals = rolling_totals.get(cat_id, [])
        return sum(vals) / 3 if vals else 0.0

    # ── Categories payload ───────────────────────────────────────────────────
    cat_payload = []
    for cat_id, total in current_totals.items():
        cat = categories.get(cat_id)
        if cat:
            cat_payload.append({
                "name": cat.name,
                "icon": cat.icon,
                "current_total": round(total, 2),
                "rolling_avg_3mo": round(rolling_avg(cat_id), 2),
            })

    # ── Largest expense ──────────────────────────────────────────────────────
    largest = max(expenses, key=lambda e: e.amount) if expenses else None
    largest_payload = (
        {"amount": largest.amount, "description": largest.description}
        if largest else {"amount": 0, "description": "N/A"}
    )

    # ── Top merchant ─────────────────────────────────────────────────────────
    merchant_totals: dict[str, float] = defaultdict(float)
    for exp in expenses:
        if exp.merchant:
            merchant_totals[exp.merchant] += exp.amount
    top_merchant_name = max(merchant_totals, key=merchant_totals.get) if merchant_totals else "N/A"
    top_merchant_total = merchant_totals.get(top_merchant_name, 0.0)

    # ── Build prompt payload ─────────────────────────────────────────────────
    data = {
        "month": month,
        "year": year,
        "categories": cat_payload,
        "total_spend": round(sum(e.amount for e in expenses), 2),
        "transaction_count": len(expenses),
        "largest_expense": largest_payload,
        "top_merchant": {"name": top_merchant_name, "total": round(top_merchant_total, 2)},
    }

    # ── Call Claude ──────────────────────────────────────────────────────────
    message = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(data)}],
    )
    raw = message.content[0].text
    parsed = json.loads(_strip_code_fences(raw))

    # ── Delete existing non-dismissed insights for same month/year ───────────
    existing = db.exec(
        select(AIInsight)
        .where(AIInsight.month == month)
        .where(AIInsight.year == year)
        .where(AIInsight.is_dismissed == False)  # noqa: E712
    ).all()
    for ins in existing:
        db.delete(ins)
    db.commit()

    # ── Persist new insights: spikes + insights arrays ───────────────────────
    saved: list[AIInsight] = []

    # Summary insight
    if summary_text := parsed.get("summary"):
        ins = AIInsight(
            type="summary",
            title="Monthly Summary",
            content=summary_text,
            severity="info",
            month=month,
            year=year,
        )
        db.add(ins)
        saved.append(ins)

    for spike in parsed.get("spikes", []):
        ins = AIInsight(
            type="spike",
            title=f"{spike.get('category', 'Category')} spike",
            content=spike.get("explanation", ""),
            severity=spike.get("severity", "warning"),
            month=month,
            year=year,
        )
        db.add(ins)
        saved.append(ins)

    for insight in parsed.get("insights", []):
        ins = AIInsight(
            type=insight.get("type", "recommendation"),
            title=insight.get("title", ""),
            content=insight.get("content", ""),
            severity=insight.get("severity", "info"),
            month=month,
            year=year,
        )
        db.add(ins)
        saved.append(ins)

    db.commit()
    for ins in saved:
        db.refresh(ins)

    return saved


# ─────────────────────────────────────────────────────────────────────────────
# 2. chat_with_finances
# ─────────────────────────────────────────────────────────────────────────────

async def chat_with_finances(question: str, db: Session) -> str:
    today = date.today()
    month, year = today.month, today.year
    month_str = f"{month:02d}"
    year_str = str(year)

    categories = {c.id: c for c in db.exec(select(Category)).all()}

    # ── Last 3 months category totals ────────────────────────────────────────
    base = date(year, month, 1)
    historical: list[dict] = []
    for i in range(1, 4):
        d = base - relativedelta(months=i)
        totals = _category_totals_for_month(d.month, d.year, db)
        for cat_id, total in totals.items():
            cat = categories.get(cat_id)
            historical.append({
                "month": d.month,
                "year": d.year,
                "category": cat.name if cat else "Unknown",
                "total": round(total, 2),
            })

    # ── Current month transactions (max 50) ───────────────────────────────────
    recent_expenses = db.exec(
        select(Expense)
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
        .order_by(Expense.date.desc())
        .limit(50)
    ).all()

    transactions = []
    for exp in recent_expenses:
        cat = categories.get(exp.category_id)
        transactions.append({
            "date": str(exp.date),
            "amount": exp.amount,
            "description": exp.description,
            "category": cat.name if cat else "Unknown",
            "merchant": exp.merchant or "",
        })

    # ── Budget status for current month ──────────────────────────────────────
    budgets = db.exec(
        select(Budget)
        .where(Budget.month == month)
        .where(Budget.year == year)
    ).all()

    current_spend_map = _category_totals_for_month(month, year, db)
    budget_context = []
    for b in budgets:
        cat = categories.get(b.category_id)
        spent = current_spend_map.get(b.category_id, 0.0)
        budget_context.append({
            "category": cat.name if cat else "Unknown",
            "limit": b.monthly_limit,
            "spent": round(spent, 2),
        })

    context = {
        "current_month": month,
        "current_year": year,
        "last_3_months_by_category": historical,
        "current_month_transactions": transactions,
        "budgets": budget_context,
    }

    message = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=(
            "You are a personal finance assistant answering questions based on provided expense data. "
            "Be concise and specific with numbers."
        ),
        messages=[{
            "role": "user",
            "content": f"Expense data:\n{json.dumps(context)}\n\nQuestion: {question}",
        }],
    )
    return message.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# 3. detect_spikes  (synchronous — no IO blocking needed)
# ─────────────────────────────────────────────────────────────────────────────

def detect_spikes(month: int, year: int, db: Session) -> list[dict]:
    categories = {c.id: c for c in db.exec(select(Category)).all()}
    current_totals = _category_totals_for_month(month, year, db)

    base = date(year, month, 1)
    prev_months = [base - relativedelta(months=i) for i in range(1, 4)]

    spikes: list[dict] = []

    for cat_id, current_spend in current_totals.items():
        cat = categories.get(cat_id)
        if not cat:
            continue

        prev_vals: list[float] = []
        for d in prev_months:
            totals = _category_totals_for_month(d.month, d.year, db)
            if cat_id in totals:
                prev_vals.append(totals[cat_id])

        if not prev_vals:
            # Not enough history
            continue

        rolling_avg = sum(prev_vals) / 3
        if rolling_avg == 0:
            continue

        percentage_above = ((current_spend - rolling_avg) / rolling_avg) * 100

        if percentage_above >= 60:
            severity = "critical"
        elif percentage_above >= 30:
            severity = "warning"
        else:
            continue  # Not a spike

        explanation = (
            f"{cat.name} spending is {percentage_above:.0f}% above your "
            f"3-month average of ${rolling_avg:.0f}"
        )

        spikes.append({
            "category": cat.name,
            "current_spend": round(current_spend, 2),
            "rolling_avg": round(rolling_avg, 2),
            "percentage_above": round(percentage_above, 1),
            "severity": severity,
            "explanation": explanation,
        })

    # Sort: critical first, then by percentage descending
    spikes.sort(key=lambda s: (0 if s["severity"] == "critical" else 1, -s["percentage_above"]))
    return spikes
