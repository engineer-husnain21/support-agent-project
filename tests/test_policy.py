"""Tests for policy.py -- no database, only rules."""
from datetime import date, timedelta
import pytest
from app import policy

TODAY = date(2026, 9, 30)


def order(amount=25.0, status="delivered", days_ago=10, refunded=False):
    d = (TODAY - timedelta(days=days_ago)).isoformat() if status == "delivered" else None
    return {"found": True, "amount": amount, "status": status, "delivered_date": d, "refunded": refunded}


# ---- refund: amount ----
def test_small_refund_allowed():
    assert policy.check_refund(order(24.99), TODAY).decision == "allowed"

def test_exactly_50_dollars_allowed():
    assert policy.check_refund(order(50.00), TODAY).decision == "allowed"

def test_50_01_needs_human():
    d = policy.check_refund(order(50.01), TODAY)
    assert (d.decision, d.reason) == ("needs_human", "above_auto_limit")

def test_80_dollars_needs_human():
    assert policy.check_refund(order(80.0), TODAY).decision == "needs_human"


# ---- refund: 30-day window ----
@pytest.mark.parametrize("days,expected", [(1, "allowed"), (29, "allowed"), (30, "allowed"),
                                           (31, "denied"), (35, "denied"), (60, "denied")])
def test_refund_window(days, expected):
    assert policy.check_refund(order(20.0, days_ago=days), TODAY).decision == expected

def test_outside_window_reason():
    assert policy.check_refund(order(20.0, days_ago=35), TODAY).reason == "outside_30_day_window"

def test_outside_window_beats_large_amount():
    # $120 and 35 days: sending it to a human is pointless, so it is denied outright
    assert policy.check_refund(order(120.0, days_ago=35), TODAY).decision == "denied"


# ---- refund: other rules ----
@pytest.mark.parametrize("status", ["processing", "shipped"])
def test_not_delivered_denied(status):
    d = policy.check_refund(order(status=status), TODAY)
    assert (d.decision, d.reason) == ("denied", "not_delivered")

def test_double_refund_denied():
    d = policy.check_refund(order(refunded=True), TODAY)
    assert (d.decision, d.reason) == ("denied", "already_refunded")

def test_missing_order_denied():
    assert policy.check_refund(None, TODAY).decision == "denied"
    assert policy.check_refund({"found": False}, TODAY).reason == "order_not_found_on_account"


# ---- address ----
def test_address_processing_allowed():
    assert policy.check_address_change(order(status="processing")).decision == "allowed"

def test_address_shipped_denied():
    d = policy.check_address_change(order(status="shipped"))
    assert (d.decision, d.reason) == ("denied", "already_shipped")

def test_address_delivered_denied():
    assert policy.check_address_change(order(status="delivered")).reason == "already_delivered"

def test_address_missing_order_denied():
    assert policy.check_address_change(None).decision == "denied"
