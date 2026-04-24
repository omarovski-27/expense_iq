import csv
import io
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import extract, or_
from sqlmodel import Session, select

from database import get_session
from models import Category, Expense, ExpenseCreate, ExpenseRead

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _load_expense(expense: Expense, session: Session) -> ExpenseRead:
    """Ensure the category relationship is loaded and return an ExpenseRead."""
    # Access the relationship so SQLModel populates it before the session closes
    _ = expense.category
    return ExpenseRead.model_validate(expense)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[ExpenseRead])
def list_expenses(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    stmt = select(Expense)

    if month is not None:
        stmt = stmt.where(extract("month", Expense.date) == month)
    if year is not None:
        stmt = stmt.where(extract("year", Expense.date) == year)
    if category_id is not None:
        stmt = stmt.where(Expense.category_id == category_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Expense.description.ilike(pattern),
                Expense.merchant.ilike(pattern),
            )
        )

    stmt = stmt.order_by(Expense.date.desc()).offset(offset).limit(limit)
    expenses = session.exec(stmt).all()
    return [_load_expense(e, session) for e in expenses]


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------

@router.post("/", response_model=ExpenseRead, status_code=201)
def create_expense(
    body: ExpenseCreate,
    session: Session = Depends(get_session),
):
    expense = Expense.model_validate(body)
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return _load_expense(expense, session)


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------

@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: int,
    session: Session = Depends(get_session),
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return _load_expense(expense, session)


# ---------------------------------------------------------------------------
# PUT /{id}
# ---------------------------------------------------------------------------

@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int,
    body: ExpenseCreate,
    session: Session = Depends(get_session),
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    expense.updated_at = datetime.utcnow()

    session.add(expense)
    session.commit()
    session.refresh(expense)
    return _load_expense(expense, session)


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------

@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    session: Session = Depends(get_session),
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    session.delete(expense)
    session.commit()
    return {"message": "Expense deleted"}


# ---------------------------------------------------------------------------
# POST /bulk-import
# ---------------------------------------------------------------------------

def _parse_date(raw: str) -> Optional[date]:
    """Accept YYYY-MM-DD or MM/DD/YYYY."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


@router.post("/bulk-import")
async def bulk_import(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    text = content.decode("utf-8-sig")  # strip BOM if present
    reader = csv.DictReader(io.StringIO(text))

    # Pre-load all categories (name → id) for fast lookup
    categories = session.exec(select(Category)).all()
    cat_map = {c.name.lower(): c.id for c in categories}
    fallback_id = cat_map.get("other")

    imported = 0
    skipped = 0

    for row in reader:
        amount_raw = row.get("amount", "").strip()
        description = row.get("description", "").strip()

        # Skip rows with missing required fields
        if not amount_raw or not description:
            skipped += 1
            continue

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            skipped += 1
            continue

        date_raw = row.get("date", "").strip()
        parsed_date = _parse_date(date_raw) if date_raw else date.today()
        if parsed_date is None:
            skipped += 1
            continue

        category_name = row.get("category", "").strip().lower()
        category_id = cat_map.get(category_name, fallback_id)

        expense = Expense(
            amount=amount,
            description=description,
            category_id=category_id,
            merchant=row.get("merchant", "").strip() or None,
            date=parsed_date,
            notes=row.get("notes", "").strip() or None,
        )
        session.add(expense)
        imported += 1

    session.commit()
    return {"imported": imported, "skipped": skipped}

