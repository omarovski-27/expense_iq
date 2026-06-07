import re
from datetime import date, datetime


def today_display(target_date: date) -> str:
    return f"{target_date:%a, %b} {target_date.day} {target_date:%Y}"


def format_help_text() -> str:
    return (
        "Log an expense by typing it:\n"
        "merchant amount category: netflix 14.7 bills\n"
        "amount category: 8.5 food\n"
        "merchant amount: coffee 2.5\n"
        "amount only: 14.7 (category defaults to Other)\n\n"
        "Reports:\n"
        "/today - expenses today\n"
        "/week - expenses this week\n"
        "/month - this month summary\n"
        "/max - highest single expense this month\n"
        "/top5 - top 5 expenses this month\n"
        "/budget - budget status\n"
        "/categories - list all categories\n\n"
        "Subscriptions:\n"
        "/subs - list all subscriptions\n"
        "/addsub - add a subscription\n"
        "/editsub - edit one (e.g. /editsub Netflix 15.99 27/06/2026)\n"
        "/delsub - delete a subscription\n\n"
        "Expenses:\n"
        "/addexpense - add an expense (can be backdated)\n"
        "/editexpense - edit a recent expense\n"
        "/delexpense - delete a recent expense\n\n"
        "/cancel - cancel the current action"
    )


def format_max_expense(expense: dict | None, target_date: date) -> str:
    if not expense:
        return f"No expenses this month for {target_date:%B %Y}."
    return (
        f"\U0001f4b8 Highest expense this month: "
        f"{expense['description']} — {expense['amount']:.2f} JOD "
        f"({expense['category_name']}) on {expense['date']}"
    )


def format_top5_expenses(expenses: list[dict], target_date: date) -> str:
    if not expenses:
        return f"No expenses this month for {target_date:%B %Y}."
    lines = [f"\U0001f3c6 Top 5 expenses this month:"]
    for i, exp in enumerate(expenses, 1):
        lines.append(
            f"{i}. {exp['description']} — {exp['amount']:.2f} JOD ({exp['category_name']})"
        )
    return "\n".join(lines)


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


def format_week_expenses(expenses: list[dict], target_date: date) -> str:
    if not expenses:
        return f"No expenses this week for {today_display(target_date)}."

    week_start = target_date.fromordinal(target_date.toordinal() - target_date.weekday())
    week_end = week_start.fromordinal(week_start.toordinal() + 6)

    lines = [
        (
            f"Expenses for {week_start:%b} {week_start.day}"
            f" - {week_end:%b} {week_end.day}, {week_end:%Y}:"
        )
    ]
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


def format_month_expenses(expenses: list[dict], target_date: date) -> str:
    if not expenses:
        return f"No expenses this month for {target_date:%B %Y}."

    category_totals: dict[str, float] = {}
    grand_total = 0.0

    for expense in expenses:
        category_name = expense.get("category_name") or "Uncategorized"
        amount = float(expense.get("amount", 0))
        category_totals[category_name] = category_totals.get(category_name, 0.0) + amount
        grand_total += amount

    lines = [f"Summary for {target_date:%B %Y}:"]
    for category_name, amount in sorted(category_totals.items()):
        lines.append(f"- {category_name}: {amount:.2f} JD")

    lines.append("")
    lines.append(f"Grand total: {grand_total:.2f} JD")
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


def format_subs_list(rules: list[dict]) -> str:
    if not rules:
        return "No subscriptions found. Use /addsubscription to add one."
    lines = ["Subscriptions (sorted by due date):"]
    for r in rules:
        due = r["next_due_date"]
        due_str = f"{due:%d/%m/%Y}" if hasattr(due, "strftime") else str(due)
        lines.append(f"- {r['name']}: {r['amount']:.2f} JD | {r['category_name']} | due {due_str}")
    return "\n".join(lines)


def format_subs_numbered(rules: list[dict], action: str = "edit") -> str:
    """Numbered subscription list for the /editsub and /delsub pick flows."""
    lines = ["Your subscriptions:"]
    for i, r in enumerate(rules, 1):
        due = r["next_due_date"]
        due_str = f"{due:%d/%m/%Y}" if hasattr(due, "strftime") else str(due)
        lines.append(f"{i}. {r['name']} - {r['amount']:.2f} JD (due {due_str})")
    lines.append(f"\nReply with a number to {action} it, or /cancel.")
    return "\n".join(lines)


def format_expenses_numbered(expenses: list[dict], action: str = "edit") -> str:
    """Numbered recent-expense list for the /editexpense and /delexpense flows.

    Each row needs: merchant/description, amount, category_name, date.
    """
    if not expenses:
        return "No expenses found yet. Type one like: coffee 2.5 food"
    lines = ["Recent expenses:"]
    for i, e in enumerate(expenses, 1):
        name = e.get("merchant") or e.get("description") or "Expense"
        category_name = e.get("category_name") or "Uncategorized"
        d = e["date"]
        d_str = f"{d:%b %d}" if hasattr(d, "strftime") else str(d)
        lines.append(f"{i}. {name} - {e['amount']:.2f} JD ({category_name}) - {d_str}")
    lines.append(f"\nReply with a number to {action} it, or /cancel.")
    return "\n".join(lines)


def parse_amount(text: str) -> float | None:
    """Parse a positive amount, tolerating a comma decimal. None if invalid."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    return value if value > 0 else None


def parse_date_ddmmyyyy(text: str) -> date | None:
    """Parse a DD/MM/YYYY date. None if it doesn't match."""
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def match_rules_by_name(query: str, rules: list[dict]) -> list[dict]:
    """Fuzzy-match subscriptions by name. Exact (case-insensitive) wins; else
    substring either direction. Returns all matches (possibly empty)."""
    q = query.lower().strip()
    if not q:
        return []
    exact = [r for r in rules if r["name"].lower() == q]
    if exact:
        return exact
    return [r for r in rules if q in r["name"].lower() or r["name"].lower() in q]


def parse_editsub_oneshot(args: str, rules: list[dict]) -> dict | None:
    """Parse '<name> <amount> [DD/MM/YYYY]' from the right so multi-word names
    work. Returns {"amount", "due_date", "matches"} or None if it can't parse a
    name + amount.
    """
    tokens = args.split()
    if not tokens:
        return None

    due_date = parse_date_ddmmyyyy(tokens[-1])
    if due_date is not None:
        tokens = tokens[:-1]
    if not tokens:
        return None

    amount = parse_amount(tokens[-1])
    if amount is None:
        return None
    tokens = tokens[:-1]
    if not tokens:
        return None

    name_query = " ".join(tokens)
    return {
        "amount": amount,
        "due_date": due_date,
        "matches": match_rules_by_name(name_query, rules),
        "name_query": name_query,
    }