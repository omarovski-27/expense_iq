from contextlib import asynccontextmanager
from datetime import date
import logging

import os

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import Category, Expense
from routers import analytics, budgets, categories, expenses, exports, health, insights, recurring
from services.telegram_service import build_expense_payload, format_confirmation, format_help_text, parse_expense_text


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

    # Process any recurring expenses that became due
    from services.recurring_service import process_recurring_expenses
    with Session(engine) as recurring_session:
        try:
            process_recurring_expenses(recurring_session)
        except Exception:
            logger.exception("Recurring expenses processing failed on startup")

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

    yield  # app runs here


app = FastAPI(
    title="ExpenseIQ API",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
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

    command = message_text.split()[0].lower()
    if command.startswith("/"):
        if command in {"/help", "/categories"}:
            reply_text = format_help_text()
        elif command in {"/today", "/month", "/budget"}:
            reply_text = "Not yet implemented."
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
            today = date.today()
            expense_data = build_expense_payload(parsed, today)
            expense = Expense.model_validate(expense_data)
            session.add(expense)
            session.commit()
            reply_text = format_confirmation(parsed, today)

    api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(api_url, json={"chat_id": chat_id, "text": reply_text})
        response.raise_for_status()

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
