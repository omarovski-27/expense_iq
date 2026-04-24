from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from models import Expense, RecurringRule


def _advance_date(current: date, frequency: str) -> date:
    """Advance a date by one period based on frequency."""
    if frequency == "daily":
        return current + timedelta(days=1)
    elif frequency == "weekly":
        return current + timedelta(weeks=1)
    elif frequency == "monthly":
        return current + relativedelta(months=1)
    elif frequency == "yearly":
        return current + relativedelta(years=1)
    # Fallback: treat as monthly
    return current + relativedelta(months=1)


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
    Returns count of expenses created.
    """
    today = date.today()
    count = 0

    rules = db.exec(
        select(RecurringRule)
        .where(RecurringRule.is_active == True)  # noqa: E712
        .where(RecurringRule.next_due_date <= today)
    ).all()

    for rule in rules:
        # Process every due date up to and including today
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
            count += 1

            rule.last_run_date = rule.next_due_date
            rule.next_due_date = _advance_date(rule.next_due_date, rule.frequency)

        db.add(rule)

    if count:
        db.commit()

    return count
