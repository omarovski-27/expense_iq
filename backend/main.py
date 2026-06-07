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
from services.recurring_service import (
    delete_recurring_rule,
    process_recurring_expenses,
    update_recurring_fields,
)
from services.expense_service import delete_expense, update_expense_fields
from routers import analytics, budgets, categories, expenses, exports, health, insights, recurring
from services.telegram_service import (
    build_expense_payload,
    find_category_id,
    format_confirmation,
    format_expenses_numbered,
    format_help_text,
    format_max_expense,
    format_month_expenses,
    format_subs_list,
    format_subs_numbered,
    format_today_expenses,
    format_top5_expenses,
    format_week_expenses,
    match_rules_by_name,
    parse_amount,
    parse_date_ddmmyyyy,
    parse_editsub_oneshot,
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


def _active_rules_payload() -> list[dict]:
    """Active subscriptions as lightweight dicts for the edit/delete pick lists."""
    with Session(engine) as session:
        rules = session.exec(
            select(RecurringRule)
            .where(RecurringRule.is_active == True)  # noqa: E712
            .order_by(RecurringRule.next_due_date)
        ).all()
        return [
            {"id": r.id, "name": r.name, "amount": r.amount, "next_due_date": r.next_due_date}
            for r in rules
        ]


def _recent_expenses_payload(limit: int = 10) -> list[dict]:
    """The most recent expenses as lightweight dicts for the edit/delete pick lists."""
    with Session(engine) as session:
        rows = session.exec(
            select(Expense).order_by(Expense.date.desc(), Expense.id.desc()).limit(limit)
        ).all()
        return [
            {
                "id": e.id,
                "description": e.description,
                "merchant": e.merchant,
                "amount": e.amount,
                "category_name": e.category.name if e.category else "Uncategorized",
                "date": e.date,
            }
            for e in rows
        ]


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

    # ── /delsub (and /removesub alias) ──────────────────────────────────────
    if step == "delsub_pick":
        rules = data["rules"]
        try:
            idx = int(text.strip()) - 1
            assert 0 <= idx < len(rules)
        except (ValueError, AssertionError):
            return f"Please reply with a number between 1 and {len(rules)}."
        chosen = rules[idx]
        with Session(engine) as session:
            deleted = delete_recurring_rule(session, chosen["id"])
        del state_dict[chat_id]
        if deleted:
            return f"Removed: {chosen['name']}.\n/subs to see remaining subscriptions."
        return f"{chosen['name']} was already removed.\n/subs to see remaining subscriptions."

    if step == "delsub_confirm":
        if text.strip().lower() in ("yes", "y"):
            with Session(engine) as session:
                deleted = delete_recurring_rule(session, data["rule_id"])
            del state_dict[chat_id]
            if deleted:
                return f"Removed: {data['rule_name']}.\n/subs to see remaining subscriptions."
            return f"{data['rule_name']} was already removed."
        del state_dict[chat_id]
        return "Cancelled. Nothing was deleted."

    # ── /editsub ────────────────────────────────────────────────────────────
    if step == "editsub_pick":
        rules = data["rules"]
        try:
            idx = int(text.strip()) - 1
            assert 0 <= idx < len(rules)
        except (ValueError, AssertionError):
            return f"Please reply with a number between 1 and {len(rules)}."
        chosen = rules[idx]
        data["rule_id"] = chosen["id"]
        data["current_due"] = chosen["next_due_date"]
        # If a one-shot supplied amount/date up front, apply now and finish.
        if data.get("pending_amount") is not None or data.get("pending_date") is not None:
            with Session(engine) as session:
                updated = update_recurring_fields(
                    session,
                    chosen["id"],
                    amount=data.get("pending_amount"),
                    next_due_date=data.get("pending_date"),
                )
            del state_dict[chat_id]
            return _format_sub_updated(updated)
        state_dict[chat_id]["step"] = "editsub_amount"
        return f"New amount for {chosen['name']}? (current {chosen['amount']:.2f}) Send a number, or 'skip'."

    if step == "editsub_amount":
        if text.strip().lower() not in ("skip", "-"):
            amount = parse_amount(text)
            if amount is None:
                return "Invalid amount. Send a positive number (e.g. 15.99) or 'skip'."
            data["new_amount"] = amount
        state_dict[chat_id]["step"] = "editsub_date"
        cur_due = data["current_due"]
        cur_due_str = f"{cur_due:%d/%m/%Y}" if hasattr(cur_due, "strftime") else str(cur_due)
        return f"New due date? DD/MM/YYYY (current {cur_due_str}) or 'skip'."

    if step == "editsub_date":
        if text.strip().lower() not in ("skip", "-"):
            due = parse_date_ddmmyyyy(text)
            if due is None:
                return "Invalid date. Use DD/MM/YYYY (e.g. 27/06/2026) or 'skip'."
            data["new_due"] = due
        with Session(engine) as session:
            updated = update_recurring_fields(
                session,
                data["rule_id"],
                amount=data.get("new_amount"),
                next_due_date=data.get("new_due"),
            )
        del state_dict[chat_id]
        return _format_sub_updated(updated)

    # ── /addexpense (guided) ────────────────────────────────────────────────
    if step == "addexp_text":
        with Session(engine) as session:
            category_rows = session.exec(select(Category).order_by(Category.name)).all()
            category_payload = [{"id": c.id, "name": c.name} for c in category_rows]
        parsed = parse_expense_text(text, category_payload)
        if parsed is None:
            return "Couldn't read that. Try: coffee 2.5 food"
        data["parsed"] = parsed
        state_dict[chat_id]["step"] = "addexp_date"
        return "Date? DD/MM/YYYY, or 'today'."

    if step == "addexp_date":
        if text.strip().lower() in ("today", "skip"):
            target = _today_jordan()
        else:
            target = parse_date_ddmmyyyy(text)
            if target is None:
                return "Invalid date. Use DD/MM/YYYY (e.g. 05/06/2026) or 'today'."
        parsed = data["parsed"]
        with Session(engine) as session:
            expense = Expense.model_validate(build_expense_payload(parsed, target))
            session.add(expense)
            session.commit()
        del state_dict[chat_id]
        return format_confirmation(parsed, target)

    # ── /editexpense ────────────────────────────────────────────────────────
    if step == "editexp_pick":
        expenses_list = data["expenses"]
        try:
            idx = int(text.strip()) - 1
            assert 0 <= idx < len(expenses_list)
        except (ValueError, AssertionError):
            return f"Please reply with a number between 1 and {len(expenses_list)}."
        chosen = expenses_list[idx]
        data["expense_id"] = chosen["id"]
        data["current"] = chosen
        state_dict[chat_id]["step"] = "editexp_amount"
        return f"New amount? (current {chosen['amount']:.2f}) Send a number, or 'skip'."

    if step == "editexp_amount":
        if text.strip().lower() not in ("skip", "-"):
            amount = parse_amount(text)
            if amount is None:
                return "Invalid amount. Send a positive number or 'skip'."
            data["new_amount"] = amount
        state_dict[chat_id]["step"] = "editexp_category"
        return f"New category? (current {data['current']['category_name']}) Send a category name, or 'skip'."

    if step == "editexp_category":
        if text.strip().lower() not in ("skip", "-"):
            with Session(engine) as session:
                cats = session.exec(select(Category).order_by(Category.name)).all()
                cat_payload = [{"id": c.id, "name": c.name} for c in cats]
            cat_id, _ = find_category_id(text.strip(), cat_payload)
            data["new_category_id"] = cat_id
        state_dict[chat_id]["step"] = "editexp_date"
        cur_date = data["current"]["date"]
        cur_str = f"{cur_date:%d/%m/%Y}" if hasattr(cur_date, "strftime") else str(cur_date)
        return f"New date? DD/MM/YYYY (current {cur_str}) or 'skip'."

    if step == "editexp_date":
        if text.strip().lower() not in ("skip", "-"):
            d = parse_date_ddmmyyyy(text)
            if d is None:
                return "Invalid date. Use DD/MM/YYYY or 'skip'."
            data["new_date"] = d
        with Session(engine) as session:
            updated = update_expense_fields(
                session,
                data["expense_id"],
                amount=data.get("new_amount"),
                category_id=data.get("new_category_id"),
                date=data.get("new_date"),
            )
        del state_dict[chat_id]
        if updated is None:
            return "That expense no longer exists."
        name = updated.merchant or updated.description or "Expense"
        return f"Updated {name} → {updated.amount:.2f} JD on {updated.date:%b %d, %Y}."

    # ── /delexpense ─────────────────────────────────────────────────────────
    if step == "delexp_pick":
        expenses_list = data["expenses"]
        try:
            idx = int(text.strip()) - 1
            assert 0 <= idx < len(expenses_list)
        except (ValueError, AssertionError):
            return f"Please reply with a number between 1 and {len(expenses_list)}."
        chosen = expenses_list[idx]
        with Session(engine) as session:
            deleted = delete_expense(session, chosen["id"])
        del state_dict[chat_id]
        name = chosen.get("merchant") or chosen.get("description") or "Expense"
        if deleted:
            return f"Deleted {name} ({chosen['amount']:.2f} JD)."
        return f"{name} was already deleted."

    del state_dict[chat_id]
    return "Something went wrong. Please try again."


def _format_sub_updated(updated: RecurringRule | None) -> str:
    """Confirmation line after a subscription edit (the name reveals a wrong fuzzy hit)."""
    if updated is None:
        return "That subscription no longer exists. /subs to see current ones."
    return (
        f"Updated {updated.name} → {updated.amount:.2f} JD, "
        f"due {updated.next_due_date:%d/%m/%Y}.\n/subs to see all."
    )


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
        # Best-effort send: any DB mutation in the step already committed, so a
        # Telegram error here must not 500 — otherwise Telegram retries the
        # webhook and (for the destructive steps) could re-run the action.
        api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                await client.post(api_url, json={"chat_id": chat_id, "text": reply_text})
            except Exception:
                logger.exception("Failed to send conversation reply")
        return {"ok": True}

    parts = message_text.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
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
        elif command in {"/addsubscription", "/addsub"}:
            conversation_state[chat_id] = {"step": "addsub_name", "data": {}}
            reply_text = "What's the subscription name?"
        elif command == "/editsub":
            rules_payload = _active_rules_payload()
            if not rules_payload:
                reply_text = "No subscriptions to edit. /addsub to add one."
            elif args:
                # One-shot: /editsub <name> <amount> [DD/MM/YYYY]
                parsed = parse_editsub_oneshot(args, rules_payload)
                if parsed is None:
                    reply_text = (
                        "Usage: /editsub <name> <amount> [DD/MM/YYYY]\n"
                        "e.g. /editsub Netflix 15.99 27/06/2026"
                    )
                elif not parsed["matches"]:
                    reply_text = f"No subscription matching '{parsed['name_query']}'. /subs to see them."
                elif len(parsed["matches"]) == 1:
                    chosen = parsed["matches"][0]
                    with Session(engine) as session:
                        updated = update_recurring_fields(
                            session,
                            chosen["id"],
                            amount=parsed["amount"],
                            next_due_date=parsed["due_date"],
                        )
                    reply_text = _format_sub_updated(updated)
                else:
                    conversation_state[chat_id] = {
                        "step": "editsub_pick",
                        "data": {
                            "rules": parsed["matches"],
                            "pending_amount": parsed["amount"],
                            "pending_date": parsed["due_date"],
                        },
                    }
                    reply_text = format_subs_numbered(parsed["matches"], "edit")
            else:
                conversation_state[chat_id] = {"step": "editsub_pick", "data": {"rules": rules_payload}}
                reply_text = format_subs_numbered(rules_payload, "edit")
        elif command in {"/delsub", "/removesub"}:
            rules_payload = _active_rules_payload()
            if not rules_payload:
                reply_text = "No subscriptions to delete."
            elif args:
                # One-shot: /delsub <name> — confirm first (fuzzy match could mis-hit).
                matches = match_rules_by_name(args, rules_payload)
                if not matches:
                    reply_text = f"No subscription matching '{args}'. /subs to see them."
                elif len(matches) == 1:
                    chosen = matches[0]
                    conversation_state[chat_id] = {
                        "step": "delsub_confirm",
                        "data": {"rule_id": chosen["id"], "rule_name": chosen["name"]},
                    }
                    reply_text = (
                        f"Delete {chosen['name']} ({chosen['amount']:.2f} JD)? "
                        "Reply 'yes' to confirm, or /cancel."
                    )
                else:
                    conversation_state[chat_id] = {"step": "delsub_pick", "data": {"rules": matches}}
                    reply_text = format_subs_numbered(matches, "delete")
            else:
                conversation_state[chat_id] = {"step": "delsub_pick", "data": {"rules": rules_payload}}
                reply_text = format_subs_numbered(rules_payload, "delete")
        elif command == "/addexpense":
            if args:
                # One-shot: /addexpense <merchant amount category> [DD/MM/YYYY]
                tokens = args.split()
                chosen_date = parse_date_ddmmyyyy(tokens[-1]) if tokens else None
                if chosen_date is not None:
                    tokens = tokens[:-1]
                with Session(engine) as session:
                    category_rows = session.exec(select(Category).order_by(Category.name)).all()
                    category_payload = [{"id": c.id, "name": c.name} for c in category_rows]
                    parsed = parse_expense_text(" ".join(tokens), category_payload)
                    if parsed is None:
                        reply_text = "Couldn't read that. Try: /addexpense coffee 2.5 food 05/06/2026"
                    else:
                        target = chosen_date or _today_jordan()
                        session.add(Expense.model_validate(build_expense_payload(parsed, target)))
                        session.commit()
                        reply_text = format_confirmation(parsed, target)
            else:
                conversation_state[chat_id] = {"step": "addexp_text", "data": {}}
                reply_text = "Send the expense: merchant amount category\ne.g. coffee 2.5 food"
        elif command == "/editexpense":
            expense_payload = _recent_expenses_payload()
            if not expense_payload:
                reply_text = "No expenses to edit yet."
            else:
                conversation_state[chat_id] = {"step": "editexp_pick", "data": {"expenses": expense_payload}}
                reply_text = format_expenses_numbered(expense_payload, "edit")
        elif command == "/delexpense":
            expense_payload = _recent_expenses_payload()
            if not expense_payload:
                reply_text = "No expenses to delete yet."
            else:
                conversation_state[chat_id] = {"step": "delexp_pick", "data": {"expenses": expense_payload}}
                reply_text = format_expenses_numbered(expense_payload, "delete")
        elif command == "/cancel":
            if chat_id in conversation_state:
                del conversation_state[chat_id]
                reply_text = "Cancelled."
            else:
                reply_text = "Nothing to cancel."
        else:
            reply_text = format_help_text()

        # Best-effort send: a one-shot command above may have already committed a
        # mutation (edit/delete/add), so a Telegram error here must not 500 —
        # otherwise Telegram retries the webhook and re-runs it.
        api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                await client.post(api_url, json={"chat_id": chat_id, "text": reply_text})
            except Exception:
                logger.exception("Failed to send command reply")

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
