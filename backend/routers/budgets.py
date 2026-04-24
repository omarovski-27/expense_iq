from calendar import monthrange
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, func

from database import get_session
from models import Budget, BudgetCreate, BudgetRead, Category, CategoryRead, Expense

router = APIRouter(prefix="/budgets", tags=["budgets"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /budgets/status   ← MUST be declared before GET /{id} to avoid collision
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status")
def get_budget_status(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    today = date.today()
    m = month or today.month
    y = year or today.year

    # All budgets for this period
    budgets = session.exec(
        select(Budget).where(Budget.month == m, Budget.year == y)
    ).all()

    if not budgets:
        return []

    # Days info for projection
    days_in_month = monthrange(y, m)[1]
    if m == today.month and y == today.year:
        days_elapsed = max(today.day, 1)
    else:
        days_elapsed = days_in_month  # past month: treat as complete

    results = []
    for budget in budgets:
        category = session.get(Category, budget.category_id)
        if not category:
            continue

        # Sum expenses for category + month/year
        spent_row = session.exec(
            select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
                Expense.category_id == budget.category_id,
                func.strftime("%m", Expense.date) == f"{m:02d}",
                func.strftime("%Y", Expense.date) == str(y),
            )
        ).one()
        spent = float(spent_row)

        pct = (spent / budget.monthly_limit * 100) if budget.monthly_limit else 0.0
        remaining = budget.monthly_limit - spent
        projected = (spent / days_elapsed * days_in_month) if days_elapsed else 0.0

        if pct >= 100:
            status = "over_budget"
        elif pct >= 70:
            status = "warning"
        else:
            status = "on_track"

        results.append({
            "category": CategoryRead.model_validate(category),
            "monthly_limit": budget.monthly_limit,
            "spent": spent,
            "percentage": round(pct, 1),
            "remaining": remaining,
            "projected_month_end": round(projected, 2),
            "status": status,
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# GET /budgets
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[BudgetRead])
def list_budgets(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    stmt = select(Budget)
    if month is not None:
        stmt = stmt.where(Budget.month == month)
    if year is not None:
        stmt = stmt.where(Budget.year == year)
    return session.exec(stmt).all()


# ─────────────────────────────────────────────────────────────────────────────
# POST /budgets  (upsert)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=BudgetRead)
def create_budget(body: BudgetCreate, session: Session = Depends(get_session)):
    # Upsert: update if category+month+year already exists
    existing = session.exec(
        select(Budget).where(
            Budget.category_id == body.category_id,
            Budget.month == body.month,
            Budget.year == body.year,
        )
    ).first()

    if existing:
        existing.monthly_limit = body.monthly_limit
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    budget = Budget(**body.model_dump())
    session.add(budget)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Budget already exists for this category/month/year")
    session.refresh(budget)
    return budget


# ─────────────────────────────────────────────────────────────────────────────
# PUT /budgets/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: int,
    body: BudgetCreate,
    session: Session = Depends(get_session),
):
    budget = session.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    budget.monthly_limit = body.monthly_limit
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget

