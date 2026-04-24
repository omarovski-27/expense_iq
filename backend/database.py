import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = os.path.join(_BASE_DIR, "..", "data", "expenses.db")
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_DB)
# Resolve relative paths to absolute so subprocess workers find the same file
if not os.path.isabs(DATABASE_URL):
    DATABASE_URL = os.path.join(_BASE_DIR, DATABASE_URL)
sqlite_url = f"sqlite:///{DATABASE_URL}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
