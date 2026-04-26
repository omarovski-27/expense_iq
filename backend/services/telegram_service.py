import re
from datetime import date


def today_display(target_date: date) -> str:
    return f"{target_date:%a, %b} {target_date.day} {target_date:%Y}"


def format_help_text() -> str:
    return (
        "Formats:\n"
        "merchant amount category: netflix 14.7 bills\n"
        "amount category: 8.5 food\n"
        "merchant amount: coffee 2.5\n"
        "amount only: 14.7 (category defaults to Other)\n\n"
        "Commands:\n"
        "/today - expenses today\n"
        "/month - this month summary\n"
        "/budget - budget status\n"
        "/categories - list all categories"
    )


def format_today_expenses(expenses: list[dict], target_date: date) -> str:
    if not expenses:
        return f"No expenses today for {today_display(target_date)}."

    lines = [f"Expenses for {today_display(target_date)}:"]
    total = 0.0

    for expense in expenses:
        name = expense.get("merchant") or expense.get("description") or "Expense"
        amount = float(expense.get("amount", 0))
        category_name = expense.get("category_name") or "Uncategorized"
        total += amount
        lines.append(f"- {name}: {amount:.2f} JD ({category_name})")

    lines.append("")
    lines.append(f"Total: {total:.2f} JD")
    return "\n".join(lines)


def find_category_id(text: str, categories: list[dict]):
    if not categories:
        raise ValueError("No categories available")

    text_lower = text.lower()
    for category in categories:
        name = category["name"].lower()
        if text_lower in name or name in text_lower:
            return category["id"], category["name"]

    for category in categories:
        if category["name"].lower() == "other":
            return category["id"], "Other"

    return categories[0]["id"], categories[0]["name"]


def parse_expense_text(text: str, categories: list[dict]):
    cleaned = re.sub(r"\b(?:JD|jd)\b|[$€£]", "", text.strip())
    cleaned = cleaned.replace(",", ".")
    tokens = [token for token in cleaned.split() if token]
    if not tokens:
        return None

    amount = None
    amount_index = None
    for index, token in enumerate(tokens):
        try:
            value = float(token.strip())
        except ValueError:
            continue
        if value > 0:
            amount = value
            amount_index = index
            break

    if amount is None or amount_index is None:
        return None

    non_amount_tokens = [token for index, token in enumerate(tokens) if index != amount_index]

    category_id = None
    category_name = None
    category_index = None
    for index, token in enumerate(non_amount_tokens):
        token_lower = token.lower()
        for category in categories:
            category_lower = category["name"].lower()
            if token_lower in category_lower or category_lower in token_lower:
                category_id = category["id"]
                category_name = category["name"]
                category_index = index
                break
        if category_id is not None:
            break

    if category_id is None:
        category_id, category_name = find_category_id("other", categories)
        merchant_tokens = non_amount_tokens
    else:
        merchant_tokens = [
            token for index, token in enumerate(non_amount_tokens) if index != category_index
        ]

    merchant = " ".join(merchant_tokens).strip()

    return {
        "amount": amount,
        "merchant": merchant,
        "category_id": category_id,
        "category_name": category_name,
    }


def build_expense_payload(parsed: dict, target_date: date) -> dict:
    return {
        "amount": parsed["amount"],
        "description": parsed["merchant"] or "Expense",
        "category_id": parsed["category_id"],
        "merchant": parsed["merchant"] or "",
        "date": target_date.isoformat(),
        "is_recurring": False,
        "notes": "",
    }


def format_confirmation(parsed: dict, target_date: date) -> str:
    merchant = parsed["merchant"] or "Expense"
    return (
        f"Added: {merchant} - {parsed['amount']:.2f} JD ({parsed['category_name']})\n"
        f"{today_display(target_date)}\n\n"
        "/today to see all expenses today"
    )