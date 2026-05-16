"""
Shared fixtures for all backend tests.

The strategy:
- Each test gets a fresh in-memory SQLite database via StaticPool.
- The FastAPI get_session dependency is overridden to use that database.
- Default categories are seeded so endpoints that look up categories work.
- TELEGRAM_BOT_TOKEN / TELEGRAM_ALLOWED_USER_ID are set *before* main is
  imported so the webhook handler reads the correct allowed user ID.
"""
import os

# ── Must be set before importing main so env vars are read at import time ──
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token_abc123")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_ID", "12345")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models import Category

# ── Constants used across test files ──────────────────────────────────────────
ALLOWED_USER_ID = 12345
TEST_CHAT_ID = 99999
TODAY = "2026-05-16"   # fixed date for predictable assertions

DEFAULT_CATEGORIES = [
    ("Bills", "#DDA0DD", "📋"),
    ("Entertainment", "#96CEB4", "🎬"),
    ("Food", "#FF6B35", "🍔"),
    ("Health", "#FFEAA7", "💊"),
    ("Other", "#AED6F1", "📦"),
    ("Transport", "#4ECDC4", "🚗"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_tg_payload(text: str, user_id: int = ALLOWED_USER_ID, chat_id: int = TEST_CHAT_ID) -> dict:
    return {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": text,
        }
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def engine():
    """Fresh in-memory SQLite with categories seeded, discarded after each test."""
    e = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(e)
    with Session(e) as session:
        for name, color, icon in DEFAULT_CATEGORIES:
            session.add(Category(name=name, color=color, icon=icon))
        session.commit()
    yield e
    SQLModel.metadata.drop_all(e)
    e.dispose()


@pytest.fixture()
def client(engine):
    """TestClient with get_session overridden to use the test engine."""
    def _override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override
    # raise_server_exceptions=False lets FastAPI's own exception handler
    # return 500 for unhandled errors rather than re-raising in the test.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def telegram_client(engine):
    """TestClient with both get_session AND main.engine patched to the test DB.

    The Telegram webhook uses Session(engine) directly (not the get_session
    dependency), so we patch main.engine as well.
    """
    import main as main_module

    original_engine = main_module.engine
    main_module.engine = engine
    main_module.conversation_state.clear()

    def _override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    main_module.engine = original_engine
    main_module.conversation_state.clear()
    app.dependency_overrides.clear()
