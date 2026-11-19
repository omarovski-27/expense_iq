"""Channel-agnostic expense capture.

Any client that can send an HTTP request (an iOS Shortcut, the installed web
app's quick-add box, a future bot) posts the same free text the Telegram bot
accepts, e.g. "coffee 2.5 food". The text runs through the same parser the bot
uses, so every channel behaves identically.

Auth: a single shared secret in the INGEST_API_KEY env var, sent as the
X-API-Key header (or "Authorization: Bearer <key>"). If the env var is unset
the endpoint refuses every request rather than running open.

Every response carries a human-readable "message" so a Shortcut can show it
as a notification without branching on status codes.
"""
import hmac
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Category, Expense, ExpenseRead
from services.telegram_service import (
    build_expense_payload,
    parse_date_ddmmyyyy,
    parse_expense_text,
)
from tz import today_jordan

router = APIRouter(prefix="/ingest", tags=["ingest"])

INGEST_SOURCE_NOTE = "via ingest"
UNDO_WINDOW = timedelta(minutes=15)
PARSE_HELP = "Couldn't read that. Try: coffee 2.5 food"


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)
    # Optional explicit date: YYYY-MM-DD, DD/MM/YYYY, "today" or "yesterday".
    date: Optional[str] = None


def require_ingest_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> None:
    expected = os.getenv("INGEST_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Ingest is not configured")

    supplied = x_api_key or ""
    if not supplied and authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()

    if not supplied or not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")


def _resolve_date(raw: Optional[str], today: date) -> Optional[date]:
    """Return the target date, or None if `raw` is present but unreadable."""
    if raw is None or not raw.strip():
        return today
    value = raw.strip().lower()
    if value == "today":
        return today
    if value == "yesterday":
        return today - timedelta(days=1)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return parse_date_ddmmyyyy(value)


def _split_date_word(text: str) -> tuple[str, Optional[str]]:
    """Pull a trailing/leading 'today'/'yesterday' out of dictated text.

    "coffee 2.5 yesterday" -> ("coffee 2.5", "yesterday"). Without this the
    parser would treat the word as part of the merchant name.
    """
    tokens = text.split()
    for word in ("yesterday", "today"):
        lowered = [t.lower() for t in tokens]
        if word in lowered:
            idx = lowered.index(word)
            return " ".join(tokens[:idx] + tokens[idx + 1:]), word
    return text, None


def _day_total(session: Session, target: date) -> float:
    total = session.exec(select(func.sum(Expense.amount)).where(Expense.date == target)).one()
    return float(total or 0)


def _fail(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"ok": False, "message": message})


def _undo_last(session: Session) -> JSONResponse | dict:
    cutoff = datetime.now(timezone.utc) - UNDO_WINDOW
    last = session.exec(
        select(Expense)
        .where(Expense.notes == INGEST_SOURCE_NOTE)
        .order_by(Expense.id.desc())
        .limit(1)
    ).first()
    if last is None:
        return _fail(404, "Nothing to undo.")
    created = last.created_at
    if created.tzinfo is None:  # SQLite returns naive datetimes
        created = created.replace(tzinfo=timezone.utc)
    if created < cutoff:
        return _fail(409, "Last quick-added expense is older than 15 minutes. Delete it in the app.")
    name = last.merchant or last.description or "Expense"
    amount = last.amount
    session.delete(last)
    session.commit()
    return {"ok": True, "message": f"Removed {name} ({amount:.2f} JD)."}


@router.post("", dependencies=[Depends(require_ingest_key)])
def ingest(body: IngestRequest, session: Session = Depends(get_session)):
    text = body.text.strip()
    if text.lower() == "undo":
        return _undo_last(session)

    today = today_jordan()
    text, date_word = _split_date_word(text)
    target = _resolve_date(body.date or date_word, today)
    if target is None:
        return _fail(422, "Invalid date. Use YYYY-MM-DD, DD/MM/YYYY, today or yesterday.")
    if target > today:
        return _fail(422, "Date can't be in the future.")

    categories = [
        {"id": c.id, "name": c.name}
        for c in session.exec(select(Category).order_by(Category.name)).all()
    ]
    if not categories:
        return _fail(503, "No categories configured.")

    parsed = parse_expense_text(text, categories)
    if parsed is None:
        return _fail(422, PARSE_HELP)

    payload = build_expense_payload(parsed, target)
    payload["notes"] = INGEST_SOURCE_NOTE
    expense = Expense.model_validate(payload)
    session.add(expense)
    session.commit()
    session.refresh(expense)
    _ = expense.category

    name = parsed["merchant"] or "Expense"
    day_label = "Today" if target == today else f"{target:%b} {target.day}"
    message = (
        f"Added {name}: {parsed['amount']:.2f} JD ({parsed['category_name']}). "
        f"{day_label}: {_day_total(session, target):.2f} JD"
    )
    return {
        "ok": True,
        "message": message,
        "expense": ExpenseRead.model_validate(expense).model_dump(mode="json"),
    }
