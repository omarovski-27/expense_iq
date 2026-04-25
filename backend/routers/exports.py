from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from database import get_session
from models import Budget, Category, Expense
from services.export_service import export_to_csv, export_to_excel

router = APIRouter(prefix="/exports", tags=["exports"])


def _build_expense_query(
    session: Session,
    month: Optional[int],
    year: Optional[int],
    category_id: Optional[int],
):
    from sqlalchemy import extract

    query = select(Expense).order_by(Expense.date.desc())
    if month is not None:
        query = query.where(extract("month", Expense.date) == month)
    if year is not None:
        query = query.where(extract("year", Expense.date) == year)
    if category_id is not None:
        query = query.where(Expense.category_id == category_id)
    return session.exec(query).all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /exports/csv
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/csv")
def download_csv(
    month: Optional[int] = None,
    year: Optional[int] = None,
    category_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    expenses = _build_expense_query(session, month, year, category_id)
    categories = session.exec(select(Category)).all()

    csv_buf = export_to_csv(expenses, categories)

    suffix = f"_{year}_{month:02d}" if year and month else "_all"
    filename = f"expenses{suffix}.csv"

    return StreamingResponse(
        iter([csv_buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /exports/excel
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/excel")
def download_excel(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    from datetime import date as _date

    today = _date.today()
    m = month if month is not None else today.month
    y = year if year is not None else today.year

    expenses = _build_expense_query(session, m, y, None)
    categories = session.exec(select(Category)).all()
    budgets = session.exec(
        select(Budget)
        .where(Budget.month == m)
        .where(Budget.year == y)
    ).all()

    xlsx_buf = export_to_excel(expenses, budgets, categories, m, y)

    filename = f"expenseiq_report_{y}_{m:02d}.xlsx"

    return StreamingResponse(
        iter([xlsx_buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

