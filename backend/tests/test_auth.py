"""Every /api route needs the device key, except a short public allowlist.

This walks the app's real route table, so a new /api route added later
without the key makes this test fail.
"""
import pytest
from fastapi.routing import APIRoute

from main import app

# (method, path) pairs under /api that are deliberately public.
PUBLIC_API = {("GET", "/api/notify/vapid-public-key")}


def _api_routes():
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield method, route.path


def _fill(path: str) -> str:
    # Any value works for path params: the key check runs before the handler.
    return path.replace("{", "").replace("}", "").replace("_id", "1").replace("id", "1")


PROTECTED = [r for r in _api_routes() if r not in PUBLIC_API]


def test_route_table_is_not_empty():
    # Guards against the walk silently finding nothing.
    assert len(PROTECTED) > 20


@pytest.mark.parametrize("method,path", PROTECTED)
def test_protected_route_needs_key(anon_client, method, path):
    r = anon_client.request(method, _fill(path))
    assert r.status_code == 401, f"{method} {path} answered {r.status_code} without a key"


@pytest.mark.parametrize("method,path", PROTECTED)
def test_protected_route_rejects_wrong_key(anon_client, method, path):
    r = anon_client.request(method, _fill(path), headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_expenses_list_works_with_key(client):
    assert client.get("/api/expenses/").status_code == 200


def test_bearer_key_accepted(anon_client):
    from tests.conftest import TEST_API_KEY
    r = anon_client.get("/api/expenses/", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert r.status_code == 200


def test_unset_key_refuses_everything(anon_client, monkeypatch):
    monkeypatch.delenv("INGEST_API_KEY")
    assert anon_client.get("/api/expenses/").status_code == 503


def test_vapid_public_key_stays_public(anon_client, monkeypatch):
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "pub")
    r = anon_client.get("/api/notify/vapid-public-key")
    assert r.status_code == 200


def test_health_stays_open(anon_client):
    assert anon_client.get("/health").status_code == 200


def test_telegram_webhook_stays_open(telegram_client):
    # No key header: the webhook must still answer (it filters by Telegram user id).
    r = telegram_client.post("/webhook/telegram", json={"update_id": 1})
    assert r.status_code == 200
