"""actions.py ke tests -- yahan check hota hai ke galat kaam hota hi nahi."""
import inspect
import sqlite3
from app import actions, db
from tests.conftest import ALICE, BOB


def refunded_flag(oid):
    con = db.get_conn()
    try:
        return con.execute("SELECT refunded FROM orders WHERE order_id=?", (oid,)).fetchone()["refunded"]
    finally:
        con.close()

def address_of(oid):
    con = db.get_conn()
    try:
        return con.execute("SELECT shipping_address FROM orders WHERE order_id=?", (oid,)).fetchone()["shipping_address"]
    finally:
        con.close()


# ---- refund ----
def test_small_refund_executes(store):
    r = actions.issue_refund(9001, ALICE)
    assert r["executed"] and r["simulated"] and r["amount"] == 24.99 and r["approved_by"] == "auto"
    assert refunded_flag(9001) == 1

def test_double_refund_blocked(store):
    actions.issue_refund(9001, ALICE)
    r = actions.issue_refund(9001, ALICE)
    assert r["executed"] is False and r["reason"] == "already_refunded"

def test_large_refund_blocked_without_human(store):
    r = actions.issue_refund(9002, ALICE)
    assert r["executed"] is False and r["decision"] == "needs_human"
    assert refunded_flag(9002) == 0

def test_large_refund_works_with_human_approval(store):
    r = actions.issue_refund(9002, ALICE, approved_by_human=True, approved_by="agent_sara")
    assert r["executed"] and r["amount"] == 119.99 and r["approved_by"] == "agent_sara"
    assert refunded_flag(9002) == 1

def test_human_cannot_override_30_day_rule(store):
    r = actions.issue_refund(9003, ALICE, approved_by_human=True, approved_by="agent_sara")
    assert r["executed"] is False and r["reason"] == "outside_30_day_window"

def test_human_cannot_double_refund(store):
    r = actions.issue_refund(9010, ALICE, approved_by_human=True)
    assert r["executed"] is False and r["reason"] == "already_refunded"

def test_boundaries(store):
    assert actions.issue_refund(9004, ALICE)["executed"] is True      # bilkul 30 din
    assert actions.issue_refund(9005, ALICE)["executed"] is False     # 31 din
    assert actions.issue_refund(9006, ALICE)["executed"] is True      # bilkul $50
    assert actions.issue_refund(9007, ALICE)["executed"] is False     # $50.01 -> human

def test_cannot_refund_undelivered(store):
    assert actions.issue_refund(9008, ALICE)["reason"] == "not_delivered"
    assert actions.issue_refund(9009, ALICE)["reason"] == "not_delivered"

def test_cannot_refund_someone_elses_order(store):
    r = actions.issue_refund(9011, ALICE)
    assert r["executed"] is False and r["reason"] == "order_not_found_on_account"
    assert refunded_flag(9011) == 0

def test_refund_has_no_amount_parameter():
    # amount hamesha DB se aata hai; "refund $500" jaisi baat kisi parameter se ghus hi nahi sakti
    assert "amount" not in inspect.signature(actions.issue_refund).parameters


# ---- address ----
def test_address_change_when_processing(store):
    r = actions.update_address(9008, ALICE, "55 New Street, Seattle, WA")
    assert r["executed"] and address_of(9008) == "55 New Street, Seattle, WA"

def test_address_change_blocked_when_shipped(store):
    before = address_of(9009)
    r = actions.update_address(9009, ALICE, "55 New Street, Seattle, WA")
    assert r["executed"] is False and r["reason"] == "already_shipped"
    assert address_of(9009) == before

def test_address_change_other_persons_order(store):
    r = actions.update_address(9011, ALICE, "55 New Street, Seattle, WA")
    assert r["executed"] is False and r["reason"] == "order_not_found_on_account"

def test_address_too_short_rejected(store):
    r = actions.update_address(9008, ALICE, "x")
    assert r["executed"] is False and r["reason"] == "invalid_address"
