from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database import get_session
from models import Category, CategoryCreate, CategoryRead, Expense

router = APIRouter(prefix="/categories", tags=["categories"])


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[CategoryRead])
def list_categories(session: Session = Depends(get_session)):
    categories = session.exec(select(Category).order_by(Category.name)).all()
    return categories


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------

@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(
    body: CategoryCreate,
    session: Session = Depends(get_session),
):
    # Check for duplicate name before attempting insert
    existing = session.exec(
        select(Category).where(Category.name == body.name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{body.name}' already exists.")

    category = Category.model_validate(body)
    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Category '{body.name}' already exists.")
    session.refresh(category)
    return category


# ---------------------------------------------------------------------------
# PUT /{id}
# ---------------------------------------------------------------------------

@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    body: CategoryCreate,
    session: Session = Depends(get_session),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Category name '{body.name}' already exists.")
    session.refresh(category)
    return category


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    reassign_to_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Prevent deleting the last category
    total_categories = session.exec(select(Category)).all()
    if len(total_categories) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last category.")

    # Check if any expenses use this category
    linked_expenses = session.exec(
        select(Expense).where(Expense.category_id == category_id)
    ).all()

    if linked_expenses:
        if reassign_to_id is None:
            raise HTTPException(
                status_code=400,
                detail="Category has expenses. Provide reassign_to_id to reassign them.",
            )
        # Validate the target category exists
        target = session.get(Category, reassign_to_id)
        if not target:
            raise HTTPException(status_code=404, detail="Reassignment target category not found.")

        for expense in linked_expenses:
            expense.category_id = reassign_to_id
        session.flush()

    session.delete(category)
    session.commit()
    return {"message": "Category deleted"}

