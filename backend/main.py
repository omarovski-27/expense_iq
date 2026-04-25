from contextlib import asynccontextmanager
import logging

import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import Category
from routers import analytics, budgets, categories, expenses, exports, health, insights, recurring


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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
