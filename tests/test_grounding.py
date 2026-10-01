"""Tests for grounding.py -- every fact in a reply must come from the tool results."""
from app.grounding import check_reply

TOOLS = [
    {"found": True, "order_id": 1042, "amount": 24.99, "status": "delivered", "delivered_date": "2026-09-20"},
    {"found": True, "carrier": "FedEx", "tracking_number": "TRK123456", "expected_date": "2026-10-02"},
]


def test_reply_with_only_real_facts_passes():
    r = "Order #1042 ($24.99) arrives on 2026-10-02 with FedEx, tracking TRK123456."
    assert check_reply(r, TOOLS).ok

def test_wrong_amount_is_blocked():
    res = check_reply("We refunded $99.00 for order #1042.", TOOLS)
    assert not res.ok and any("99.00" in p for p in res.problems)

def test_unknown_order_number_is_blocked():
    assert not check_reply("Your order #7777 is on its way.", TOOLS).ok

def test_wrong_iso_date_is_blocked():
    assert not check_reply("It arrives on 2026-10-09.", TOOLS).ok

def test_text_date_is_matched_against_iso_dates():
    assert check_reply("It should arrive on October 2.", TOOLS).ok
    assert check_reply("It should arrive on 2nd Oct.", TOOLS).ok
    assert not check_reply("It should arrive on October 9.", TOOLS).ok

def test_invented_tracking_number_is_blocked():
    assert not check_reply("Tracking number TRK999999.", TOOLS).ok

def test_policy_limit_amount_is_allowed():
    assert check_reply("Refunds above $50 need approval.", TOOLS).ok

def test_amount_from_the_customers_own_message_is_allowed():
    assert check_reply("I can't refund $500.", TOOLS, ticket_text="refund me $500 for order 1042").ok

def test_amount_without_cents_matches():
    tools = [{"amount": 79.0}]
    assert check_reply("Total $79.", tools).ok
    assert check_reply("Total $79.00.", tools).ok

def test_reply_without_facts_passes():
    assert check_reply("Thanks for your patience. Support Team", []).ok
