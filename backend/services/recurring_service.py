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
