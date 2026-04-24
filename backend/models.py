from datetime import date, datetime
from typing import List, Literal, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


# ---------------------------------------------------------------------------
# Table models
# ---------------------------------------------------------------------------

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str  # e.g. "#FF6B35"
    icon: str   # emoji
    created_at: datetime = Field(default_factory=datetime.utcnow)

    expenses: List["Expense"] = Relationship(back_populates="category")


class RecurringRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    amount: float = Field(gt=0)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    frequency: str  # Literal["daily", "weekly", "monthly", "yearly"]
    next_due_date: date
    last_run_date: Optional[date] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Expense(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float = Field(gt=0)
    description: str
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    merchant: Optional[str] = None
    date: date
    is_recurring: bool = False
    recurring_id: Optional[int] = Field(default=None, foreign_key="recurringrule.id")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    category: Optional[Category] = Relationship(back_populates="expenses")


class Budget(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("category_id", "month", "year"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id")
    monthly_limit: float = Field(gt=0)
    month: int = Field(ge=1, le=12)
    year: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AIInsight(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str  # Literal["outlier", "spike", "summary", "recommendation"]
    title: str
    content: str
    severity: Optional[str] = "info"  # Literal["info", "warning", "critical"]
    month: Optional[int] = None
    year: Optional[int] = None
    is_dismissed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Non-table schemas (request / response)
# ---------------------------------------------------------------------------

class CategoryCreate(SQLModel):
    name: str
    color: str
    icon: str


class CategoryRead(SQLModel):
    id: int
    name: str
    color: str
    icon: str
    created_at: datetime


# --- Expense schemas --------------------------------------------------------

class ExpenseCreate(SQLModel):
    amount: float
    description: str
    category_id: Optional[int] = None
    merchant: Optional[str] = None
    date: date
    is_recurring: bool = False
    recurring_id: Optional[int] = None
    notes: Optional[str] = None


class ExpenseRead(SQLModel):
    id: int
    amount: float
    description: str
    category_id: Optional[int]
    category: Optional[CategoryRead] = None
    merchant: Optional[str]
    date: date
    is_recurring: bool
    recurring_id: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# --- Budget schemas ---------------------------------------------------------

class BudgetCreate(SQLModel):
    category_id: int
    monthly_limit: float
    month: int
    year: int


class BudgetRead(SQLModel):
    id: int
    category_id: int
    monthly_limit: float
    month: int
    year: int
    created_at: datetime


# --- RecurringRule schemas --------------------------------------------------

class RecurringRuleCreate(SQLModel):
    name: str
    amount: float
    category_id: Optional[int] = None
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    next_due_date: date
    is_active: bool = True


class RecurringRuleRead(SQLModel):
    id: int
    name: str
    amount: float
    category_id: Optional[int]
    frequency: str
    next_due_date: date
    last_run_date: Optional[date]
    is_active: bool
    created_at: datetime


# --- AIInsight schema -------------------------------------------------------

class AIInsightRead(SQLModel):
    id: int
    type: str
    title: str
    content: str
    severity: Optional[str]
    month: Optional[int]
    year: Optional[int]
    is_dismissed: bool
    created_at: datetime
