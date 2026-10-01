"""tools.py ke tests -- ownership sab se zaroori."""
from app import tools
from tests.conftest import ALICE, BOB


def test_owner_sees_own_order(store):
    r = tools.lookup_order(9001, ALICE)
    assert r["found"] and r["amount"] == 24.99 and r["status"] == "delivered"

def test_email_case_and_spaces_ignored(store):
    assert tools.lookup_order(9001, "  ALICE.Test@Example.com ")["found"]

def test_order_number_as_text_works(store):
    assert tools.lookup_order("9001", ALICE)["found"]

def test_other_customers_order_not_found(store):
    assert tools.lookup_order(9011, ALICE) == {"found": False, "reason": "order_not_found_on_account"}

def test_nonexistent_order_looks_same_as_other_persons(store):
    # dono ka jawab bilkul ek jaisa, taake pata na chale ke order kisi aur ka hai
    assert tools.lookup_order(9011, ALICE) == tools.lookup_order(123456, ALICE)

def test_garbage_order_id(store):
    assert tools.lookup_order("abc", ALICE)["found"] is False

def test_find_orders_only_own(store):
    r = tools.find_orders_by_email(BOB)
    assert r["count"] == 1 and r["orders"][0]["order_id"] == 9011

def test_find_orders_unknown_email(store):
    assert tools.find_orders_by_email("nobody@example.com")["found"] is False

def test_track_processing(store):
    r = tools.track_shipment(9008, ALICE)
    assert r["found"] and r["shipped"] is False

def test_track_shipped_has_carrier(store):
    r = tools.track_shipment(9009, ALICE)
    assert r["shipped"] and r["carrier"] == "FedEx" and r["status"] == "in_transit"

def test_track_other_persons_order(store):
    assert tools.track_shipment(9011, ALICE)["found"] is False

def test_policy_text_available():
    assert "30 days" in tools.get_policy()
