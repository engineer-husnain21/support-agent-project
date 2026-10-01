"""db.py -- database se connection. Baaqi sab files yahin se connection leti hain."""
import os
import sqlite3
from datetime import date

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "store.db")


def db_path() -> str:
    # Tests STORE_DB set karke ek alag copy use karte hain, asli DB kharab nahi hoti.
    return os.environ.get("STORE_DB", DEFAULT_DB)


def get_conn() -> sqlite3.Connection:
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def store_today() -> date:
    """Store ki 'aaj' ki tareekh. make_mock_data.py ne jis din data banaya, wohi din.
    Isse 30 din wali ginti demo ke din bhi wahi rehti hai jo data banate waqt thi."""
    con = get_conn()
    try:
        row = con.execute("SELECT value FROM meta WHERE key='store_today'").fetchone()
    finally:
        con.close()
    return date.fromisoformat(row["value"])
