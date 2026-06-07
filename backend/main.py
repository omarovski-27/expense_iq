from contextlib import asynccontextmanager
from datetime import date, timedelta
import logging

import os

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import Category, Expense, RecurringRule
from services.recurring_service import process_recurring_expenses
from routers import analytics, budgets, categories, expenses, exports, health, insights, recurring
from services.telegram_service import (
    build_expense_payload,
    find_category_id,
    format_confirmation,
    format_help_text,
    format_max_expense,
    format_month_expenses,
    format_removesub_list,
    format_subs_list,
    format_today_expenses,
    format_top5_expenses,
    format_week_expenses,
    parse_expense_text,
)
from tz import today_jordan as _today_jordan


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if "http://localhost:5173" not in cors_origins:
    cors_origins.append("http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    create_db_and_tables()

    # Seed default categories if the table is empty
    default_categories = [
        ("Food", "#FF6B35", "🍔"),
        ("Transport", "#4ECDC4", "🚗"),
        ("Shopping", "#45B7D1", "🛍️"),
        ("Entertainment", "#96CEB4", "🎬"),
        ("Health", "#FFEAA7", "💊"),
        ("Bills", "#DDA0DD", "📋"),
        ("Travel", "#98D8C8", "✈️"),
        ("Education", "#F7DC6F", "📚"),
        ("Personal", "#BB8FCE", "💈"),
        ("Other", "#AED6F1", "📦"),
    ]

    with Session(engine) as session:
        existing = session.exec(select(Category)).first()
        if not existing:
            for name, color, icon in default_categories:
                session.add(Category(name=name, color=color, icon=icon))
            session.commit()

    # Process any recurring expenses that became due and notify via Telegram
    with Session(engine) as recurring_session:
        try:
            charged = process_recurring_expenses(recurring_session)
        except Exception:
            logger.exception("Recurring expenses processing failed on startup")
            charged = []

    if charged:
        _telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        _chat_id_str = os.getenv("TELEGRAM_ALLOWED_USER_ID")
        if _telegram_token and _chat_id_str:
            _api_url = f"https://api.telegram.org/bot{_telegram_token}/sendMessage"
            async with httpx.AsyncClient(timeout=15) as _client:
                for item in charged:
                    _msg = f"\U0001f4c5 Auto-charged: {item['name']} — {item['amount']:.2f} JOD added to today's expenses."
                    try:
                        await _client.post(_api_url, json={"chat_id": int(_chat_id_str), "text": _msg})
                    except Exception:
                        logger.exception("Failed to send Telegram startup notification for %s", item["name"])

    yield  # app runs here


app = FastAPI(
    title="ExpenseIQ API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while processing %s", request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Routers
app.include_router(expenses.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(budgets.router, prefix="/api")
app.include_router(recurring.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(health.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.head("/health", status_code=200)
def health_check_head():
    return Response(status_code=200)


conversation_state: dict[int, dict] = {}


async def _handle_conversation(chat_id: int, text: str, step: str, data: dict, state_dict: dict) -> str:
    if step == "addsub_name":
        data["name"] = text.strip()
        state_dict[chat_id]["step"] = "addsub_amount"
        return "How much? (JOD)"

    if step == "addsub_amount":
        try:
            amount = float(text.strip().replace(",", "."))
            assert amount > 0
        except (ValueError, AssertionError):
            return "Invalid amount. Please enter a positive number (e.g. 14.7):"
        data["amount"] = amount
        state_dict[chat_id]["step"] = "addsub_category"
        return "Category? (bills / entertainment / health / other)"

    if step == "addsub_category":
        with Session(engine) as session:
            category_rows = session.exec(select(Category).order_by(Category.name)).all()
            cats = [{"id": c.id, "name": c.name} for c in category_rows]
        cat_id, cat_name = find_category_id(text.strip(), cats)
        data["category_id"] = cat_id
        data["category_name"] = cat_name
        state_dict[chat_id]["step"] = "addsub_date"
        return "Next due date? (DD/MM/YYYY)"

    if step == "addsub_date":
        from datetime import datetime as dt_
        try:
            due_date = dt_.strptime(text.strip(), "%d/%m/%Y").date()
        except ValueError:
            return "Invalid date. Please use DD/MM/YYYY (e.g. 01/06/2026):"
        with Session(engine) as session:
            rule = RecurringRule(
                name=data["name"],
                amount=data["amount"],
                category_id=data["category_id"],
                frequency="monthly",
                next_due_date=due_date,
            )
            session.add(rule)
            session.commit()
        del state_dict[chat_id]
        return (
            f"Saved! {data['name']} - {data['amount']:.2f} JOD "
            f"({data['category_name']}) due {due_date:%d/%m/%Y}.\n"
            "/subs to see all subscriptions."
        )

    if step == "removesub_pick":
        rules = data["rules"]
        try:
            idx = int(text.strip()) - 1
            assert 0 <= idx < len(rules)
        except (ValueError, AssertionError):
            return f"Please reply with a number between 1 and {len(rules)}."
        chosen = rules[idx]
        with Session(engine) as session:
            rule = session.get(RecurringRule, chosen["id"])
            if rule:
                session.delete(rule)
                session.commit()
        del state_dict[chat_id]
        return f"Removed: {chosen['name']}.\n/subs to see remaining subscriptions."

    del state_dict[chat_id]
    return "Something went wrong. Please try again."


@app.post("/webhook/telegram")
async def telegram_webhook(payload: dict):
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    allowed_user_id = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

    if not telegram_token:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")

    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return {"ok": True}

    from_user = message.get("from") or {}
    if from_user.get("id") != allowed_user_id:
        return {"ok": True}

    message_text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not message_text or chat_id is None:
        return {"ok": True}

    if chat_id in conversation_state and not message_text.startswith("/"):
        state = conversation_state[chat_id]
        reply_text = await _handle_conversation(chat_id, message_text, state["step"], state["data"], conversation_state)
        api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(api_url, json={"chat_id": chat_id, "text": reply_text})
            resp.raise_for_status()
        return {"ok": True}

    command = message_text.split()[0].lower()
    if command.startswith("/"):
        if command in {"/help", "/categories"}:
            reply_text = format_help_text()
        elif command == "/today":
            today = _today_jordan()
            with Session(engine) as session:
                expense_rows = session.exec(
                    select(Expense)
                    .where(Expense.date == today)
                    .order_by(Expense.id)
                ).all()
                expense_payload = [
                    {
                        "description": expense.description,
                        "merchant": expense.merchant,
                        "amount": expense.amount,
                        "category_name": (
                            expense.category.name if expense.category else "Uncategorized"
                        ),
                    }
                    for expense in expense_rows
                ]
            reply_text = format_today_expenses(expense_payload, today)
        elif command == "/week":
            today = _today_jordan()
            week_start = today - timedelta(days=today.weekday())
            with Session(engine) as session:
                expense_rows = session.exec(
                    select(Expense)
                    .where(Expense.date >= week_start)
                    .where(Expense.date <= today)
                    .order_by(Expense.date, Expense.id)
                ).all()
                expense_payload = [
                    {
                        "description": expense.description,
                        "merchant": expense.merchant,
                        "amount": expense.amount,
                        "category_name": (
                            expense.category.name if expense.category else "Uncategorized"
                        ),
                    }
                    for expense in expense_rows
                ]
            reply_text = format_week_expenses(expense_payload, today)
        elif command == "/month":
            today = _today_jordan()
            month_start = date(today.year, today.month, 1)
            if today.month == 12:
                next_month_start = date(today.year + 1, 1, 1)
            else:
                next_month_start = date(today.year, today.month + 1, 1)

            with Session(engine) as session:
                expense_rows = session.exec(
                    select(Expense)
                    .where(Expense.date >= month_start)
                    .where(Expense.date < next_month_start)
                    .order_by(Expense.date, Expense.id)
                ).all()
                expense_payload = [
                    {
                        "description": expense.description,
                        "merchant": expense.merchant,
                        "amount": expense.amount,
                        "category_name": (
                            expense.category.name if expense.category else "Uncategorized"
                        ),
                    }
                    for expense in expense_rows
                ]
            reply_text = format_month_expenses(expense_payload, today)
        elif command == "/budget":
            reply_text = "Not yet implemented."
        elif command == "/max":
            today = _today_jordan()
            month_start = date(today.year, today.month, 1)
            if today.month == 12:
                next_month_start = date(today.year + 1, 1, 1)
            else:
                next_month_start = date(today.year, today.month + 1, 1)
            with Session(engine) as session:
                expense_row = session.exec(
                    select(Expense)
                    .where(Expense.date >= month_start)
                    .where(Expense.date < next_month_start)
                    .order_by(Expense.amount.desc())
                    .limit(1)
                ).first()
                if expense_row:
                    max_payload = {
                        "description": expense_row.merchant or expense_row.description,
                        "amount": expense_row.amount,
                        "category_name": (
                            expense_row.category.name if expense_row.category else "Uncategorized"
                        ),
                        "date": expense_row.date.strftime("%b %d, %Y"),
                    }
                else:
                    max_payload = None
            reply_text = format_max_expense(max_payload, today)
        elif command == "/top5":
            today = _today_jordan()
            month_start = date(today.year, today.month, 1)
            if today.month == 12:
                next_month_start = date(today.year + 1, 1, 1)
            else:
                next_month_start = date(today.year, today.month + 1, 1)
            with Session(engine) as session:
                expense_rows = session.exec(
                    select(Expense)
                    .where(Expense.date >= month_start)
                    .where(Expense.date < next_month_start)
                    .order_by(Expense.amount.desc())
                    .limit(5)
                ).all()
                top5_payload = [
                    {
                        "description": e.merchant or e.description,
                        "amount": e.amount,
                        "category_name": (
                            e.category.name if e.category else "Uncategorized"
                        ),
                    }
                    for e in expense_rows
                ]
            reply_text = format_top5_expenses(top5_payload, today)
        elif command == "/subs":
            # 1. Auto-charge any subscriptions that are due.
            #    Must not raise: a 500 here makes Telegram retry the webhook and
            #    re-run the charge, double-charging daily/weekly rules (their only
            #    idempotency guard is the advanced next_due_date).
            try:
                with Session(engine) as session:
                    charged = process_recurring_expenses(session)
            except Exception:
                logger.exception("Auto-charge failed during /subs")
                charged = []

            # 2. Send one notification per charged subscription (best-effort —
            #    the charge already committed, so a send failure must not 500).
            _subs_api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            async with httpx.AsyncClient(timeout=15) as _subs_client:
                for item in charged:
                    _msg = f"\U0001f4c5 Auto-charged: {item['name']} — {item['amount']:.2f} JOD added to today's expenses."
                    try:
                        await _subs_client.post(_subs_api_url, json={"chat_id": chat_id, "text": _msg})
                    except Exception:
                        logger.exception("Failed to send /subs auto-charge notification for %s", item["name"])

                # 3. Fetch the current subscription list and send it (best-effort).
                try:
                    with Session(engine) as session:
                        rules = session.exec(
                            select(RecurringRule)
                            .where(RecurringRule.is_active == True)
                            .order_by(RecurringRule.next_due_date)
                        ).all()
                        rules_payload = [
                            {
                                "name": r.name,
                                "amount": r.amount,
                                "category_name": (
                                    session.get(Category, r.category_id).name
                                    if r.category_id else "Other"
                                ),
                                "next_due_date": r.next_due_date,
                            }
                            for r in rules
                        ]
                    list_text = format_subs_list(rules_payload)
                    await _subs_client.post(_subs_api_url, json={"chat_id": chat_id, "text": list_text})
                except Exception:
                    logger.exception("Failed to build or send the /subs list")

            return {"ok": True}
        elif command == "/addsubscription":
            conversation_state[chat_id] = {"step": "addsub_name", "data": {}}
            reply_text = "What's the subscription name?"
        elif command == "/removesub":
            with Session(engine) as session:
                rules = session.exec(
                    select(RecurringRule)
                    .where(RecurringRule.is_active == True)
                    .order_by(RecurringRule.next_due_date)
                ).all()
                rules_payload = [
                    {
                        "id": r.id,
                        "name": r.name,
                        "amount": r.amount,
                        "next_due_date": r.next_due_date,
                    }
                    for r in rules
                ]
            if not rules_payload:
                reply_text = "No subscriptions to remove."
            else:
                conversation_state[chat_id] = {"step": "removesub_pick", "data": {"rules": rules_payload}}
                reply_text = format_removesub_list(rules_payload)
        else:
            reply_text = format_help_text()

        api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(api_url, json={"chat_id": chat_id, "text": reply_text})
            response.raise_for_status()

        return {"ok": True}

    with Session(engine) as session:
        category_rows = session.exec(select(Category).order_by(Category.name)).all()
        category_payload = [
            {"id": category.id, "name": category.name}
            for category in category_rows
        ]
        parsed = parse_expense_text(message_text, category_payload)

        if parsed is None:
            reply_text = format_help_text()
        else:
            today = _today_jordan()
            expense_data = build_expense_payload(parsed, today)
            expense = Expense.model_validate(expense_data)
            session.add(expense)
            session.commit()
            reply_text = format_confirmation(parsed, today)

    # Best-effort send: the expense is already committed, so a Telegram error
    # here must not 500 — otherwise Telegram retries the webhook and the same
    # expense is logged twice.
    api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(api_url, json={"chat_id": chat_id, "text": reply_text})
        except Exception:
            logger.exception("Failed to send expense confirmation")

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
