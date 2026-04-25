from datetime import date
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models import AIInsight, AIInsightRead
from services.ai_service import (
    chat_with_finances,
    detect_spikes,
    generate_monthly_insights,
)

router = APIRouter(prefix="/insights", tags=["insights"])


# ─────────────────────────────────────────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────────────────────────────────────────

class GenerateBody(BaseModel):
    month: int
    year: int


class ChatBody(BaseModel):
    question: str


# ─────────────────────────────────────────────────────────────────────────────
# GET /insights
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[AIInsightRead])
def list_insights(
    month: Optional[int] = None,
    year: Optional[int] = None,
    insight_type: Optional[str] = None,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    query = (
        select(AIInsight)
        .where(AIInsight.is_dismissed == False)  # noqa: E712
        .order_by(AIInsight.created_at.desc())
        .limit(limit)
    )
    if month is not None:
        query = query.where(AIInsight.month == month)
    if year is not None:
        query = query.where(AIInsight.year == year)
    if insight_type is not None:
        query = query.where(AIInsight.type == insight_type)
    return session.exec(query).all()


# ─────────────────────────────────────────────────────────────────────────────
# POST /insights/generate
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=list[AIInsightRead])
async def generate_insights(body: GenerateBody, session: Session = Depends(get_session)):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="AI service not configured")
    insights = await generate_monthly_insights(body.month, body.year, session)
    return insights


# ─────────────────────────────────────────────────────────────────────────────
# POST /insights/chat
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(body: ChatBody, session: Session = Depends(get_session)):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="AI service not configured")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if len(body.question) > 1000:
        raise HTTPException(status_code=400, detail="Question is too long (max 1000 characters)")
    response = await chat_with_finances(body.question, session)
    return {"response": response}


# ─────────────────────────────────────────────────────────────────────────────
# GET /insights/spikes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/spikes")
def get_spikes(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    today = date.today()
    m = month if month is not None else today.month
    y = year if year is not None else today.year
    return detect_spikes(m, y, session)


# ─────────────────────────────────────────────────────────────────────────────
# GET /insights/monthly-report
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/monthly-report")
async def monthly_report(
    month: Optional[int] = None,
    year: Optional[int] = None,
    session: Session = Depends(get_session),
):
    today = date.today()
    m = month if month is not None else today.month
    y = year if year is not None else today.year

    # Return most recent non-dismissed summary for this month/year
    existing = session.exec(
        select(AIInsight)
        .where(AIInsight.type == "summary")
        .where(AIInsight.month == m)
        .where(AIInsight.year == y)
        .where(AIInsight.is_dismissed == False)  # noqa: E712
        .order_by(AIInsight.created_at.desc())
        .limit(1)
    ).first()

    if existing:
        return {"id": existing.id, "content": existing.content, "created_at": existing.created_at}

    # None found — generate fresh insights and return the summary
    insights = await generate_monthly_insights(m, y, session)
    summary = next((i for i in insights if i.type == "summary"), None)
    if summary:
        return {"id": summary.id, "content": summary.content, "created_at": summary.created_at}

    return {"id": None, "content": "No report available for this period.", "created_at": None}


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /insights/{id}/dismiss
# ─────────────────────────────────────────────────────────────────────────────

@router.delete("/{insight_id}/dismiss")
def dismiss_insight(insight_id: int, session: Session = Depends(get_session)):
    insight = session.get(AIInsight, insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insight.is_dismissed = True
    session.add(insight)
    session.commit()
    return {"message": "Insight dismissed"}

