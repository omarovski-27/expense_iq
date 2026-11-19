"""Web Push delivery to every subscribed device (installed web app / browser).

Configured by VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY (generate with
gen_vapid_keys.py) and optional VAPID_SUBJECT (defaults to a mailto: URI the
push services accept). With no keys set, sending is a silent no-op so the rest
of the app keeps working.
"""
import json
import logging
import os

from pywebpush import WebPushException, webpush
from sqlmodel import Session, select

from models import PushSubscription

logger = logging.getLogger(__name__)

# Push services return these when a subscription is permanently gone
# (app uninstalled, permission revoked); the row should be dropped.
_GONE_STATUSES = {404, 410}


def vapid_public_key() -> str | None:
    return os.getenv("VAPID_PUBLIC_KEY") or None


def push_configured() -> bool:
    return bool(os.getenv("VAPID_PUBLIC_KEY") and os.getenv("VAPID_PRIVATE_KEY"))


def send_push(session: Session, title: str, body: str, url: str = "/") -> int:
    """Send one notification to every subscription. Returns how many succeeded.

    Never raises: a notification failure must not undo or 500 the action that
    triggered it (an expense or charge has already been committed by then).
    """
    if not push_configured():
        return 0

    private_key = os.environ["VAPID_PRIVATE_KEY"]
    claims = {"sub": os.getenv("VAPID_SUBJECT", "mailto:expenseiq@example.com")}
    payload = json.dumps({"title": title, "body": body, "url": url})

    sent = 0
    for sub in session.exec(select(PushSubscription)).all():
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(claims),  # webpush mutates claims (adds aud/exp)
                timeout=10,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in _GONE_STATUSES:
                session.delete(sub)
                session.commit()
                logger.info("Removed expired push subscription %s", sub.id)
            else:
                logger.warning("Push to subscription %s failed: %s", sub.id, exc)
        except Exception:
            logger.exception("Push to subscription %s failed", sub.id)
    return sent


def notify_charged(session: Session, charged: list[dict]) -> int:
    """Push one notification per auto-charged subscription."""
    sent = 0
    for item in charged:
        sent += send_push(
            session,
            "Subscription charged",
            f"{item['name']}: {item['amount']:.2f} JOD added to today's expenses.",
            url="/transactions",
        )
    return sent
