"""
stats.py -- the numbers on the dashboard. Every number comes from the database, nothing is typed in by hand.

Definitions (these must match METRICS.md):
  processed          = tickets that have a row in ticket_results
  auto-resolved %    = tickets with outcome 'auto_resolved' / processed tickets
                       ('asked_question' is NOT counted as resolved)
  escalations        = tickets with outcome 'escalated' (waiting or already handled by a human)
  avg handling time  = average agent processing time per ticket (screen + LLM calls + tools)
"""
import json
from app import results
from app.db import get_conn

# The brief says a human needs 5-10 minutes per ticket; we use the midpoint as an ESTIMATE only.
MINUTES_PER_TICKET_ESTIMATE = 7.5


def _escalation_reasons(rows) -> list:
    counts = {}
    for r in rows:
        if r["outcome"] == "escalated":
            counts[r["reason"]] = counts.get(r["reason"], 0) + 1
    return [{"reason": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def compute_stats() -> dict:
    results.ensure_table()
    con = get_conn()
    try:
        total_tickets = con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        rows = con.execute("SELECT status, outcome, reason, priority, duration_ms FROM ticket_results").fetchall()
        has_refunds = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='refunds'").fetchone()
        refunds = con.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM refunds").fetchone() if has_refunds else (0, 0)
    finally:
        con.close()

    processed = len(rows)
    count = lambda **kw: sum(1 for r in rows if all(r[k] == v for k, v in kw.items()))
    auto = count(outcome="auto_resolved")
    durations = [r["duration_ms"] for r in rows if r["duration_ms"]]

    return {
        "total_tickets": total_tickets,
        "processed": processed,
        "new": total_tickets - processed,
        "auto_resolved": auto,
        "asked_question": count(outcome="asked_question"),
        "escalated": count(outcome="escalated"),
        "waiting_for_human": count(status="waiting_for_human"),
        "human_approved": count(status="human_approved"),
        "human_rejected": count(status="human_rejected"),
        "high_priority_waiting": sum(1 for r in rows if r["status"] == "waiting_for_human" and r["priority"] == "high"),
        "auto_resolved_pct": round(100 * auto / processed, 1) if processed else 0.0,
        "escalation_reasons": _escalation_reasons(rows),
        "avg_handling_seconds": round(sum(durations) / len(durations) / 1000, 1) if durations else 0.0,
        "refund_count": refunds[0],
        "refund_total": round(refunds[1], 2),
        "estimated_minutes_saved": round(auto * MINUTES_PER_TICKET_ESTIMATE),
        "minutes_per_ticket_assumption": MINUTES_PER_TICKET_ESTIMATE,
    }
