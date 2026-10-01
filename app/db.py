"""db.py -- database connection helpers. Every other module gets its connection from here."""
import os
import sqlite3
from datetime import date

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "store.db")


def db_path() -> str:
    # Tests set STORE_DB to point at a throwaway copy, so the real database is never touched.
    return os.environ.get("STORE_DB", DEFAULT_DB)


def get_conn() -> sqlite3.Connection:
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def store_today() -> date:
    """The store's fixed 'today': the date make_mock_data.py generated the data on.
    Using it keeps the 30-day window maths identical on demo day."""
    con = get_conn()
    try:
        row = con.execute("SELECT value FROM meta WHERE key='store_today'").fetchone()
    finally:
        con.close()
    return date.fromisoformat(row["value"])
