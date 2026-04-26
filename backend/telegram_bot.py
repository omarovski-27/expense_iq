import logging
import os
import sys
import time
import traceback
from datetime import date

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from services.telegram_service import build_expense_payload, format_confirmation, format_help_text, parse_expense_text


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not TELEGRAM_BOT_TOKEN:
    print("TELEGRAM_BOT_TOKEN is not configured.")
    sys.exit(1)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 40
_category_cache = {"data": [], "timestamp": 0.0}


def _friendly_handler_error(exc: Exception) -> str:
    message = str(exc)
    if "Backend unavailable" in message:
        return "Server is starting up, try again in 30 seconds."
    if "Request timed out" in message:
        return "Request timed out. Server waking up. Try again shortly."
    return "Something went wrong. Try again."


async def call_backend(method: str, path: str, data=None):
    url = f"{BACKEND_URL}/api{path}"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.request(method.upper(), url, json=data)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError as exc:
        raise Exception("Backend unavailable - may be waking up") from exc
    except httpx.TimeoutException as exc:
        raise Exception("Request timed out - try again shortly") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        raise Exception(detail or f"Backend request failed with status {exc.response.status_code}") from exc


async def get_categories():
    if time.time() - _category_cache["timestamp"] > 300:
        categories = await call_backend("GET", "/categories")
        _category_cache["data"] = categories
        _category_cache["timestamp"] = time.time()
    return _category_cache["data"]


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        await update.message.reply_text(
            "ExpenseIQ ready.\n\n"
            "Send expenses like:\n"
            "netflix 14.7 bills\n"
            "lunch 8.5 food\n"
            "petrol 20 transport\n\n"
            "/help for all commands"
        )
    except Exception as exc:
        logger.error("start_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text(_friendly_handler_error(exc))


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        await update.message.reply_text(format_help_text())
    except Exception as exc:
        logger.error("help_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text(_friendly_handler_error(exc))


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        today = date.today()
        expenses = await call_backend(
            "GET",
            f"/expenses?month={today.month}&year={today.year}&limit=200",
        )
        today_expenses = [expense for expense in expenses if expense.get("date") == today.isoformat()]

        if not today_expenses:
            await update.message.reply_text("No expenses today yet.")
            return

        lines = []
        total = 0.0
        for index, expense in enumerate(today_expenses, start=1):
            description = expense.get("merchant") or expense.get("description") or "Expense"
            amount = float(expense.get("amount", 0))
            total += amount
            category = (expense.get("category") or {}).get("name")
            category_suffix = f" ({category})" if category else ""
            lines.append(f"{index}. {description} - {amount:.2f} JD{category_suffix}")

        lines.append("--------------------")
        lines.append(f"Total: {total:.2f} JD")
        await update.message.reply_text("\n".join(lines))
    except Exception as exc:
        logger.error("today_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text(_friendly_handler_error(exc))


async def month_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        today = date.today()
        summary = await call_backend(
            "GET",
            f"/analytics/summary?month={today.month}&year={today.year}",
        )
        month_name = today.strftime("%B %Y")
        message = (
            f"{month_name}\n"
            f"Total: {float(summary.get('total_this_month', 0)):.2f} JD\n"
            f"Daily average: {float(summary.get('daily_average', 0)):.2f} JD\n"
            f"MoM change: {float(summary.get('mom_change_percent', 0)):.1f}%\n"
            f"Budget used: {float(summary.get('budget_used_percent', 0)):.1f}%"
        )
        await update.message.reply_text(message)
    except Exception:
        logger.error("month_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text("Could not load summary.")


async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        today = date.today()
        budgets = await call_backend(
            "GET",
            f"/budgets/status?month={today.month}&year={today.year}",
        )
        if not budgets:
            await update.message.reply_text("No budgets set. Configure them in the app.")
            return

        status_map = {
            "on_track": "OK",
            "warning": "WARNING",
            "over_budget": "OVER",
        }
        lines = []
        for item in budgets:
            category_name = item["category"]["name"]
            spent = float(item.get("spent", 0))
            limit = float(item.get("monthly_limit", 0))
            percentage = float(item.get("percentage", 0))
            status_word = status_map.get(item.get("status"), "OK")
            lines.append(
                f"{category_name}: {spent:.2f}/{limit:.2f} JD, {percentage:.1f}% - {status_word}"
            )

        await update.message.reply_text("\n".join(lines))
    except Exception as exc:
        logger.error("budget_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text(_friendly_handler_error(exc))


async def categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        categories = await call_backend("GET", "/categories")
        names = ", ".join(category["name"] for category in categories)
        await update.message.reply_text(names or "No categories found.")
    except Exception as exc:
        logger.error("categories_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text(_friendly_handler_error(exc))


async def expense_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        message_text = (update.message.text or "").strip()
        categories = await get_categories()
        parsed = parse_expense_text(message_text, categories)
        if parsed is None:
            await update.message.reply_text(format_help_text())
            return

        today = date.today()
        payload = build_expense_payload(parsed, today)

        try:
            await call_backend("POST", "/expenses", payload)
        except Exception:
            await update.message.reply_text("Could not save - server may be waking up. Try again shortly.")
            return

        await update.message.reply_text(format_confirmation(parsed, today))
    except Exception as exc:
        logger.error("expense_handler failed\n%s", traceback.format_exc())
        await update.message.reply_text(format_help_text())


async def post_init(application: Application):
    try:
        await application.bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text=(
                "ExpenseIQ bot online.\n"
                f"Backend: {BACKEND_URL}\n"
                "/help for commands."
            ),
        )
    except Exception:
        logger.error("Failed to send startup message\n%s", traceback.format_exc())


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("today", today_handler))
    application.add_handler(CommandHandler("month", month_handler))
    application.add_handler(CommandHandler("budget", budget_handler))
    application.add_handler(CommandHandler("categories", categories_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, expense_handler))
    application.run_polling(allowed_updates=Update.ALL_TYPES)