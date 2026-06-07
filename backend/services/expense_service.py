from datetime import datetime

from sqlmodel import Session

from models import Expense


# Fields a caller (Telegram bot or HTTP router) is allowed to patch on an expense.
_EXPENSE_EDITABLE_FIELDS = (
    "amount",
    "description",
    "category_id",
    "merchant",
    "date",
    "notes",
)


def update_expense_fields(db: Session, expense_id: int, **fields) -> Expense | None:
    """Patch an expense in place.

    Only keys in ``_EXPENSE_EDITABLE_FIELDS`` whose value is not None are applied,
    so callers can pass just the fields they want to change. ``updated_at`` is
    always bumped. Returns the updated expense, or None if no expense has that id.
    """
    expense = db.get(Expense, expense_id)
    if not expense:
        return None
    for key in _EXPENSE_EDITABLE_FIELDS:
        value = fields.get(key)
        if value is not None:
            setattr(expense, key, value)
    expense.updated_at = datetime.utcnow()
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense_id: int) -> bool:
    """Delete an expense. Returns True if one was deleted, False if none matched."""
    expense = db.get(Expense, expense_id)
    if not expense:
        return False
    db.delete(expense)
    db.commit()
    return True
