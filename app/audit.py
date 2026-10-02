"""
audit.py -- a record of every step. The dashboard's audit trail and the step timeline are built from this table.
Each entry: which ticket, which step, the details of that step (JSON), and when.
"""
import json
from datetime import datetime
from app.db import get_conn


def _ensure(con):
    con.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, step TEXT, detail TEXT, created_at TEXT)""")


def log(ticket_id: int, step: str, detail: dict | None = None) -> None:
    con = get_conn()
    try:
        _ensure(con)
        con.execute("INSERT INTO audit_log (ticket_id, step, detail, created_at) VALUES (?,?,?,?)",
                    (ticket_id, step, json.dumps(detail or {}, default=str),
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit()
    finally:
        con.close()


def get_trail(ticket_id: int) -> list[dict]:
    con = get_conn()
    try:
        _ensure(con)
        rows = con.execute("SELECT step, detail, created_at FROM audit_log WHERE ticket_id = ? ORDER BY id",
                           (ticket_id,)).fetchall()
    finally:
        con.close()
    return [{"step": r["step"], "detail": json.loads(r["detail"]), "created_at": r["created_at"]} for r in rows]


def clear(ticket_id: int) -> None:
    """Remove the old trail of a ticket (used when a ticket is processed again, so the timeline shows only the latest run)."""
    con = get_conn()
    try:
        _ensure(con)
        con.execute("DELETE FROM audit_log WHERE ticket_id = ?", (ticket_id,))
        con.commit()
    finally:
        con.close()
