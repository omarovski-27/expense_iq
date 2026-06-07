"""
AI insights service tests.

These do NOT hit the Anthropic API — the client is patched. They verify that
generate_monthly_insights sends a *grounded* payload (real uncategorized total,
a real prior-month baseline, and the actual subscriptions) so the model can't
invent figures like a fake "$25 average" or a non-existent "$150 gym".
"""
import asyncio
import json
from datetime import date
from unittest.mock import MagicMock, patch

from sqlmodel import Session, select

import services.ai_service as ai_service
from models import Category, Expense, RecurringRule


def _fake_claude_response():
    resp = MagicMock()
    resp.content = [
        MagicMock(text=json.dumps({"summary": "test", "spikes": [], "recommendations": [], "insights": []}))
    ]
    return resp


def test_generate_monthly_insights_sends_grounded_payload(engine):
    with Session(engine) as s:
        food_id = next(c.id for c in s.exec(select(Category)).all() if c.name == "Food")
        # Current month (May 2026): one categorized + one uncategorized expense
        s.add(Expense(amount=100.0, description="Groceries", date=date(2026, 5, 10), category_id=food_id))
        s.add(Expense(amount=60.0, description="Mystery charge", date=date(2026, 5, 11)))
        # Prior month (April 2026): establishes the baseline
        s.add(Expense(amount=40.0, description="April thing", date=date(2026, 4, 5), category_id=food_id))
        # An active subscription
        s.add(RecurringRule(name="Gym", amount=150.0, frequency="monthly",
                            next_due_date=date(2026, 5, 1), is_active=True))
        s.commit()

    with patch.object(ai_service, "_client") as mock_client:
        mock_client.messages.create.return_value = _fake_claude_response()
        with Session(engine) as s:
            asyncio.run(ai_service.generate_monthly_insights(5, 2026, s))
        call_kwargs = mock_client.messages.create.call_args.kwargs

    sent = json.loads(call_kwargs["messages"][0]["content"])

    # total includes uncategorized; uncategorized is reported separately
    assert sent["total_spend"] == 160.0
    assert sent["uncategorized_total"] == 60.0
    # real prior-month baseline (April = 40), not an invented number
    assert {"month": 4, "year": 2026, "total": 40.0} in sent["prior_3_month_totals"]
    assert sent["avg_monthly_spend_prior_3mo"] == 40.0
    # the only subscription the model is allowed to reference
    assert sent["active_subscriptions"] == [
        {"name": "Gym", "amount": 150.0, "frequency": "monthly"}
    ]
