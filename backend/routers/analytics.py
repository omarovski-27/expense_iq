from calendar import monthrange
from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Budget, Category, CategoryRead, Expense

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_summary(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    today = date.today()
    m = month or today.month
    y = year or today.year
    month_str = f"{m:02d}"
    year_str = str(y)

    # Total this month
    total_row = session.exec(
        select(func.coalesce(func.sum(Expense.amount), 0.0))
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
    ).one()
    total_this_month = round(float(total_row), 2)

    # Previous month total for MoM change
    prev = date(y, m, 1) - relativedelta(months=1)
    prev_row = session.exec(
        select(func.coalesce(func.sum(Expense.amount), 0.0))
        .where(func.strftime("%m", Expense.date) == f"{prev.month:02d}")
        .where(func.strftime("%Y", Expense.date) == str(prev.year))
    ).one()
    prev_total = float(prev_row)

    mom_change_percent = 0.0
    if prev_total > 0:
        mom_change_percent = round(((total_this_month - prev_total) / prev_total) * 100, 1)

    # Budget used percent
    budgets = session.exec(
        select(Budget).where(Budget.month == m, Budget.year == y)
    ).all()
    total_budgeted = sum(b.monthly_limit for b in budgets)
    budget_used_percent = 0.0
    if total_budgeted > 0:
        budget_used_percent = round((total_this_month / total_budgeted) * 100, 1)

    # Daily average
    days_in_month = monthrange(y, m)[1]
    if m == today.month and y == today.year:
        days_elapsed = max(today.day, 1)
    else:
        days_elapsed = days_in_month
    daily_average = round(total_this_month / days_elapsed, 2) if days_elapsed else 0.0

    # Top category
    top_row = session.exec(
        select(Expense.category_id, func.sum(Expense.amount).label("total"))
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
        .where(Expense.category_id.is_not(None))
        .group_by(Expense.category_id)
        .order_by(func.sum(Expense.amount).desc())
        .limit(1)
    ).first()

    top_category = None
    if top_row:
        cat = session.get(Category, top_row[0])
        if cat:
            top_category = {
                "name": cat.name,
                "icon": cat.icon,
                "amount": round(float(top_row[1]), 2),
            }

    return {
        "total_this_month": total_this_month,
        "mom_change_percent": mom_change_percent,
        "budget_used_percent": budget_used_percent,
        "daily_average": daily_average,
        "top_category": top_category,
    }


# ---------------------------------------------------------------------------
# GET /analytics/trends
# ---------------------------------------------------------------------------

@router.get("/trends")
def get_trends(session: Session = Depends(get_session)):
    today = date.today()
    results = []
    for i in range(5, -1, -1):  # 5 months ago → current month
        d = date(today.year, today.month, 1) - relativedelta(months=i)
        month_str = f"{d.month:02d}"
        year_str = str(d.year)

        row = session.exec(
            select(func.coalesce(func.sum(Expense.amount), 0.0))
            .where(func.strftime("%m", Expense.date) == month_str)
            .where(func.strftime("%Y", Expense.date) == year_str)
        ).one()

        results.append({
            "month": d.month,
            "year": d.year,
            "total": round(float(row), 2),
            "label": d.strftime("%b %Y"),
        })
    return results


# ---------------------------------------------------------------------------
# GET /analytics/category-breakdown
# ---------------------------------------------------------------------------

@router.get("/category-breakdown")
def get_category_breakdown(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    today = date.today()
    m = month or today.month
    y = year or today.year
    month_str = f"{m:02d}"
    year_str = str(y)

    rows = session.exec(
        select(Expense.category_id, func.sum(Expense.amount).label("total"))
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
        .where(Expense.category_id.is_not(None))
        .group_by(Expense.category_id)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    if not rows:
        return []

    grand_total = sum(float(r[1]) for r in rows)
    results = []
    for cat_id, total in rows:
        cat = session.get(Category, cat_id)
        if not cat:
            continue
        amount = round(float(total), 2)
        pct = round((amount / grand_total * 100), 1) if grand_total else 0.0
        results.append({
            "category": CategoryRead.model_validate(cat),
            "amount": amount,
            "percentage": pct,
        })
    return results


# ---------------------------------------------------------------------------
# GET /analytics/merchant-breakdown
# ---------------------------------------------------------------------------

@router.get("/merchant-breakdown")
def get_merchant_breakdown(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    today = date.today()
    m = month or today.month
    y = year or today.year
    month_str = f"{m:02d}"
    year_str = str(y)

    rows = session.exec(
        select(
            Expense.merchant,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .where(func.strftime("%m", Expense.date) == month_str)
        .where(func.strftime("%Y", Expense.date) == year_str)
        .where(Expense.merchant.is_not(None))
        .where(Expense.merchant != "")
        .group_by(Expense.merchant)
        .order_by(func.sum(Expense.amount).desc())
        .limit(20)
    ).all()

    return [
        {"merchant": row[0], "amount": round(float(row[1]), 2), "count": int(row[2])}
        for row in rows
    ]
