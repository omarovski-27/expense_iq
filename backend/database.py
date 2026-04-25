import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

base_dir = os.path.dirname(os.path.abspath(__file__))
database_url = os.getenv("DATABASE_URL", "sqlite:///../data/expenses.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url.startswith(("sqlite", "postgresql://")):
    database_url = f"sqlite:///{database_url}"

if database_url.startswith("sqlite:///"):
    sqlite_path = database_url.replace("sqlite:///", "", 1)
    if not os.path.isabs(sqlite_path):
        sqlite_path = os.path.abspath(os.path.join(base_dir, sqlite_path))
    database_url = f"sqlite:///{sqlite_path.replace(os.sep, '/')}"

if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
    )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
