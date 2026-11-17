"""Tests for POST /api/ingest (Shortcut / quick-add capture)."""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from models import Expense
from tests.conftest import TODAY

FROZEN_TODAY = date.fromisoformat(TODAY)
KEY = "test-ingest-key"
HEADERS = {"X-API-Key": KEY}


@pytest.fixture(autouse=True)
def _env_and_today(monkeypatch):
    monkeypatch.setenv("INGEST_API_KEY", KEY)
    import routers.ingest as ingest_module
    monkeypatch.setattr(ingest_module, "today_jordan", lambda: FROZEN_TODAY)


def _post(client, text, headers=HEADERS, **extra):
    return client.post("/api/ingest", json={"text": text, **extra}, headers=headers)


def _expenses(engine):
    with Session(engine) as s:
        return s.exec(select(Expense).order_by(Expense.id)).all()


class TestAuth:
    def test_missing_key_401(self, client):
        assert _post(client, "coffee 2.5", headers={}).status_code == 401

    def test_wrong_key_401(self, client):
        assert _post(client, "coffee 2.5", headers={"X-API-Key": "nope"}).status_code == 401

    def test_bearer_header_accepted(self, client):
        r = _post(client, "coffee 2.5", headers={"Authorization": f"Bearer {KEY}"})
        assert r.status_code == 200

    def test_unconfigured_refuses(self, client, monkeypatch):
        monkeypatch.delenv("INGEST_API_KEY")
        assert _post(client, "coffee 2.5").status_code == 503

    def test_rejected_request_writes_nothing(self, client, engine):
        _post(client, "coffee 2.5", headers={"X-API-Key": "nope"})
        assert _expenses(engine) == []


class TestCapture:
    def test_logs_expense_same_as_telegram_parser(self, client, engine):
        r = _post(client, "shawarma 3.5 food")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["message"] == "Added shawarma: 3.50 JD (Food). Today: 3.50 JD"
        assert body["expense"]["category"]["name"] == "Food"
        [e] = _expenses(engine)
        assert (e.amount, e.merchant, e.date) == (3.5, "shawarma", FROZEN_TODAY)

    def test_message_includes_running_day_total(self, client):
        _post(client, "coffee 2.5 food")
        r = _post(client, "taxi 4 transport")
        assert r.json()["message"].endswith("Today: 6.50 JD")

    def test_unparseable_text_422_with_message(self, client, engine):
        r = _post(client, "no amount here")
        assert r.status_code == 422
        assert r.json() == {"ok": False, "message": "Couldn't read that. Try: coffee 2.5 food"}
        assert _expenses(engine) == []

    def test_empty_text_rejected(self, client):
        assert _post(client, "").status_code == 422

    def test_yesterday_word_in_text(self, client, engine):
        r = _post(client, "coffee 2.5 yesterday")
        assert r.status_code == 200
        [e] = _expenses(engine)
        assert e.date == FROZEN_TODAY - timedelta(days=1)
        assert e.merchant == "coffee"  # the date word is not part of the merchant
        assert "May 15" in r.json()["message"]

    @pytest.mark.parametrize("raw", ["2026-05-10", "10/05/2026"])
    def test_explicit_date_formats(self, client, engine, raw):
        assert _post(client, "coffee 2.5", date=raw).status_code == 200
        assert _expenses(engine)[0].date == date(2026, 5, 10)

    def test_bad_date_422(self, client, engine):
        assert _post(client, "coffee 2.5", date="someday").status_code == 422
        assert _expenses(engine) == []

    def test_future_date_rejected(self, client, engine):
        assert _post(client, "coffee 2.5", date="2026-05-17").status_code == 422
        assert _expenses(engine) == []


class TestUndo:
    def test_undo_removes_last_ingested(self, client, engine):
        _post(client, "coffee 2.5")
        _post(client, "taxi 4")
        r = _post(client, "undo")
        assert r.json() == {"ok": True, "message": "Removed taxi (4.00 JD)."}
        assert [e.merchant for e in _expenses(engine)] == ["coffee"]

    def test_undo_ignores_expenses_added_elsewhere(self, client, engine):
        client.post("/api/expenses/", json={
            "amount": 9, "description": "rent", "date": TODAY, "category_id": 1,
        })
        r = _post(client, "undo")
        assert r.status_code == 404
        assert len(_expenses(engine)) == 1

    def test_undo_refuses_old_entries(self, client, engine):
        _post(client, "coffee 2.5")
        with Session(engine) as s:
            e = s.exec(select(Expense)).one()
            e.created_at = datetime.now(timezone.utc) - timedelta(minutes=20)
            s.add(e)
            s.commit()
        assert _post(client, "undo").status_code == 409
        assert len(_expenses(engine)) == 1
