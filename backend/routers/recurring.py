from calendar import monthrange
from datetime import date as date_
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import (
    RecurringRule,
    RecurringRuleCreate,
    RecurringRuleRead,
    Category,
    CategoryRead,
)

router = APIRouter(prefix="/recurring", tags=["recurring"])


def _rule_read(rule: RecurringRule, session: Session) -> dict:
    """Return a dict matching RecurringRuleRead plus a nested category."""
    data = RecurringRuleRead.model_validate(rule).model_dump()
    if rule.category_id:
        cat = session.get(Category, rule.category_id)
        data["category"] = CategoryRead.model_validate(cat).model_dump() if cat else None
    else:
        data["category"] = None
    return data


def _rule_applies_to_month(rule: RecurringRule, month: int, year: int) -> bool:
    """True if the rule would generate at least one charge during (month, year).

    A rule's first possible charge is bounded by `created_at`. After that, the
    cadence determines whether the rule hits the selected month:
      - daily / weekly / monthly: charges in every subsequent month
      - yearly: charges only in the anniversary month (anchored on next_due_date)
    """
    last_day = date_(year, month, monthrange(year, month)[1])
    rule_start = rule.created_at.date()
    if rule_start > last_day:
        return False
    if rule.frequency == "yearly":
        return rule.next_due_date.month == month
    return True


# ─────────────────────────────────────────────────────────────────────────────
# GET /recurring
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/")
def list_recurring(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=1970, le=2100),
    session: Session = Depends(get_session),
):
    rules = session.exec(select(RecurringRule).order_by(RecurringRule.name)).all()
    if month is not None and year is not None:
        rules = [r for r in rules if _rule_applies_to_month(r, month, year)]
    return [_rule_read(r, session) for r in rules]


# ─────────────────────────────────────────────────────────────────────────────
# POST /recurring
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=RecurringRuleRead)
def create_recurring(body: RecurringRuleCreate, session: Session = Depends(get_session)):
    rule = RecurringRule(**body.model_dump())
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


# ─────────────────────────────────────────────────────────────────────────────
# PUT /recurring/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/{rule_id}", response_model=RecurringRuleRead)
def update_recurring(
    rule_id: int,
    body: RecurringRuleCreate,
    session: Session = Depends(get_session),
):
    rule = session.get(RecurringRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /recurring/{id}/toggle  — toggle is_active
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{rule_id}/toggle", response_model=RecurringRuleRead)
def toggle_recurring(rule_id: int, session: Session = Depends(get_session)):
    rule = session.get(RecurringRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    rule.is_active = not rule.is_active
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /recurring/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete("/{rule_id}")
def delete_recurring(rule_id: int, session: Session = Depends(get_session)):
    from services.recurring_service import delete_recurring_rule

    # Shared helper nulls recurring_id on linked expenses before deleting, so we
    # never leave a dangling FK. Same path the Telegram /delsub flow uses.
    if not delete_recurring_rule(session, rule_id):
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    return {"message": "Recurring rule deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /recurring/run  — manually trigger due expenses
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/run")
def run_recurring(session: Session = Depends(get_session)):
    from services.recurring_service import process_recurring_expenses
    charged = process_recurring_expenses(session)
    n = len(charged)
    return {"message": f"Created {n} expense(s) from recurring rules", "created": n}

