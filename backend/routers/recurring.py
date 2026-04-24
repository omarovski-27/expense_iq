from fastapi import APIRouter, Depends, HTTPException
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


# ─────────────────────────────────────────────────────────────────────────────
# GET /recurring
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/")
def list_recurring(session: Session = Depends(get_session)):
    rules = session.exec(select(RecurringRule).order_by(RecurringRule.name)).all()
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
    rule = session.get(RecurringRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    session.delete(rule)
    session.commit()
    return {"message": "Recurring rule deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /recurring/run  — manually trigger due expenses
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/run")
def run_recurring(session: Session = Depends(get_session)):
    from services.recurring_service import process_recurring_expenses
    count = process_recurring_expenses(session)
    return {"message": f"Created {count} expense(s) from recurring rules", "created": count}

