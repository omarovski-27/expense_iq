from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from models import Expense, RecurringRule
from tz import today_jordan as _today_jordan


def _advance_date(current: date, frequency: str) -> date:
    if frequency == "daily":
        return current + timedelta(days=1)
    elif frequency == "weekly":
        return current + timedelta(weeks=1)
    elif frequency == "monthly":
        return current + relativedelta(months=1)
    elif frequency == "yearly":
        return current + relativedelta(years=1)
    return current + relativedelta(months=1)


def process_recurring_expenses(db: Session) -> list[dict]:
    """Check all active recurring rules due today or earlier.

    For each qualifying rule:
    1. Create an Expense record (is_recurring=True, recurring_id=rule.id)
    2. Update rule.last_run_date and advance rule.next_due_date
    3. Skip monthly/yearly rules already charged this calendar month

    Returns a list of {"name": str, "amount": float} for every expense created,
    so callers can send Telegram notifications.
    """
    today = _today_jordan()
    charged: list[dict] = []

    rules = db.exec(
        select(RecurringRule)
        .where(RecurringRule.is_active == True)  # noqa: E712
        .where(RecurringRule.next_due_date <= today)
    ).all()

    for rule in rules:
        # Guard: don't double-charge monthly/yearly rules in the same calendar month
        if rule.frequency in ("monthly", "yearly"):
            if (
                rule.last_run_date
                and rule.last_run_date.year == today.year
                and rule.last_run_date.month == today.month
            ):
                continue

        while rule.next_due_date <= today:
            expense = Expense(
                amount=rule.amount,
                description=rule.name,
                category_id=rule.category_id,
                date=rule.next_due_date,
                is_recurring=True,
                recurring_id=rule.id,
            )
            db.add(expense)
            charged.append({"name": rule.name, "amount": rule.amount})

            rule.last_run_date = rule.next_due_date
            rule.next_due_date = _advance_date(rule.next_due_date, rule.frequency)

        db.add(rule)

    if charged:
        db.commit()

    return charged


# Fields a caller (Telegram bot or HTTP router) is allowed to patch on a rule.
_RULE_EDITABLE_FIELDS = ("name", "amount", "category_id", "frequency", "next_due_date")


def update_recurring_fields(db: Session, rule_id: int, **fields) -> RecurringRule | None:
    """Patch a recurring rule in place.

    Only keys in ``_RULE_EDITABLE_FIELDS`` whose value is not None are applied,
    so callers can pass just the fields they want to change (e.g. amount only).
    Returns the updated rule, or None if no rule has that id.
    """
    rule = db.get(RecurringRule, rule_id)
    if not rule:
        return None
    for key in _RULE_EDITABLE_FIELDS:
        value = fields.get(key)
        if value is not None:
            setattr(rule, key, value)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_recurring_rule(db: Session, rule_id: int) -> bool:
    """Delete a recurring rule, first nulling recurring_id on any expenses it
    generated so we never leave a dangling foreign key (which Postgres rejects).

    Returns True if a rule was deleted, False if none matched the id.
    """
    rule = db.get(RecurringRule, rule_id)
    if not rule:
        return False
    linked = db.exec(select(Expense).where(Expense.recurring_id == rule_id)).all()
    for exp in linked:
        exp.recurring_id = None
        db.add(exp)
    db.delete(rule)
    db.commit()
    return True
