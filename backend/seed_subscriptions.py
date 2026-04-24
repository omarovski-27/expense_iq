"""
seed_subscriptions.py
Run from the backend directory to seed recurring subscription rules.
Usage: python seed_subscriptions.py
"""

import sys
import os
from datetime import date

# Ensure backend directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

from database import engine
from models import RecurringRule, Category
from sqlmodel import Session, select

SUBSCRIPTIONS = [
    {"name": "iCloud Storage",         "amount": 7.10,  "category": "Bills",         "next_due_date": date(2026, 5, 16)},
    {"name": "Gym Monthly Fee",         "amount": 50.00, "category": "Health",        "next_due_date": date(2026, 5, 26)},
    {"name": "Spotify Premium",         "amount": 1.80,  "category": "Entertainment", "next_due_date": date(2026, 4, 27)},
    {"name": "Careem Subscription",     "amount": 3.00,  "category": "Transport",     "next_due_date": date(2026, 5,  5)},
    {"name": "Songsterr",               "amount": 3.00,  "category": "Entertainment", "next_due_date": date(2026, 5, 21)},
    {"name": "Whoop Membership",        "amount": 14.17, "category": "Health",        "next_due_date": date(2026, 5, 24)},
    {"name": "Claude AI",               "amount": 14.70, "category": "Bills",         "next_due_date": date(2026, 5, 18)},
    {"name": "GYM Rizeup",              "amount": 60.00, "category": "Health",        "next_due_date": date(2026, 5, 29)},
    {"name": "YouTube Premium",         "amount": 11.50, "category": "Entertainment", "next_due_date": date(2026, 5,  3)},
    {"name": "VSC Copilot + GitHub",    "amount": 7.30,  "category": "Education",     "next_due_date": date(2026, 5, 16)},
    {"name": "Shaving Supplies",        "amount": 30.00, "category": "Personal",      "next_due_date": date(2026, 5,  1)},
    {"name": "Gas",                     "amount": 40.00, "category": "Transport",     "next_due_date": date(2026, 5,  1)},
]

def main():
    added = 0
    skipped = 0

    with Session(engine) as session:
        # Build a case-insensitive category name → id map
        categories = session.exec(select(Category)).all()
        cat_map = {c.name.lower(): c.id for c in categories}

        # Fallback to "Other" category id
        other_id = cat_map.get("other")

        # Fetch existing rule names to detect duplicates
        existing_names = {
            r.name.lower()
            for r in session.exec(select(RecurringRule)).all()
        }

        for sub in SUBSCRIPTIONS:
            if sub["name"].lower() in existing_names:
                print(f"  [skip]  {sub['name']} — already exists")
                skipped += 1
                continue

            category_id = cat_map.get(sub["category"].lower(), other_id)
            if category_id is None:
                print(f"  [warn]  No category found for '{sub['category']}' and no 'Other' category exists — skipping {sub['name']}")
                skipped += 1
                continue

            rule = RecurringRule(
                name=sub["name"],
                amount=sub["amount"],
                category_id=category_id,
                frequency="monthly",
                next_due_date=sub["next_due_date"],
                is_active=True,
            )
            session.add(rule)
            existing_names.add(sub["name"].lower())  # prevent in-batch duplicates
            print(f"  [add]   {sub['name']}  ${sub['amount']:.2f}/mo  → next due {sub['next_due_date']}")
            added += 1

        session.commit()

    print(f"\nDone. Added {added} recurring rules, skipped {skipped} duplicates.")


if __name__ == "__main__":
    main()
