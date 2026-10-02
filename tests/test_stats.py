"""Tests for stats.py -- dashboard numbers must come from the saved results."""
from app import results, stats


def save(tid, status, outcome, reason, priority="normal", ms=4000, pending=None):
    results.save_result(tid, status, outcome, reason, priority, pending_action=pending)
    results.update_result(tid, duration_ms=ms)


def test_empty_database_gives_zeroes(store):
    s = stats.compute_stats()
    assert s["processed"] == 0 and s["auto_resolved_pct"] == 0.0 and s["total_tickets"] >= 150

def test_numbers_add_up(store):
    save(1, "auto_resolved", "auto_resolved", "handled_by_agent", ms=2000)
    save(2, "auto_resolved", "auto_resolved", "handled_by_agent", ms=6000)
    save(3, "asked_question", "asked_question", "multiple_orders_ask_which_one", ms=1000)
    save(4, "waiting_for_human", "escalated", "angry_customer", "high", ms=50)
    save(5, "human_approved", "escalated", "above_auto_limit", ms=3000, pending={"type": "refund"})
    s = stats.compute_stats()
    assert s["processed"] == 5 and s["auto_resolved"] == 2 and s["asked_question"] == 1 and s["escalated"] == 2
    assert s["auto_resolved_pct"] == 40.0                      # 2 of 5; the question does not count as resolved
    assert s["waiting_for_human"] == 1 and s["high_priority_waiting"] == 1 and s["human_approved"] == 1
    assert s["avg_handling_seconds"] == 2.4                     # (2000+6000+1000+50+3000)/5 ms
    assert s["estimated_minutes_saved"] == 15                   # 2 tickets x 7.5 min
    assert {r["reason"] for r in s["escalation_reasons"]} == {"angry_customer", "above_auto_limit"}

def test_refund_totals_come_from_the_refunds_table(store):
    from app import actions
    from tests.conftest import ALICE
    actions.issue_refund(9001, ALICE)
    s = stats.compute_stats()
    assert s["refund_count"] == 1 and s["refund_total"] == 24.99
