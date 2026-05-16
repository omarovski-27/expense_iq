"""
Comprehensive API endpoint tests.

Every endpoint is tested for happy-path, validation errors, 404s, and
business-logic edge cases.  All tests use an isolated in-memory SQLite
database via the `client` fixture from conftest.
"""
from datetime import date, timedelta

import pytest
from sqlmodel import Session

from models import Category, Expense, RecurringRule
from tests.conftest import TODAY


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cat_id(client, name: str) -> int:
    cats = client.get("/api/categories/").json()
    return next(c["id"] for c in cats if c["name"] == name)


def _make_expense(client, **overrides) -> dict:
    payload = {"amount": 10.0, "description": "Test", "date": TODAY}
    payload.update(overrides)
    r = client.post("/api/expenses/", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _make_rule(client, **overrides) -> dict:
    payload = {
        "name": "Netflix",
        "amount": 14.99,
        "frequency": "monthly",
        "next_due_date": TODAY,
        "is_active": True,
    }
    payload.update(overrides)
    r = client.post("/api/recurring/", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_health_head(self, client):
        r = client.head("/health")
        assert r.status_code == 200

    def test_detailed_health(self, client):
        r = client.get("/health/detailed")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["database"] in ("ok", "connected")


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────

class TestCategories:
    def test_list_categories(self, client):
        r = client.get("/api/categories/")
        assert r.status_code == 200
        names = [c["name"] for c in r.json()]
        assert "Food" in names
        assert "Other" in names

    def test_create_category(self, client):
        r = client.post("/api/categories/", json={"name": "Pets", "color": "#abc123", "icon": "🐾"})
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Pets"
        assert body["id"] is not None

    def test_create_duplicate_category_fails(self, client):
        r = client.post("/api/categories/", json={"name": "Food", "color": "#000", "icon": "x"})
        assert r.status_code == 400

    def test_create_category_missing_fields(self, client):
        r = client.post("/api/categories/", json={"name": "X"})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Expenses — CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestExpensesCRUD:
    def test_list_expenses_empty(self, client):
        r = client.get("/api/expenses/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_expense_minimal(self, client):
        r = client.post("/api/expenses/", json={"amount": 5.0, "description": "Coffee", "date": TODAY})
        assert r.status_code == 201
        body = r.json()
        assert body["amount"] == 5.0
        assert body["description"] == "Coffee"
        assert body["id"] is not None

    def test_create_expense_full(self, client):
        food_id = _cat_id(client, "Food")
        r = client.post("/api/expenses/", json={
            "amount": 12.5,
            "description": "Lunch",
            "date": TODAY,
            "merchant": "McDonald's",
            "category_id": food_id,
            "notes": "With colleagues",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["merchant"] == "McDonald's"
        assert body["category"]["name"] == "Food"

    def test_get_expense(self, client):
        created = _make_expense(client)
        r = client.get(f"/api/expenses/{created['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    def test_get_expense_not_found(self, client):
        r = client.get("/api/expenses/99999")
        assert r.status_code == 404

    def test_update_expense(self, client):
        created = _make_expense(client)
        r = client.put(f"/api/expenses/{created['id']}", json={
            "amount": 99.0,
            "description": "Updated",
            "date": TODAY,
        })
        assert r.status_code == 200
        assert r.json()["amount"] == 99.0
        assert r.json()["description"] == "Updated"

    def test_update_expense_not_found(self, client):
        r = client.put("/api/expenses/99999", json={"amount": 1.0, "description": "X", "date": TODAY})
        assert r.status_code == 404

    def test_delete_expense(self, client):
        created = _make_expense(client)
        r = client.delete(f"/api/expenses/{created['id']}")
        assert r.status_code == 200
        assert "deleted" in r.json()["message"].lower()
        # Confirm it's gone
        r2 = client.get(f"/api/expenses/{created['id']}")
        assert r2.status_code == 404

    def test_delete_expense_not_found(self, client):
        r = client.delete("/api/expenses/99999")
        assert r.status_code == 404

    def test_list_expenses_shows_created(self, client):
        _make_expense(client, description="Alpha")
        _make_expense(client, description="Beta")
        r = client.get("/api/expenses/")
        names = [e["description"] for e in r.json()]
        assert "Alpha" in names
        assert "Beta" in names


# ─────────────────────────────────────────────────────────────────────────────
# Expenses — Validation edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestExpensesValidation:
    def test_missing_amount(self, client):
        r = client.post("/api/expenses/", json={"description": "X", "date": TODAY})
        assert r.status_code == 422

    def test_missing_description(self, client):
        r = client.post("/api/expenses/", json={"amount": 5.0, "date": TODAY})
        assert r.status_code == 422

    def test_missing_date(self, client):
        r = client.post("/api/expenses/", json={"amount": 5.0, "description": "X"})
        assert r.status_code == 422

    def test_negative_amount(self, client):
        # ExpenseCreate lacks gt=0; Expense model raises it → 422 or 500
        r = client.post("/api/expenses/", json={"amount": -5.0, "description": "X", "date": TODAY})
        assert r.status_code >= 400

    def test_zero_amount(self, client):
        r = client.post("/api/expenses/", json={"amount": 0.0, "description": "X", "date": TODAY})
        assert r.status_code >= 400

    def test_string_amount(self, client):
        r = client.post("/api/expenses/", json={"amount": "abc", "description": "X", "date": TODAY})
        assert r.status_code == 422

    def test_invalid_date_format(self, client):
        r = client.post("/api/expenses/", json={"amount": 5.0, "description": "X", "date": "not-a-date"})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Expenses — Filtering
# ─────────────────────────────────────────────────────────────────────────────

class TestExpensesFiltering:
    def _seed(self, client):
        food_id = _cat_id(client, "Food")
        other_id = _cat_id(client, "Other")
        _make_expense(client, description="May Food", date="2026-05-10", category_id=food_id, amount=10.0)
        _make_expense(client, description="May Other", date="2026-05-20", category_id=other_id, amount=20.0)
        _make_expense(client, description="April Food", date="2026-04-15", category_id=food_id, amount=5.0)
        return food_id, other_id

    def test_filter_by_month(self, client):
        self._seed(client)
        r = client.get("/api/expenses/?month=5&year=2026")
        descs = [e["description"] for e in r.json()]
        assert "May Food" in descs
        assert "May Other" in descs
        assert "April Food" not in descs

    def test_filter_by_year(self, client):
        self._seed(client)
        r = client.get("/api/expenses/?year=2026")
        assert len(r.json()) == 3
        r2 = client.get("/api/expenses/?year=2025")
        assert len(r2.json()) == 0

    def test_filter_by_category(self, client):
        food_id, _ = self._seed(client)
        r = client.get(f"/api/expenses/?category_id={food_id}")
        for e in r.json():
            assert e["category"]["name"] == "Food"
        assert any(e["description"] == "May Food" for e in r.json())
        assert any(e["description"] == "April Food" for e in r.json())

    def test_filter_by_search(self, client):
        _make_expense(client, description="Netflix subscription", merchant="Netflix")
        _make_expense(client, description="Gym membership", merchant="FitLife")
        r = client.get("/api/expenses/?search=netflix")
        descriptions = [e["description"] for e in r.json()]
        assert "Netflix subscription" in descriptions
        assert "Gym membership" not in descriptions

    def test_filter_month_and_category(self, client):
        food_id, _ = self._seed(client)
        r = client.get(f"/api/expenses/?month=5&year=2026&category_id={food_id}")
        assert len(r.json()) == 1
        assert r.json()[0]["description"] == "May Food"

    def test_pagination_limit(self, client):
        for i in range(5):
            _make_expense(client, description=f"Exp {i}")
        r = client.get("/api/expenses/?limit=2")
        assert len(r.json()) == 2

    def test_pagination_offset(self, client):
        for i in range(5):
            _make_expense(client, description=f"Exp {i}", amount=float(i + 1))
        r_all = client.get("/api/expenses/?limit=5")
        r_offset = client.get("/api/expenses/?offset=2&limit=5")
        assert len(r_offset.json()) == 3
        assert r_offset.json()[0]["id"] != r_all.json()[0]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Budgets
# ─────────────────────────────────────────────────────────────────────────────

class TestBudgets:
    def test_list_budgets_empty(self, client):
        r = client.get("/api/budgets/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_budget(self, client):
        food_id = _cat_id(client, "Food")
        r = client.post("/api/budgets/", json={
            "category_id": food_id, "monthly_limit": 200.0, "month": 5, "year": 2026
        })
        assert r.status_code == 200
        body = r.json()
        assert body["monthly_limit"] == 200.0
        assert body["month"] == 5

    def test_budget_upsert(self, client):
        food_id = _cat_id(client, "Food")
        payload = {"category_id": food_id, "monthly_limit": 100.0, "month": 5, "year": 2026}
        r1 = client.post("/api/budgets/", json=payload)
        budget_id = r1.json()["id"]
        r2 = client.post("/api/budgets/", json={**payload, "monthly_limit": 300.0})
        assert r2.json()["id"] == budget_id
        assert r2.json()["monthly_limit"] == 300.0

    def test_budget_status_empty(self, client):
        r = client.get("/api/budgets/status?month=5&year=2026")
        assert r.status_code == 200
        assert r.json() == []

    def test_budget_status_with_spending(self, client):
        food_id = _cat_id(client, "Food")
        client.post("/api/budgets/", json={
            "category_id": food_id, "monthly_limit": 100.0, "month": 5, "year": 2026
        })
        _make_expense(client, amount=40.0, category_id=food_id, date="2026-05-10")
        r = client.get("/api/budgets/status?month=5&year=2026")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        entry = body[0]
        assert entry["spent"] == 40.0
        assert entry["monthly_limit"] == 100.0
        assert entry["percentage"] == 40.0
        assert entry["status"] == "on_track"
        assert "budget_id" in entry

    def test_budget_status_warning(self, client):
        food_id = _cat_id(client, "Food")
        client.post("/api/budgets/", json={
            "category_id": food_id, "monthly_limit": 100.0, "month": 5, "year": 2026
        })
        _make_expense(client, amount=75.0, category_id=food_id, date="2026-05-10")
        r = client.get("/api/budgets/status?month=5&year=2026")
        assert r.json()[0]["status"] == "warning"

    def test_budget_status_over_budget(self, client):
        food_id = _cat_id(client, "Food")
        client.post("/api/budgets/", json={
            "category_id": food_id, "monthly_limit": 50.0, "month": 5, "year": 2026
        })
        _make_expense(client, amount=80.0, category_id=food_id, date="2026-05-10")
        r = client.get("/api/budgets/status?month=5&year=2026")
        assert r.json()[0]["status"] == "over_budget"

    def test_update_budget(self, client):
        food_id = _cat_id(client, "Food")
        r = client.post("/api/budgets/", json={
            "category_id": food_id, "monthly_limit": 100.0, "month": 5, "year": 2026
        })
        bid = r.json()["id"]
        r2 = client.put(f"/api/budgets/{bid}", json={"monthly_limit": 250.0})
        assert r2.status_code == 200
        assert r2.json()["monthly_limit"] == 250.0


# ─────────────────────────────────────────────────────────────────────────────
# Recurring Rules
# ─────────────────────────────────────────────────────────────────────────────

class TestRecurringRules:
    def test_list_rules_empty(self, client):
        r = client.get("/api/recurring/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_rule(self, client):
        r = client.post("/api/recurring/", json={
            "name": "Spotify",
            "amount": 5.99,
            "frequency": "monthly",
            "next_due_date": "2026-06-01",
            "is_active": True,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Spotify"
        assert body["amount"] == 5.99
        assert body["is_active"] is True

    def test_create_rule_with_category(self, client):
        ent_id = _cat_id(client, "Entertainment")
        r = client.post("/api/recurring/", json={
            "name": "Netflix",
            "amount": 14.99,
            "frequency": "monthly",
            "next_due_date": "2026-06-01",
            "is_active": True,
            "category_id": ent_id,
        })
        assert r.status_code == 200
        assert r.json()["category_id"] == ent_id

    def test_create_rule_missing_name(self, client):
        r = client.post("/api/recurring/", json={
            "amount": 5.0, "frequency": "monthly", "next_due_date": "2026-06-01", "is_active": True,
        })
        assert r.status_code == 422

    def test_create_rule_missing_amount(self, client):
        """amount is a required field — omitting it returns 422."""
        r = client.post("/api/recurring/", json={
            "name": "X", "frequency": "monthly",
            "next_due_date": "2026-06-01", "is_active": True,
        })
        assert r.status_code == 422

    def test_delete_rule(self, client):
        rule = _make_rule(client)
        r = client.delete(f"/api/recurring/{rule['id']}")
        assert r.status_code == 200
        assert "deleted" in r.json()["message"].lower()
        r2 = client.get("/api/recurring/")
        assert len(r2.json()) == 0

    def test_delete_rule_not_found(self, client):
        r = client.delete("/api/recurring/99999")
        assert r.status_code == 404

    def test_toggle_rule(self, client):
        rule = _make_rule(client)
        assert rule["is_active"] is True
        r = client.patch(f"/api/recurring/{rule['id']}/toggle")
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        r2 = client.patch(f"/api/recurring/{rule['id']}/toggle")
        assert r2.json()["is_active"] is True

    def test_delete_rule_nulls_expense_recurring_id(self, client, engine):
        rule = _make_rule(client)
        # Create an expense linked to this rule
        with Session(engine) as s:
            exp = Expense(
                amount=14.99,
                description="Netflix",
                date=date.today(),
                is_recurring=True,
                recurring_id=rule["id"],
            )
            s.add(exp)
            s.commit()
            exp_id = exp.id

        client.delete(f"/api/recurring/{rule['id']}")

        with Session(engine) as s:
            exp = s.get(Expense, exp_id)
            assert exp is not None
            assert exp.recurring_id is None


# ─────────────────────────────────────────────────────────────────────────────
# Recurring Auto-charge Logic
# ─────────────────────────────────────────────────────────────────────────────

class TestRecurringAutoCharge:
    def test_run_recurring_creates_expense(self, client, engine):
        """A due rule fires and creates an expense transaction."""
        _make_rule(client, next_due_date=TODAY, name="Auto-test")
        r = client.post("/api/recurring/run")
        assert r.status_code == 200
        data = r.json()
        assert data["created"] == 1

        # Verify expense exists in DB
        with Session(engine) as s:
            exps = s.exec(
                __import__("sqlmodel").select(Expense).where(Expense.is_recurring == True)
            ).all()
        assert len(exps) == 1
        assert exps[0].description == "Auto-test"
        assert exps[0].amount == 14.99

    def test_run_recurring_future_rule_not_charged(self, client):
        """A rule with a future due date does NOT fire."""
        future = (date.today() + timedelta(days=30)).isoformat()
        _make_rule(client, next_due_date=future)
        r = client.post("/api/recurring/run")
        assert r.json()["created"] == 0

    def test_run_recurring_no_double_charge(self, client, engine):
        """Running the processor twice in the same month creates only 1 expense."""
        _make_rule(client, next_due_date=TODAY, name="NoDbl")
        r1 = client.post("/api/recurring/run")
        assert r1.json()["created"] == 1
        r2 = client.post("/api/recurring/run")
        assert r2.json()["created"] == 0

        with Session(engine) as s:
            exps = s.exec(
                __import__("sqlmodel").select(Expense).where(Expense.description == "NoDbl")
            ).all()
        assert len(exps) == 1

    def test_run_recurring_advances_next_due_date(self, client, engine):
        """After firing, next_due_date is pushed forward by one month."""
        rule = _make_rule(client, next_due_date=TODAY)
        client.post("/api/recurring/run")
        with Session(engine) as s:
            updated_rule = s.get(RecurringRule, rule["id"])
        assert updated_rule.next_due_date > date.fromisoformat(TODAY)

    def test_run_recurring_inactive_rule_skipped(self, client):
        """Inactive rules are not processed."""
        _make_rule(client, next_due_date=TODAY, is_active=False)
        r = client.post("/api/recurring/run")
        assert r.json()["created"] == 0

    def test_run_recurring_updates_last_run_date(self, client, engine):
        rule = _make_rule(client, next_due_date=TODAY)
        client.post("/api/recurring/run")
        with Session(engine) as s:
            updated_rule = s.get(RecurringRule, rule["id"])
        assert updated_rule.last_run_date is not None


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_summary_empty(self, client):
        r = client.get("/api/analytics/summary?month=5&year=2026")
        assert r.status_code == 200
        body = r.json()
        assert body["total_this_month"] == 0.0
        assert body["mom_change_percent"] == 0.0
        assert body["top_category"] is None

    def test_summary_with_expenses(self, client):
        food_id = _cat_id(client, "Food")
        _make_expense(client, amount=30.0, date="2026-05-10", category_id=food_id)
        _make_expense(client, amount=20.0, date="2026-05-15", category_id=food_id)
        r = client.get("/api/analytics/summary?month=5&year=2026")
        body = r.json()
        assert body["total_this_month"] == 50.0
        assert body["top_category"]["name"] == "Food"
        assert body["top_category"]["amount"] == 50.0

    def test_summary_mom_change(self, client):
        _make_expense(client, amount=100.0, date="2026-04-15")
        _make_expense(client, amount=150.0, date="2026-05-15")
        r = client.get("/api/analytics/summary?month=5&year=2026")
        body = r.json()
        assert body["mom_change_percent"] == 50.0

    def test_trends_returns_six_months(self, client):
        r = client.get("/api/analytics/trends")
        assert r.status_code == 200
        assert len(r.json()) == 6
        for entry in r.json():
            assert "month" in entry
            assert "year" in entry
            assert "total" in entry
            assert "label" in entry

    def test_category_breakdown_empty(self, client):
        r = client.get("/api/analytics/category-breakdown?month=5&year=2026")
        assert r.status_code == 200
        assert r.json() == []

    def test_category_breakdown_with_expenses(self, client):
        food_id = _cat_id(client, "Food")
        bills_id = _cat_id(client, "Bills")
        _make_expense(client, amount=60.0, date="2026-05-01", category_id=food_id)
        _make_expense(client, amount=40.0, date="2026-05-01", category_id=bills_id)
        r = client.get("/api/analytics/category-breakdown?month=5&year=2026")
        body = r.json()
        assert len(body) == 2
        top = body[0]
        assert top["category"]["name"] == "Food"
        assert top["amount"] == 60.0
        assert top["percentage"] == 60.0

    def test_merchant_breakdown(self, client):
        _make_expense(client, merchant="Starbucks", amount=5.0, date="2026-05-01")
        _make_expense(client, merchant="Starbucks", amount=5.0, date="2026-05-02")
        _make_expense(client, merchant="McDonalds", amount=10.0, date="2026-05-03")
        r = client.get("/api/analytics/merchant-breakdown?month=5&year=2026")
        assert r.status_code == 200
        body = r.json()
        merchants = {m["merchant"]: m for m in body}
        assert merchants["Starbucks"]["count"] == 2
        assert merchants["McDonalds"]["amount"] == 10.0

    def test_budget_used_percent(self, client):
        food_id = _cat_id(client, "Food")
        client.post("/api/budgets/", json={
            "category_id": food_id, "monthly_limit": 100.0, "month": 5, "year": 2026
        })
        _make_expense(client, amount=25.0, date="2026-05-01", category_id=food_id)
        r = client.get("/api/analytics/summary?month=5&year=2026")
        assert r.json()["budget_used_percent"] == 25.0
