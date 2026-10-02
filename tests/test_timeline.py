"""Tests for timeline.py -- raw audit rows become friendly steps."""
from app.timeline import build_timeline


def row(step, detail, t="2026-10-01 10:00:05"):
    return {"step": step, "detail": detail, "created_at": t}


def test_refund_steps_read_like_the_brief():
    trail = [
        row("ticket_received", {}),
        row("screen", {"action": "pass", "reason": "ok", "priority": "normal"}),
        row("intent", {"ok": True, "intents": ["refund"], "order_id": 1043}),
        row("tool_call", {"name": "lookup_order", "args": {"order_id": 1043},
                          "result": {"found": True, "item": "Wireless Mouse", "amount": 24.99, "status": "delivered"}}),
        row("tool_call", {"name": "issue_refund", "args": {"order_id": 1043},
                          "result": {"executed": True, "amount": 24.99, "approved_by": "auto"}}),
        row("grounding", {"ok": True, "problems": [], "retry": False}),
        row("reply_sent_simulated", {}),
    ]
    items = build_timeline(trail)
    titles = [i["title"] for i in items]
    assert "Looked up order #1043" in titles
    assert any("Refunded $24.99 (simulated)" in t for t in titles)
    assert titles[-1] == "Reply sent (simulated)"
    assert items[0]["time"] == "10:00:05"
    assert [i["kind"] for i in items][-3:] == ["ok", "ok", "ok"]

def test_blocked_and_failed_steps_are_marked():
    items = build_timeline([
        row("screen", {"action": "escalate", "reason": "prompt_injection", "priority": "high", "message": "Tries to override rules."}),
        row("tool_call", {"name": "track_shipment", "args": {"order_id": 1}, "error": "RuntimeError"}),
        row("grounding", {"ok": False, "problems": ["amount $99 not found in tool results"], "retry": False}),
        row("tool_call", {"name": "issue_refund", "args": {"order_id": 2},
                          "result": {"executed": False, "decision": "denied", "reason": "outside_30_day_window", "message": "Too old."}}),
    ])
    assert [i["kind"] for i in items] == ["stop", "stop", "warn", "stop"]
    assert "prompt injection" in items[0]["title"]
    assert "outside 30 day window" in items[3]["title"]

def test_other_persons_order_reveals_nothing():
    item = build_timeline([row("tool_call", {"name": "lookup_order", "args": {"order_id": 9011},
                                              "result": {"found": False, "reason": "order_not_found_on_account"}})])[0]
    assert "not found on this account" in item["title"] and item["kind"] == "warn"

def test_human_steps():
    items = build_timeline([row("human_refund", {"executed": True, "amount": 119.99, "approved_by": "sara"}),
                            row("human_approved", {"by": "sara", "edited": True}),
                            row("human_rejected", {"by": "sara"})])
    assert "$119.99" in items[0]["title"] and "reply edited" in items[1]["title"] and items[2]["kind"] == "stop"
