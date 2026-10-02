"""Tests for democases.py -- the 14 client-ready test cases must really behave as the brief describes."""
from datetime import date

import pytest
from app import db, democases, results, tickets
from app.pipeline import process_ticket
from tests.fake_llm import SmartFakeClient


def order(oid):
    con = db.get_conn()
    try:
        return dict(con.execute("""SELECT o.*, c.email FROM orders o JOIN customers c USING(customer_id) WHERE order_id=?""",
                                (oid,)).fetchone())
    finally:
        con.close()


@pytest.fixture()
def demo(store):
    made = democases.create_demo_tickets()
    return {m["case"]: m for m in made}


def test_all_tickets_exist_with_the_planned_ids(demo):
    assert sorted(m["ticket_id"] for m in demo.values()) == list(range(201, 217))
    assert demo["1"]["body"] == "Where is my order #1042?"
    assert all(tickets.get_ticket(m["ticket_id"]) for m in demo.values())

def test_the_orders_have_the_properties_each_case_needs(demo, store):
    today = db.store_today()
    days = lambda o: (today - date.fromisoformat(o["delivered_date"])).days
    assert order(demo["1"]["order_id"])["status"] == "shipped"
    o2 = order(demo["2"]["order_id"]); assert (o2["amount"], days(o2)) == (24.99, 10)
    assert order(demo["3"]["order_id"])["status"] == "processing"
    o4 = order(demo["4"]["order_id"]); assert o4["amount"] == 119.99
    o5 = order(demo["5"]["order_id"]); assert 60 <= o5["amount"] <= 100 and days(o5) <= 29
    o6 = order(demo["6"]["order_id"]); assert o6["amount"] <= 50 and 33 <= days(o6) <= 45
    assert order(demo["8"]["order_id"])["status"] == "processing"
    assert order(demo["9"]["order_id"])["status"] == "shipped"
    # case 11: the sender is NOT the owner of the order
    assert order(demo["11"]["order_id"])["email"] != demo["11"]["email"]

def test_every_ticket_has_its_own_customer(demo):
    emails = [m["email"] for m in demo.values()]
    assert len(set(emails)) == len(emails)

def test_creating_twice_replaces_the_old_tickets(store):
    democases.create_demo_tickets()
    process_ticket(201, client=SmartFakeClient())
    democases.create_demo_tickets()
    assert results.get_result(201) is None            # the old result was cleared
    con = db.get_conn()
    assert con.execute("SELECT COUNT(*) FROM tickets WHERE ticket_id BETWEEN 201 AND 216").fetchone()[0] == 16
    con.close()

def test_all_cases_behave_as_the_brief_describes(demo, store, monkeypatch):
    client = SmartFakeClient()
    got = {case: process_ticket(m["ticket_id"], client=client) for case, m in demo.items() if case not in ("13", "14")}
    refunded = lambda case: bool(order(demo[case]["order_id"])["refunded"])

    assert got["1"]["status"] == "auto_resolved"                                           # tracking
    assert got["2"]["status"] == "auto_resolved" and refunded("2")                          # $24.99 refund done
    assert got["3"]["status"] == "auto_resolved"                                           # address updated
    assert order(demo["3"]["order_id"])["shipping_address"] == "55 New Street, Seattle, WA"
    assert (got["4"]["status"], got["4"]["reason"]) == ("waiting_for_human", "above_auto_limit") and not refunded("4")
    assert got["5"]["reason"] == "above_auto_limit" and not refunded("5")                   # about $80
    assert got["6"]["status"] == "auto_resolved" and not refunded("6")                      # day 35: refused
    assert got["7"]["status"] == "asked_question"                                          # several orders
    assert got["7b"]["status"] == "auto_resolved"                                          # one order found by email
    assert got["8"]["status"] == "auto_resolved"                                           # both requests
    assert order(demo["8"]["order_id"])["shipping_address"] == "77 Pine Road, Denver, CO"
    before = order(demo["9"]["order_id"])["shipping_address"]
    assert got["9"]["status"] == "auto_resolved" and order(demo["9"]["order_id"])["shipping_address"] == before
    assert got["10"]["reason"] == "prompt_injection" and not refunded("10")                # injection
    assert got["11"]["status"] == "auto_resolved" and "could not find" in got["11"]["reply"].lower()
    assert (got["12"]["reason"], got["12"]["priority"]) == ("angry_customer", "high")
    assert (got["12b"]["reason"], got["12b"]["priority"]) == ("legal_threat", "high")

    # case 13: a tool fails
    monkeypatch.setenv("FAIL_TOOL", "track_shipment")
    out = process_ticket(demo["13"]["ticket_id"], client=SmartFakeClient())
    assert (out["status"], out["reason"]) == ("waiting_for_human", "system_unavailable")
    monkeypatch.delenv("FAIL_TOOL")

    # human approves the $120 refund of case 4
    from app import human_queue
    assert human_queue.approve(demo["4"]["ticket_id"], "sara")["ok"] and refunded("4")


def test_grounding_demo_script_blocks_the_simulated_mistake(demo, store):
    import runpy, sys
    from app import audit
    sys.argv = ["demo_grounding.py"]
    runpy.run_path("demo_grounding.py", run_name="__main__")
    steps = [a["step"] for a in audit.get_trail(214)]
    trail = {a["step"]: a for a in audit.get_trail(214)}
    assert steps.count("grounding") == 2 and results.get_result(214)["status"] == "auto_resolved"
    first = [a for a in audit.get_trail(214) if a["step"] == "grounding"][0]["detail"]
    assert first["ok"] is False and any("99.00" in p for p in first["problems"])

    sys.argv = ["demo_grounding.py", "--persist"]
    runpy.run_path("demo_grounding.py", run_name="__main__")
    assert results.get_result(214)["reason"] == "ungrounded_reply"
