"""
results.py -- one row per ticket describing what happened to it (the 'ticket_results' table).
The UI (ticket list, human queue, dashboard) reads from here.

status  : auto_resolved | asked_question | waiting_for_human | human_approved | human_rejected
outcome : auto_resolved | asked_question | escalated   (used later to compare against the expected labels)
"""
import json
from datetime import datetime
from app.db import get_conn


def _ensure(con):
    con.execute("""CREATE TABLE IF NOT EXISTS ticket_results (
        ticket_id INTEGER PRIMARY KEY, status TEXT, outcome TEXT, reason TEXT, priority TEXT,
        reply TEXT, summary TEXT, pending_action TEXT, reply_sent INTEGER DEFAULT 0,
        handled_by TEXT, updated_at TEXT, duration_ms INTEGER)""")
    columns = [r[1] for r in con.execute("PRAGMA table_info(ticket_results)").fetchall()]
    if "duration_ms" not in columns:   # table created by an older version of the code
        con.execute("ALTER TABLE ticket_results ADD COLUMN duration_ms INTEGER")


def ensure_table() -> None:
    """Create the results table if it does not exist yet (used by the API and the stats)."""
    con = get_conn()
    try:
        _ensure(con)
        con.commit()
    finally:
        con.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_result(ticket_id, status, outcome, reason, priority="normal", reply=None, summary=None,
                pending_action=None, reply_sent=False, handled_by="agent") -> None:
    con = get_conn()
    try:
        _ensure(con)
        con.execute("""INSERT OR REPLACE INTO ticket_results
                       (ticket_id, status, outcome, reason, priority, reply, summary, pending_action,
                        reply_sent, handled_by, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (ticket_id, status, outcome, reason, priority, reply, summary,
                     json.dumps(pending_action) if pending_action else None,
                     1 if reply_sent else 0, handled_by, _now()))
        con.commit()
    finally:
        con.close()


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["pending_action"] = json.loads(d["pending_action"]) if d["pending_action"] else None
    d["reply_sent"] = bool(d["reply_sent"])
    return d


def get_result(ticket_id: int) -> dict | None:
    con = get_conn()
    try:
        _ensure(con)
        row = con.execute("SELECT * FROM ticket_results WHERE ticket_id = ?", (ticket_id,)).fetchone()
    finally:
        con.close()
    return _row_to_dict(row) if row else None


def list_results(status: str | None = None) -> list[dict]:
    con = get_conn()
    try:
        _ensure(con)
        if status:
            rows = con.execute("SELECT * FROM ticket_results WHERE status = ? ORDER BY ticket_id", (status,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM ticket_results ORDER BY ticket_id").fetchall()
    finally:
        con.close()
    return [_row_to_dict(r) for r in rows]


def update_result(ticket_id: int, **fields) -> None:
    allowed = {"status", "reply", "reply_sent", "handled_by", "duration_ms"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Cannot update fields: {sorted(bad)}")
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields) + ", updated_at = ?"
    values = [int(v) if k in ("reply_sent", "duration_ms") else v for k, v in fields.items()] + [_now(), ticket_id]
    con = get_conn()
    try:
        _ensure(con)
        con.execute(f"UPDATE ticket_results SET {sets} WHERE ticket_id = ?", values)
        con.commit()
    finally:
        con.close()
