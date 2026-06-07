"""
Telegram bot webhook tests.

Covers:
- Auth / security checks
- Command routing (/help, /today, /week, /month, /subs)
- Multi-step conversation flows (/addsubscription, /removesub)
- Natural-language expense parsing (pure functions)
- Conversation state isolation
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from models import Category, Expense, RecurringRule
from services.telegram_service import find_category_id, parse_expense_text
from tests.conftest import ALLOWED_USER_ID, TEST_CHAT_ID, TODAY, make_tg_payload


# Freeze "today" (Jordan time) for the whole module so the date-filtered
# commands (/today, /week, /month, /max, /top5) and the rows seeded below agree
# on the calendar day. Without this, fixtures seed with the host's local (UTC)
# date while handlers filter by Jordan-local today (UTC+3), so the suite flakes
# in the 21:00–24:00 UTC window and at month boundaries.
FROZEN_TODAY = date.fromisoformat(TODAY)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _freeze_jordan_today(monkeypatch):
    """Pin today_jordan() to FROZEN_TODAY in every module that calls it.

    today_jordan is imported as the module-level name `_today_jordan` in both
    main and the recurring service, so patch it in each place — rebinding
    tz.today_jordan wouldn't affect those already-bound aliases.
    """
    import main as main_module
    import services.recurring_service as recurring_module

    monkeypatch.setattr(main_module, "_today_jordan", lambda: FROZEN_TODAY)
    monkeypatch.setattr(recurring_module, "_today_jordan", lambda: FROZEN_TODAY)


@pytest.fixture()
def mock_tg():
    """Replace httpx.AsyncClient in main with a mock that captures .post() calls."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        yield mock_client


def _last_text(mock_tg) -> str:
    """Return the `text` field from the last Telegram sendMessage call."""
    calls = mock_tg.post.call_args_list
    assert calls, "No Telegram message was sent"
    return calls[-1].kwargs["json"]["text"]


def _all_texts(mock_tg) -> list[str]:
    return [c.kwargs["json"]["text"] for c in mock_tg.post.call_args_list]


def _post(telegram_client, mock_tg, text: str, user_id: int = ALLOWED_USER_ID):
    """Send a webhook payload and return (HTTP response, last Telegram text)."""
    mock_tg.post.reset_mock()
    r = telegram_client.post("/webhook/telegram", json=make_tg_payload(text, user_id=user_id))
    return r, _last_text(mock_tg)


# ─────────────────────────────────────────────────────────────────────────────
# Auth / security
# ─────────────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_unauthorized_user_ignored(self, telegram_client, mock_tg):
        r = telegram_client.post(
            "/webhook/telegram",
            json=make_tg_payload("/help", user_id=99999),
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        mock_tg.post.assert_not_called()

    def test_missing_message_key_ok(self, telegram_client, mock_tg):
        r = telegram_client.post("/webhook/telegram", json={"update_id": 1})
        assert r.status_code == 200
        mock_tg.post.assert_not_called()

    def test_empty_text_ignored(self, telegram_client, mock_tg):
        r = telegram_client.post(
            "/webhook/telegram",
            json={
                "message": {
                    "from": {"id": ALLOWED_USER_ID},
                    "chat": {"id": TEST_CHAT_ID},
                    "text": "",
                }
            },
        )
        assert r.status_code == 200
        mock_tg.post.assert_not_called()

    def test_no_telegram_token_503(self, telegram_client, mock_tg):
        import os
        original = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        try:
            r = telegram_client.post(
                "/webhook/telegram", json=make_tg_payload("/help")
            )
            assert r.status_code == 503
        finally:
            if original:
                os.environ["TELEGRAM_BOT_TOKEN"] = original


# ─────────────────────────────────────────────────────────────────────────────
# Command routing
# ─────────────────────────────────────────────────────────────────────────────

class TestCommandRouting:
    def test_help_command(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/help")
        assert "/today" in text
        assert "/subs" in text
        assert "/addsub" in text
        assert "/editsub" in text
        assert "/delsub" in text
        assert "/addexpense" in text
        assert "/editexpense" in text
        assert "/delexpense" in text

    def test_categories_command(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/categories")
        assert "/today" in text  # /categories shows the same help text

    def test_unknown_command_shows_help(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/doesnotexist")
        assert "/today" in text

    def test_today_no_expenses(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/today")
        assert "no expenses" in text.lower()

    def test_week_no_expenses(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/week")
        assert "no expenses" in text.lower()

    def test_month_no_expenses(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/month")
        assert "no expenses" in text.lower()

    def test_budget_not_implemented(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/budget")
        assert "not yet implemented" in text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# /today, /week, /month with DB data
# ─────────────────────────────────────────────────────────────────────────────

class TestDateCommands:
    def _seed_today(self, engine):
        with Session(engine) as s:
            cats = s.exec(__import__("sqlmodel").select(Category)).all()
            food_id = next(c.id for c in cats if c.name == "Food")
            s.add(Expense(amount=12.5, description="Lunch", date=FROZEN_TODAY, category_id=food_id))
            s.commit()

    def test_today_shows_expense(self, telegram_client, mock_tg, engine):
        self._seed_today(engine)
        _, text = _post(telegram_client, mock_tg, "/today")
        assert "12.5" in text or "12.50" in text
        assert "Lunch" in text

    def test_today_shows_total(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            s.add(Expense(amount=10.0, description="A", date=FROZEN_TODAY))
            s.add(Expense(amount=5.0, description="B", date=FROZEN_TODAY))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/today")
        assert "15" in text  # total

    def test_week_shows_expense_from_this_week(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            s.add(Expense(amount=8.0, description="WeekExpense", date=FROZEN_TODAY))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/week")
        assert "WeekExpense" in text

    def test_month_shows_category_summary(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            cats = s.exec(__import__("sqlmodel").select(Category)).all()
            food_id = next(c.id for c in cats if c.name == "Food")
            s.add(Expense(
                amount=25.0, description="Groceries",
                date=date(FROZEN_TODAY.year, FROZEN_TODAY.month, 1),
                category_id=food_id,
            ))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/month")
        assert "Food" in text
        assert "25" in text


# ─────────────────────────────────────────────────────────────────────────────
# /subs command
# ─────────────────────────────────────────────────────────────────────────────

class TestSubsCommand:
    def test_subs_empty(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/subs")
        assert "no subscriptions" in text.lower()

    def test_subs_shows_rules(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            cats = s.exec(__import__("sqlmodel").select(Category)).all()
            ent_id = next(c.id for c in cats if c.name == "Entertainment")
            s.add(RecurringRule(
                name="Netflix",
                amount=14.99,
                frequency="monthly",
                next_due_date=date(2026, 6, 1),
                category_id=ent_id,
                is_active=True,
            ))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/subs")
        assert "Netflix" in text
        assert "14.99" in text

    def test_subs_auto_charges_due_rule(self, telegram_client, mock_tg, engine):
        """A rule due today is charged when /subs is called."""
        with Session(engine) as s:
            s.add(RecurringRule(
                name="AutoCharge",
                amount=9.99,
                frequency="monthly",
                next_due_date=FROZEN_TODAY,
                is_active=True,
            ))
            s.commit()
        mock_tg.post.reset_mock()
        telegram_client.post("/webhook/telegram", json=make_tg_payload("/subs"))
        texts = _all_texts(mock_tg)
        # One notification + the list
        assert any("Auto-charged" in t and "AutoCharge" in t for t in texts)


# ─────────────────────────────────────────────────────────────────────────────
# /addsubscription multi-step flow
# ─────────────────────────────────────────────────────────────────────────────

class TestAddSubscriptionFlow:
    def test_full_flow(self, telegram_client, mock_tg, engine):
        # Step 1: start
        _, t = _post(telegram_client, mock_tg, "/addsubscription")
        assert "subscription name" in t.lower()

        # Step 2: name
        _, t = _post(telegram_client, mock_tg, "Netflix")
        assert "how much" in t.lower()

        # Step 3: amount
        _, t = _post(telegram_client, mock_tg, "14.7")
        assert "category" in t.lower()

        # Step 4: category
        _, t = _post(telegram_client, mock_tg, "entertainment")
        assert "due date" in t.lower()

        # Step 5: date
        _, t = _post(telegram_client, mock_tg, "01/06/2026")
        assert "saved" in t.lower() or "netflix" in t.lower()

        # Verify the rule was persisted
        with Session(engine) as s:
            rules = s.exec(__import__("sqlmodel").select(RecurringRule)).all()
        assert len(rules) == 1
        assert rules[0].name == "Netflix"
        assert rules[0].amount == 14.7

    def test_invalid_amount_reprompts(self, telegram_client, mock_tg):
        _post(telegram_client, mock_tg, "/addsubscription")
        _post(telegram_client, mock_tg, "MyService")  # name step
        _, t = _post(telegram_client, mock_tg, "not-a-number")
        assert "invalid" in t.lower()
        # State should still be waiting for amount
        _, t2 = _post(telegram_client, mock_tg, "5.0")
        assert "category" in t2.lower()

    def test_invalid_date_reprompts(self, telegram_client, mock_tg, engine):
        _post(telegram_client, mock_tg, "/addsubscription")
        _post(telegram_client, mock_tg, "ServiceX")
        _post(telegram_client, mock_tg, "9.99")
        _post(telegram_client, mock_tg, "other")
        _, t = _post(telegram_client, mock_tg, "not-a-date")
        assert "invalid" in t.lower() or "dd/mm" in t.lower()
        # Should still be waiting for date
        _, t2 = _post(telegram_client, mock_tg, "15/06/2026")
        assert "saved" in t2.lower() or "servicex" in t2.lower()

    def test_command_mid_flow_breaks_state(self, telegram_client, mock_tg):
        """Sending a / command during a flow resets it and processes the command."""
        _post(telegram_client, mock_tg, "/addsubscription")
        _post(telegram_client, mock_tg, "Netflix")  # in name-waiting state
        # Send a slash command — should process /help, not continue flow
        _, t = _post(telegram_client, mock_tg, "/help")
        assert "/today" in t


# ─────────────────────────────────────────────────────────────────────────────
# /removesub flow
# ─────────────────────────────────────────────────────────────────────────────

class TestRemoveSubFlow:
    def _add_rule(self, engine, name="SpotifyTest", amount=5.99):
        with Session(engine) as s:
            s.add(RecurringRule(
                name=name,
                amount=amount,
                frequency="monthly",
                next_due_date=date(2026, 6, 1),
                is_active=True,
            ))
            s.commit()

    def test_removesub_empty(self, telegram_client, mock_tg):
        _, t = _post(telegram_client, mock_tg, "/removesub")
        assert "no subscriptions" in t.lower()

    def test_removesub_shows_list(self, telegram_client, mock_tg, engine):
        self._add_rule(engine, "SpotifyTest")
        _, t = _post(telegram_client, mock_tg, "/removesub")
        assert "SpotifyTest" in t
        assert "1." in t  # numbered list

    def test_removesub_deletes_rule(self, telegram_client, mock_tg, engine):
        self._add_rule(engine, "ToDelete")
        _post(telegram_client, mock_tg, "/removesub")  # shows list
        _, t = _post(telegram_client, mock_tg, "1")    # pick #1
        assert "removed" in t.lower() or "todelete" in t.lower()

        # Rule should be gone
        with Session(engine) as s:
            rules = s.exec(__import__("sqlmodel").select(RecurringRule)).all()
        assert len(rules) == 0

    def test_removesub_invalid_number(self, telegram_client, mock_tg, engine):
        self._add_rule(engine, "OneSub")
        _post(telegram_client, mock_tg, "/removesub")
        _, t = _post(telegram_client, mock_tg, "999")  # out of range
        assert "number" in t.lower() or "between" in t.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Free-form expense parsing (pure function tests — no DB or HTTP needed)
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = [
    {"id": 1, "name": "Food"},
    {"id": 2, "name": "Entertainment"},
    {"id": 3, "name": "Bills"},
    {"id": 4, "name": "Other"},
]


class TestParseExpenseText:
    def test_merchant_amount_category(self):
        r = parse_expense_text("coffee 2.5 food", CATEGORIES)
        assert r is not None
        assert r["amount"] == 2.5
        assert r["merchant"] == "coffee"
        assert r["category_name"] == "Food"

    def test_amount_category(self):
        r = parse_expense_text("8.5 food", CATEGORIES)
        assert r is not None
        assert r["amount"] == 8.5
        assert r["category_name"] == "Food"

    def test_merchant_amount(self):
        r = parse_expense_text("uber 3", CATEGORIES)
        assert r is not None
        assert r["amount"] == 3.0
        assert r["merchant"] == "uber"
        assert r["category_name"] == "Other"

    def test_amount_only(self):
        r = parse_expense_text("14.7", CATEGORIES)
        assert r is not None
        assert r["amount"] == 14.7
        assert r["merchant"] == ""

    def test_netflix_entertainment(self):
        r = parse_expense_text("netflix 5 entertainment", CATEGORIES)
        assert r is not None
        assert r["amount"] == 5.0
        assert r["merchant"] == "netflix"
        assert r["category_name"] == "Entertainment"

    def test_strips_jod_currency(self):
        r = parse_expense_text("coffee 2.5 JD food", CATEGORIES)
        assert r is not None
        assert r["amount"] == 2.5

    def test_no_number_returns_none(self):
        assert parse_expense_text("blah blah", CATEGORIES) is None

    def test_empty_string_returns_none(self):
        assert parse_expense_text("", CATEGORIES) is None

    def test_negative_number_not_parsed_as_amount(self):
        # -5 should not be treated as a valid positive amount
        r = parse_expense_text("-5", CATEGORIES)
        assert r is None

    def test_comma_decimal(self):
        r = parse_expense_text("lunch 12,50", CATEGORIES)
        assert r is not None
        assert r["amount"] == 12.5

    def test_dollar_sign_stripped(self):
        r = parse_expense_text("$10 food", CATEGORIES)
        assert r is not None
        assert r["amount"] == 10.0


class TestFindCategoryId:
    def test_exact_match(self):
        cid, name = find_category_id("food", CATEGORIES)
        assert name == "Food"

    def test_partial_match(self):
        cid, name = find_category_id("entertain", CATEGORIES)
        assert name == "Entertainment"

    def test_fallback_to_other(self):
        cid, name = find_category_id("xyz_unknown_cat", CATEGORIES)
        assert name == "Other"


# ─────────────────────────────────────────────────────────────────────────────
# Free-form expense via webhook
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookExpenseParsing:
    def test_valid_expense_saved(self, telegram_client, mock_tg, engine):
        _, t = _post(telegram_client, mock_tg, "coffee 3.5 food")
        assert "3.5" in t or "3.50" in t
        assert "coffee" in t.lower()

        with Session(engine) as s:
            exps = s.exec(__import__("sqlmodel").select(Expense)).all()
        assert len(exps) == 1
        assert exps[0].amount == 3.5

    def test_invalid_text_shows_help(self, telegram_client, mock_tg):
        _, t = _post(telegram_client, mock_tg, "not parseable at all")
        assert "/today" in t  # help text shown

    def test_just_a_number_saves_expense(self, telegram_client, mock_tg, engine):
        _, t = _post(telegram_client, mock_tg, "5.0")
        assert "5" in t
        with Session(engine) as s:
            exps = s.exec(__import__("sqlmodel").select(Expense)).all()
        assert len(exps) == 1
        assert exps[0].amount == 5.0


# ─────────────────────────────────────────────────────────────────────────────
# /max command
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxCommand:
    def test_max_no_expenses(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/max")
        assert "no expenses" in text.lower()

    def test_max_returns_highest(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            s.add(Expense(amount=15.0, description="Cheap", date=FROZEN_TODAY))
            s.add(Expense(amount=250.0, description="Expensive", date=FROZEN_TODAY))
            s.add(Expense(amount=40.0, description="Medium", date=FROZEN_TODAY))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/max")
        assert "250" in text
        assert "Expensive" in text

    def test_max_includes_category(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            cats = s.exec(__import__("sqlmodel").select(Category)).all()
            food_id = next(c.id for c in cats if c.name == "Food")
            s.add(Expense(amount=180.0, description="BigMeal", date=FROZEN_TODAY, category_id=food_id))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/max")
        assert "Food" in text
        assert "180" in text

    def test_max_ignores_previous_month(self, telegram_client, mock_tg, engine):
        today = FROZEN_TODAY
        prev_month = date(
            today.year if today.month > 1 else today.year - 1,
            today.month - 1 if today.month > 1 else 12,
            1,
        )
        with Session(engine) as s:
            s.add(Expense(amount=999.0, description="OldExpense", date=prev_month))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/max")
        assert "no expenses" in text.lower()

    def test_max_in_help(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/help")
        assert "/max" in text


# ─────────────────────────────────────────────────────────────────────────────
# /top5 command
# ─────────────────────────────────────────────────────────────────────────────

class TestTop5Command:
    def test_top5_no_expenses(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/top5")
        assert "no expenses" in text.lower()

    def test_top5_returns_sorted_by_amount(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            for i, amount in enumerate([10.0, 50.0, 30.0, 20.0, 40.0], 1):
                s.add(Expense(amount=amount, description=f"Exp{i}", date=FROZEN_TODAY))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/top5")
        assert "50" in text
        assert "40" in text
        # verify descending order: 50 appears before 10
        assert text.index("50") < text.index("10")

    def test_top5_limited_to_5(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            for i in range(8):
                s.add(Expense(amount=float(i + 1) * 10, description=f"Item{i}", date=FROZEN_TODAY))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/top5")
        # Only 5 numbered entries
        assert "1." in text
        assert "5." in text
        assert "6." not in text

    def test_top5_fewer_than_5(self, telegram_client, mock_tg, engine):
        with Session(engine) as s:
            s.add(Expense(amount=100.0, description="Only", date=FROZEN_TODAY))
            s.add(Expense(amount=50.0, description="Two", date=FROZEN_TODAY))
            s.commit()
        _, text = _post(telegram_client, mock_tg, "/top5")
        assert "1." in text
        assert "2." in text
        assert "3." not in text

    def test_top5_in_help(self, telegram_client, mock_tg):
        _, text = _post(telegram_client, mock_tg, "/help")
        assert "/top5" in text


# ─────────────────────────────────────────────────────────────────────────────
# /editsub flow
# ─────────────────────────────────────────────────────────────────────────────

def _add_rule(engine, name="Netflix", amount=14.7, due=date(2026, 6, 1)):
    with Session(engine) as s:
        r = RecurringRule(
            name=name, amount=amount, frequency="monthly",
            next_due_date=due, is_active=True,
        )
        s.add(r)
        s.commit()
        s.refresh(r)
        return r.id


def _only_rule(engine) -> RecurringRule:
    with Session(engine) as s:
        return s.exec(__import__("sqlmodel").select(RecurringRule)).first()


def _only_expense(engine) -> Expense:
    with Session(engine) as s:
        return s.exec(__import__("sqlmodel").select(Expense)).first()


def _all_rules(engine):
    with Session(engine) as s:
        return s.exec(__import__("sqlmodel").select(RecurringRule)).all()


def _all_expenses(engine):
    with Session(engine) as s:
        return s.exec(__import__("sqlmodel").select(Expense)).all()


class TestEditSubFlow:
    def test_editsub_empty(self, telegram_client, mock_tg):
        _, t = _post(telegram_client, mock_tg, "/editsub")
        assert "no subscriptions" in t.lower()

    def test_editsub_guided_updates_amount_and_date(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix", 14.7)
        _, t = _post(telegram_client, mock_tg, "/editsub")
        assert "Netflix" in t and "1." in t
        _, t = _post(telegram_client, mock_tg, "1")
        assert "amount" in t.lower()
        _, t = _post(telegram_client, mock_tg, "20")
        assert "due date" in t.lower()
        _, t = _post(telegram_client, mock_tg, "15/07/2026")
        assert "updated" in t.lower()
        rule = _only_rule(engine)
        assert rule.amount == 20
        assert rule.next_due_date == date(2026, 7, 15)

    def test_editsub_skip_keeps_amount(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Spotify", 5.99, date(2026, 6, 10))
        _post(telegram_client, mock_tg, "/editsub")
        _post(telegram_client, mock_tg, "1")
        _, t = _post(telegram_client, mock_tg, "skip")       # keep amount
        assert "due date" in t.lower()
        _post(telegram_client, mock_tg, "20/06/2026")        # change date only
        rule = _only_rule(engine)
        assert rule.amount == 5.99
        assert rule.next_due_date == date(2026, 6, 20)

    def test_editsub_invalid_amount_reprompts(self, telegram_client, mock_tg, engine):
        _add_rule(engine)
        _post(telegram_client, mock_tg, "/editsub")
        _post(telegram_client, mock_tg, "1")
        _, t = _post(telegram_client, mock_tg, "abc")
        assert "invalid" in t.lower()

    def test_editsub_oneshot_amount_and_date(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix", 14.7, date(2026, 6, 1))
        _, t = _post(telegram_client, mock_tg, "/editsub Netflix 19.99 27/06/2026")
        assert "updated" in t.lower()
        rule = _only_rule(engine)
        assert rule.amount == 19.99
        assert rule.next_due_date == date(2026, 6, 27)

    def test_editsub_oneshot_amount_only_keeps_date(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix", 14.7, date(2026, 6, 1))
        _post(telegram_client, mock_tg, "/editsub Netflix 19.99")
        rule = _only_rule(engine)
        assert rule.amount == 19.99
        assert rule.next_due_date == date(2026, 6, 1)

    def test_editsub_oneshot_multiword_name(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix Premium", 14.7, date(2026, 6, 1))
        _post(telegram_client, mock_tg, "/editsub Netflix Premium 22")
        rule = _only_rule(engine)
        assert rule.amount == 22

    def test_editsub_oneshot_no_match(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix")
        _, t = _post(telegram_client, mock_tg, "/editsub Hulu 10")
        assert "no subscription matching" in t.lower()


# ─────────────────────────────────────────────────────────────────────────────
# /delsub flow
# ─────────────────────────────────────────────────────────────────────────────

class TestDelSubFlow:
    def test_delsub_empty(self, telegram_client, mock_tg):
        _, t = _post(telegram_client, mock_tg, "/delsub")
        assert "no subscriptions" in t.lower()

    def test_delsub_guided_deletes(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "ToDelete")
        _, t = _post(telegram_client, mock_tg, "/delsub")
        assert "ToDelete" in t and "1." in t
        _, t = _post(telegram_client, mock_tg, "1")
        assert "removed" in t.lower()
        assert _all_rules(engine) == []

    def test_delsub_oneshot_requires_confirm(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix")
        _, t = _post(telegram_client, mock_tg, "/delsub Netflix")
        assert "yes" in t.lower()
        assert len(_all_rules(engine)) == 1          # not deleted yet
        _, t = _post(telegram_client, mock_tg, "yes")
        assert "removed" in t.lower()
        assert _all_rules(engine) == []

    def test_delsub_oneshot_cancel_keeps_rule(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix")
        _post(telegram_client, mock_tg, "/delsub Netflix")
        _, t = _post(telegram_client, mock_tg, "no")
        assert "cancel" in t.lower()
        assert len(_all_rules(engine)) == 1

    def test_delsub_preserves_linked_expense_and_nulls_fk(self, telegram_client, mock_tg, engine):
        """The bug fix: deleting a subscription must keep its generated expenses
        (recurring_id nulled), never orphan or lose them."""
        rule_id = _add_rule(engine, "Gym", 30.0)
        with Session(engine) as s:
            s.add(Expense(
                amount=30.0, description="Gym", date=FROZEN_TODAY,
                is_recurring=True, recurring_id=rule_id,
            ))
            s.commit()
        _post(telegram_client, mock_tg, "/delsub")
        _post(telegram_client, mock_tg, "1")
        exps = _all_expenses(engine)
        assert len(exps) == 1                        # expense preserved
        assert exps[0].recurring_id is None          # FK nulled, not dangling
        assert _all_rules(engine) == []


# ─────────────────────────────────────────────────────────────────────────────
# /addexpense flow
# ─────────────────────────────────────────────────────────────────────────────

class TestAddExpenseFlow:
    def test_addexpense_oneshot_backdated(self, telegram_client, mock_tg, engine):
        _, t = _post(telegram_client, mock_tg, "/addexpense coffee 2.5 food 05/06/2026")
        assert "coffee" in t.lower()
        exp = _only_expense(engine)
        assert exp.amount == 2.5
        assert exp.date == date(2026, 6, 5)

    def test_addexpense_oneshot_defaults_today(self, telegram_client, mock_tg, engine):
        _post(telegram_client, mock_tg, "/addexpense lunch 8 food")
        assert _only_expense(engine).date == FROZEN_TODAY

    def test_addexpense_guided_with_date(self, telegram_client, mock_tg, engine):
        _, t = _post(telegram_client, mock_tg, "/addexpense")
        assert "expense" in t.lower()
        _, t = _post(telegram_client, mock_tg, "taxi 3 transport")
        assert "date" in t.lower()
        _post(telegram_client, mock_tg, "01/06/2026")
        exp = _only_expense(engine)
        assert exp.amount == 3
        assert exp.date == date(2026, 6, 1)

    def test_addexpense_guided_today(self, telegram_client, mock_tg, engine):
        _post(telegram_client, mock_tg, "/addexpense")
        _post(telegram_client, mock_tg, "snack 1.5 food")
        _post(telegram_client, mock_tg, "today")
        assert _only_expense(engine).date == FROZEN_TODAY


# ─────────────────────────────────────────────────────────────────────────────
# /editexpense flow
# ─────────────────────────────────────────────────────────────────────────────

def _add_expense(engine, amount=2.5, desc="coffee", cat="Food", when=None):
    with Session(engine) as s:
        cats = s.exec(__import__("sqlmodel").select(Category)).all()
        cid = next(c.id for c in cats if c.name == cat)
        e = Expense(
            amount=amount, description=desc, merchant=desc,
            date=when or FROZEN_TODAY, category_id=cid,
        )
        s.add(e)
        s.commit()
        s.refresh(e)
        return e.id


class TestEditExpenseFlow:
    def test_editexpense_empty(self, telegram_client, mock_tg):
        _, t = _post(telegram_client, mock_tg, "/editexpense")
        assert "no expenses" in t.lower()

    def test_editexpense_updates_amount(self, telegram_client, mock_tg, engine):
        _add_expense(engine, 2.5, "coffee")
        _, t = _post(telegram_client, mock_tg, "/editexpense")
        assert "coffee" in t.lower() and "1." in t
        _, t = _post(telegram_client, mock_tg, "1")
        assert "amount" in t.lower()
        _, t = _post(telegram_client, mock_tg, "9")
        assert "category" in t.lower()
        _, t = _post(telegram_client, mock_tg, "skip")
        assert "date" in t.lower()
        _, t = _post(telegram_client, mock_tg, "skip")
        assert "updated" in t.lower()
        assert _only_expense(engine).amount == 9

    def test_editexpense_changes_category_and_date(self, telegram_client, mock_tg, engine):
        _add_expense(engine, 2.5, "coffee", "Food")
        _post(telegram_client, mock_tg, "/editexpense")
        _post(telegram_client, mock_tg, "1")
        _post(telegram_client, mock_tg, "skip")          # keep amount
        _post(telegram_client, mock_tg, "transport")     # new category
        _post(telegram_client, mock_tg, "20/06/2026")    # new date
        with Session(engine) as s:
            exp = s.exec(__import__("sqlmodel").select(Expense)).first()
            cat = s.get(Category, exp.category_id)
        assert exp.amount == 2.5                          # unchanged
        assert exp.date == date(2026, 6, 20)
        assert cat.name == "Transport"


# ─────────────────────────────────────────────────────────────────────────────
# /delexpense flow
# ─────────────────────────────────────────────────────────────────────────────

class TestDelExpenseFlow:
    def test_delexpense_empty(self, telegram_client, mock_tg):
        _, t = _post(telegram_client, mock_tg, "/delexpense")
        assert "no expenses" in t.lower()

    def test_delexpense_deletes(self, telegram_client, mock_tg, engine):
        _add_expense(engine, 5.0, "snack")
        _, t = _post(telegram_client, mock_tg, "/delexpense")
        assert "snack" in t.lower() and "1." in t
        _, t = _post(telegram_client, mock_tg, "1")
        assert "deleted" in t.lower()
        assert _all_expenses(engine) == []

    def test_delexpense_invalid_number(self, telegram_client, mock_tg, engine):
        _add_expense(engine, 5.0, "snack")
        _post(telegram_client, mock_tg, "/delexpense")
        _, t = _post(telegram_client, mock_tg, "999")
        assert "between" in t.lower() or "number" in t.lower()
        assert len(_all_expenses(engine)) == 1           # nothing deleted


# ─────────────────────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelFlow:
    def test_cancel_clears_active_flow(self, telegram_client, mock_tg, engine):
        _add_rule(engine, "Netflix")
        _post(telegram_client, mock_tg, "/editsub")          # enter a flow
        _, t = _post(telegram_client, mock_tg, "/cancel")
        assert "cancel" in t.lower()
        # State cleared → cancelling again reports nothing to cancel
        _, t = _post(telegram_client, mock_tg, "/cancel")
        assert "nothing to cancel" in t.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Service-layer mutation helpers (single source of truth for Telegram + API)
# ─────────────────────────────────────────────────────────────────────────────

class TestMutationHelpers:
    def test_delete_recurring_rule_nulls_fk(self, engine):
        from services.recurring_service import delete_recurring_rule
        with Session(engine) as s:
            r = RecurringRule(
                name="Gym", amount=30, frequency="monthly",
                next_due_date=date(2026, 6, 1), is_active=True,
            )
            s.add(r)
            s.commit()
            s.refresh(r)
            s.add(Expense(
                amount=30, description="Gym", date=FROZEN_TODAY,
                is_recurring=True, recurring_id=r.id,
            ))
            s.commit()
            assert delete_recurring_rule(s, r.id) is True
            exps = s.exec(__import__("sqlmodel").select(Expense)).all()
            assert len(exps) == 1 and exps[0].recurring_id is None
            assert delete_recurring_rule(s, r.id) is False   # already gone → no-op

    def test_update_recurring_fields_partial(self, engine):
        from services.recurring_service import update_recurring_fields
        with Session(engine) as s:
            r = RecurringRule(
                name="Netflix", amount=14.7, frequency="monthly",
                next_due_date=date(2026, 6, 1), is_active=True,
            )
            s.add(r)
            s.commit()
            s.refresh(r)
            updated = update_recurring_fields(s, r.id, amount=20)
            assert updated.amount == 20
            assert updated.next_due_date == date(2026, 6, 1)   # untouched
            assert update_recurring_fields(s, 999, amount=5) is None

    def test_update_expense_fields_partial(self, engine):
        from services.expense_service import update_expense_fields
        with Session(engine) as s:
            e = Expense(amount=2.5, description="coffee", date=FROZEN_TODAY)
            s.add(e)
            s.commit()
            s.refresh(e)
            updated = update_expense_fields(s, e.id, amount=9)
            assert updated.amount == 9
            assert updated.description == "coffee"              # untouched

    def test_delete_expense_helper(self, engine):
        from services.expense_service import delete_expense
        with Session(engine) as s:
            e = Expense(amount=2.5, description="coffee", date=FROZEN_TODAY)
            s.add(e)
            s.commit()
            s.refresh(e)
            assert delete_expense(s, e.id) is True
            assert delete_expense(s, e.id) is False             # already gone → no-op
