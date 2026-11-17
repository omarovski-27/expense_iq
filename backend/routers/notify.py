"""Web Push subscription management and the daily recurring-charge run.

Everything except the public VAPID key requires the same INGEST_API_KEY as
/api/ingest, so a stranger can't subscribe their own browser to your alerts or
trigger charges.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from database import get_session
from models import PushSubscription
from routers.ingest import require_ingest_key
from services.push_service import notify_charged, push_configured, send_push, vapid_public_key
from services.recurring_service import process_recurring_expenses

router = APIRouter(prefix="/notify", tags=["notify"])


class SubscriptionKeys(BaseModel):
    p256dh: str = Field(..., min_length=1, max_length=255)
    auth: str = Field(..., min_length=1, max_length=255)


class SubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=1000)
    keys: SubscriptionKeys


class UnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=1000)


@router.get("/vapid-public-key")
def get_vapid_public_key():
    key = vapid_public_key()
    if not key:
        raise HTTPException(status_code=503, detail="Push notifications are not configured")
    return {"key": key}


@router.post("/subscribe", dependencies=[Depends(require_ingest_key)])
def subscribe(body: SubscribeRequest, session: Session = Depends(get_session)):
    if not body.endpoint.startswith("https://"):
        raise HTTPException(status_code=422, detail="Push endpoint must be https")
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing:
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
        session.add(existing)
    else:
        session.add(
            PushSubscription(endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth)
        )
    session.commit()
    return {"ok": True}


@router.post("/unsubscribe", dependencies=[Depends(require_ingest_key)])
def unsubscribe(body: UnsubscribeRequest, session: Session = Depends(get_session)):
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing:
        session.delete(existing)
        session.commit()
    return {"ok": True}


@router.post("/test", dependencies=[Depends(require_ingest_key)])
def test_push(session: Session = Depends(get_session)):
    if not push_configured():
        raise HTTPException(status_code=503, detail="Push notifications are not configured")
    sent = send_push(session, "ExpenseIQ", "Notifications are working.", url="/quick")
    return {"ok": True, "sent": sent}


@router.post("/run-daily", dependencies=[Depends(require_ingest_key)])
def run_daily(session: Session = Depends(get_session)):
    """Charge due subscriptions and push a notice for each.

    Called once a day by the GitHub Actions workflow. Before this existed, charges
    only ran on a cold start or the Telegram /subs command, and the keep-warm
    pings mean cold starts are rare, so subscriptions could silently stop being
    logged. Safe to call repeatedly: each rule's next_due_date advances once
    it has been charged.
    """
    charged = process_recurring_expenses(session)
    sent = notify_charged(session, charged)
    return {"ok": True, "charged": charged, "sent": sent}
