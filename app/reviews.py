"""
reviews.py -- a human reviewer checks the tickets that the AI resolved ("self-validation").

For each AI-resolved ticket (status auto_resolved or asked_question) the reviewer says:
  correct    the AI did the right thing and the reply is good
  incorrect  something is wrong (a reason is required)
  unsure     the reviewer cannot tell
A review belongs to the reply that was reviewed. If the ticket is processed again and the reply changes,
the old review is marked 'stale' and the ticket counts as not reviewed again.
"""
from datetime import datetime

from app import results
from app.db import get_conn

VERDICTS = ("correct", "incorrect", "unsure")
REASONS = {
    "wrong_action": "Wrong action (refund or address)",
    "wrong_fact": "Wrong fact in the reply",
    "unhelpful_reply": "Reply does not help the customer",
    "should_have_escalated": "Should have gone to a human",
    "policy_issue": "Policy applied wrongly",
    "other": "Other",
}
AI_RESOLVED = ("auto_resolved", "asked_question")


def _ensure(con):
    con.execute("""CREATE TABLE IF NOT EXISTS reviews (
        ticket_id INTEGER PRIMARY KEY, verdict TEXT, reason TEXT, note TEXT, reviewer TEXT,
        reviewed_at TEXT, reply_at_review TEXT)""")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_review(ticket_id: int, verdict: str, reason: str | None = None, note: str | None = None,
                reviewer: str = "reviewer") -> dict:
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if verdict == "incorrect" and reason not in REASONS:
        raise ValueError("A reason is required when a ticket is marked incorrect.")
    if verdict != "incorrect":
        reason = None
    res = results.get_result(ticket_id)
    if not res or res["status"] not in AI_RESOLVED:
        raise ValueError("Only tickets that the AI resolved can be reviewed.")
    con = get_conn()
    try:
        _ensure(con)
        con.execute("INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?,?,?)",
                    (ticket_id, verdict, reason, (note or "").strip() or None, reviewer, _now(), res["reply"]))
        con.commit()
    finally:
        con.close()
    return get_review(ticket_id)


def get_review(ticket_id: int) -> dict | None:
    con = get_conn()
    try:
        _ensure(con)
        row = con.execute("SELECT * FROM reviews WHERE ticket_id = ?", (ticket_id,)).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    d = dict(row)
    res = results.get_result(ticket_id)
    d["stale"] = not res or res["status"] not in AI_RESOLVED or (res["reply"] or "") != (d.pop("reply_at_review") or "")
    d["reason_text"] = REASONS.get(d["reason"])
    return d


def delete_review(ticket_id: int) -> bool:
    con = get_conn()
    try:
        _ensure(con)
        cur = con.execute("DELETE FROM reviews WHERE ticket_id = ?", (ticket_id,))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def review_stats() -> dict:
    """Numbers for the dashboard. Stale reviews count as 'not reviewed'."""
    results.ensure_table()
    con = get_conn()
    try:
        _ensure(con)
        resolved = con.execute("SELECT ticket_id, reply FROM ticket_results WHERE status IN ('auto_resolved','asked_question')").fetchall()
        reviews = {r["ticket_id"]: dict(r) for r in con.execute("SELECT * FROM reviews").fetchall()}
    finally:
        con.close()
    counts = {"correct": 0, "incorrect": 0, "unsure": 0}
    reasons = {}
    for r in resolved:
        rv = reviews.get(r["ticket_id"])
        if rv and (rv["reply_at_review"] or "") == (r["reply"] or ""):
            counts[rv["verdict"]] += 1
            if rv["verdict"] == "incorrect":
                reasons[rv["reason"]] = reasons.get(rv["reason"], 0) + 1
    reviewed = sum(counts.values())
    decided = counts["correct"] + counts["incorrect"]
    return {
        "ai_resolved": len(resolved), "reviewed": reviewed, "unreviewed": len(resolved) - reviewed,
        **counts,
        "agreement_pct": round(100 * counts["correct"] / decided, 1) if decided else 0.0,
        "reasons": [{"reason": k, "text": REASONS.get(k, k), "count": v} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])],
    }


def all_states() -> dict:
    """ticket_id -> {'verdict', 'reason', 'stale', 'reviewer', 'reviewed_at'} for every ticket that has a review."""
    results.ensure_table()
    con = get_conn()
    try:
        _ensure(con)
        reviews = con.execute("SELECT * FROM reviews").fetchall()
        replies = {r["ticket_id"]: (r["status"], r["reply"] or "") for r in con.execute("SELECT ticket_id, status, reply FROM ticket_results")}
    finally:
        con.close()
    out = {}
    for r in reviews:
        status, reply = replies.get(r["ticket_id"], (None, ""))
        out[r["ticket_id"]] = {"verdict": r["verdict"], "reason": r["reason"], "reason_text": REASONS.get(r["reason"]),
                               "note": r["note"], "reviewer": r["reviewer"], "reviewed_at": r["reviewed_at"],
                               "stale": status not in AI_RESOLVED or reply != (r["reply_at_review"] or "")}
    return out
