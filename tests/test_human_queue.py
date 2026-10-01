"""Tests for human_queue.py -- the Approve / Reject rules."""
from app import db, human_queue, results
from tests.conftest import ALICE, add_ticket


def waiting(ticket_id, order_id, amount=119.99, reply="Approved."):
    results.save_result(ticket_id, "waiting_for_human", "escalated", "above_auto_limit", "normal", reply=reply,
                        pending_action={"type": "refund", "order_id": order_id, "amount": amount, "item": "Test Item"})


def refunded_flag(oid):
    con = db.get_conn()
    try:
        return con.execute("SELECT refunded FROM orders WHERE order_id=?", (oid,)).fetchone()["refunded"]
    finally:
        con.close()


def test_approve_uses_the_edited_reply(store):
    add_ticket(9501, "Refund order #9002", ALICE)
    waiting(9501, 9002)
    out = human_queue.approve(9501, "sara", edited_reply="Hi Alice, all sorted!")
    assert out["ok"] and results.get_result(9501)["reply"] == "Hi Alice, all sorted!"

def test_cannot_approve_twice(store):
    add_ticket(9502, "Refund order #9002", ALICE)
    waiting(9502, 9002)
    assert human_queue.approve(9502, "sara")["ok"]
    assert human_queue.approve(9502, "sara") == {"ok": False, "error": "ticket_not_waiting_for_human"}

def test_human_cannot_approve_an_expired_refund(store):
    add_ticket(9503, "Refund order #9003", ALICE)
    waiting(9503, 9003)                      # delivered 35 days ago
    out = human_queue.approve(9503, "sara")
    assert out["ok"] is False and out["error"] == "refund_blocked"
    assert refunded_flag(9003) == 0 and results.get_result(9503)["status"] == "waiting_for_human"

def test_approve_without_any_reply_is_refused(store):
    add_ticket(9504, "Something odd", ALICE)
    results.save_result(9504, "waiting_for_human", "escalated", "legal_threat", "high", reply=None)
    assert human_queue.approve(9504, "sara")["error"] == "no_reply_to_send"

def test_reject_works_and_is_recorded(store):
    add_ticket(9505, "Refund order #9002", ALICE)
    waiting(9505, 9002)
    out = human_queue.reject(9505, "sara")
    assert out["ok"] and results.get_result(9505)["status"] == "human_rejected" and refunded_flag(9002) == 0

def test_unknown_ticket(store):
    assert human_queue.approve(123456)["ok"] is False
