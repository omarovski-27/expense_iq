"""Tests for Web Push subscriptions, delivery, and the daily recurring run.

Delivery goes through the real pywebpush encryption and VAPID signing with
freshly generated keys; only the outbound HTTP call is faked.
"""
import base64
import os
from datetime import date, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlmodel import Session, select

from gen_vapid_keys import generate
from models import Expense, PushSubscription, RecurringRule
from tests.conftest import TODAY

KEY = "test-ingest-key"
HEADERS = {"X-API-Key": KEY}
FROZEN_TODAY = date.fromisoformat(TODAY)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _browser_keys() -> dict:
    """Keys shaped like a real PushSubscription.toJSON() from a browser."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return {"p256dh": _b64url(pub), "auth": _b64url(os.urandom(16))}


class _FakeResponse:
    def __init__(self, status):
        self.status_code = status
        self.text = ""
        self.reason = "Gone" if status == 410 else "Created"
        self.headers = {}


@pytest.fixture()
def push_calls(monkeypatch):
    """Capture outbound push requests; endpoints containing 'gone' answer 410."""
    import pywebpush

    calls = []

    def fake_post(url, data=None, headers=None, timeout=None, **_):
        calls.append({"url": url, "headers": headers, "data": data})
        return _FakeResponse(410 if "gone" in url else 201)

    monkeypatch.setattr(pywebpush.requests, "post", fake_post)
    return calls


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    pub, priv = generate()
    monkeypatch.setenv("INGEST_API_KEY", KEY)
    monkeypatch.setenv("VAPID_PUBLIC_KEY", pub)
    monkeypatch.setenv("VAPID_PRIVATE_KEY", priv)
    import services.recurring_service as rs
    monkeypatch.setattr(rs, "_today_jordan", lambda: FROZEN_TODAY)


def _subscribe(client, endpoint="https://push.example/abc"):
    return client.post(
        "/api/notify/subscribe",
        json={"endpoint": endpoint, "keys": _browser_keys()},
        headers=HEADERS,
    )


def _subs(engine):
    with Session(engine) as s:
        return s.exec(select(PushSubscription)).all()


class TestSubscriptions:
    def test_public_key_is_open(self, client):
        r = client.get("/api/notify/vapid-public-key")
        assert r.status_code == 200
        assert r.json()["key"] == os.environ["VAPID_PUBLIC_KEY"]

    def test_public_key_503_when_unconfigured(self, client, monkeypatch):
        monkeypatch.delenv("VAPID_PUBLIC_KEY")
        assert client.get("/api/notify/vapid-public-key").status_code == 503

    def test_subscribe_requires_key(self, client, engine):
        r = client.post(
            "/api/notify/subscribe",
            json={"endpoint": "https://push.example/x", "keys": _browser_keys()},
        )
        assert r.status_code == 401
        assert _subs(engine) == []

    def test_subscribe_is_idempotent_per_endpoint(self, client, engine):
        assert _subscribe(client).status_code == 200
        assert _subscribe(client).status_code == 200
        assert len(_subs(engine)) == 1

    def test_rejects_non_https_endpoint(self, client):
        assert _subscribe(client, "http://push.example/x").status_code == 422

    def test_unsubscribe(self, client, engine):
        _subscribe(client)
        r = client.post(
            "/api/notify/unsubscribe", json={"endpoint": "https://push.example/abc"}, headers=HEADERS
        )
        assert r.status_code == 200
        assert _subs(engine) == []


class TestDelivery:
    def test_test_push_is_encrypted_and_signed(self, client, push_calls):
        _subscribe(client)
        r = client.post("/api/notify/test", headers=HEADERS)
        assert r.json() == {"ok": True, "sent": 1}
        [call] = push_calls
        assert call["url"] == "https://push.example/abc"
        assert call["headers"]["content-encoding"] == "aes128gcm"
        assert call["headers"]["Authorization"].startswith("vapid t=")
        assert b"Notifications are working" not in call["data"]  # payload is encrypted

    def test_gone_subscription_is_removed(self, client, engine, push_calls):
        _subscribe(client, "https://push.example/live")
        _subscribe(client, "https://push.example/gone")
        r = client.post("/api/notify/test", headers=HEADERS)
        assert r.json()["sent"] == 1
        assert [s.endpoint for s in _subs(engine)] == ["https://push.example/live"]

    def test_unconfigured_push_is_a_noop(self, client, monkeypatch, push_calls):
        _subscribe(client)
        monkeypatch.delenv("VAPID_PRIVATE_KEY")
        assert client.post("/api/notify/test", headers=HEADERS).status_code == 503
        assert push_calls == []


class TestRunDaily:
    def test_requires_key(self, client):
        assert client.post("/api/notify/run-daily").status_code == 401

    def test_charges_due_rule_and_pushes(self, client, engine, push_calls):
        _subscribe(client)
        with Session(engine) as s:
            s.add(RecurringRule(
                name="Netflix", amount=7.0, category_id=1,
                frequency="monthly", next_due_date=FROZEN_TODAY,
            ))
            s.commit()

        r = client.post("/api/notify/run-daily", headers=HEADERS)
        body = r.json()
        assert body["charged"] == [{"name": "Netflix", "amount": 7.0}]
        assert body["sent"] == 1
        assert len(push_calls) == 1

        # Running again the same day charges nothing more.
        again = client.post("/api/notify/run-daily", headers=HEADERS).json()
        assert again["charged"] == []
        with Session(engine) as s:
            assert len(s.exec(select(Expense)).all()) == 1

    def test_nothing_due(self, client, engine, push_calls):
        with Session(engine) as s:
            s.add(RecurringRule(
                name="Gym", amount=30.0, category_id=1,
                frequency="monthly", next_due_date=FROZEN_TODAY + timedelta(days=3),
            ))
            s.commit()
        body = client.post("/api/notify/run-daily", headers=HEADERS).json()
        assert body == {"ok": True, "charged": [], "sent": 0}
        assert push_calls == []
