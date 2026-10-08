"""Tests for evidence.py and grounding.fact_table -- what the reviewer sees."""
import json
from app import audit, evidence, grounding, results
from app.pipeline import process_ticket
from tests.conftest import ALICE, BOB, ScriptedClient, add_ticket

TOOLS = [{"found": True, "order_id": 1042, "amount": 24.99, "delivered_date": "2026-09-20", "tracking_number": "TRK123"}]


def test_fact_table_says_where_each_fact_was_found():
    rows = grounding.fact_table("Order #1042: $24.99 on 2026-09-20, tracking TRK123. Refunds over $50 need approval.", TOOLS, "refund order #1042")
    by = {(r["kind"], r["value"]): r for r in rows}
    assert by[("Order number", "#1042")]["where"] == "system data"
    assert by[("Amount", "$24.99")]["where"] == "system data"
    assert by[("Amount", "$50.00")]["where"] == "policy limit"
    assert by[("Date", "2026-09-20")]["ok"] and by[("Tracking number", "TRK123")]["ok"]

def test_fact_table_flags_a_fact_that_was_found_nowhere():
    rows = grounding.fact_table("We refunded $99.00 for order #7777 on 2026-12-25.", TOOLS, "")
    assert [r["ok"] for r in rows] == [False, False, False]
    assert {r["value"] for r in rows} == {"#7777", "$99.00", "2026-12-25"}

def test_fact_table_accepts_customer_stated_values():
    rows = grounding.fact_table("I cannot refund $500.", [], "please refund $500")
    assert rows[0]["where"] == "customer message"

def test_evidence_for_a_refund(store):
    add_ticket(9901, "I want a refund for order #9001.", ALICE)
    client = ScriptedClient(['{"intents": ["refund"], "new_address": null}', {"tool_calls": [("issue_refund", {"order_id": 9001})]},
                             "Hi, your refund of $24.99 for order #9001 was issued. Support Team"])
    process_ticket(9901, client=client)
    ev = evidence.build_evidence(9901)
    assert ev["facts_ok"] and ev["llm_used"] and ev["tools_used"] == 1
    d = ev["decisions"][0]
    assert d["ok"] and "$24.99 executed" in d["title"] and "within 30 days" in d["why"]
    assert ev["order_now"]["refunded"] is True and ev["order_now"]["refund_records"][0]["amount"] == 24.99

def test_evidence_for_a_refusal(store):
    add_ticket(9902, "I want a refund for order #9003.", ALICE)
    client = ScriptedClient(['{"intents": ["refund"], "new_address": null}', {"tool_calls": [("issue_refund", {"order_id": 9003})]},
                             "Sorry, order #9003 is past the 30-day refund window. Support Team"])
    process_ticket(9902, client=client)
    d = evidence.build_evidence(9902)["decisions"][0]
    assert not d["ok"] and "more than 30 days" in d["why"]

def test_someone_elses_order_is_never_shown_to_the_reviewer(store):
    add_ticket(9903, "Where is order #9011?", ALICE)
    client = ScriptedClient(['{"intents": ["track"], "new_address": null}', {"tool_calls": [("track_shipment", {"order_id": 9011})]},
                             "I could not find order #9011 on your account. Support Team"])
    process_ticket(9903, client=client)
    ev = evidence.build_evidence(9903)
    assert ev["order_now"] == {"found": False, "order_id": 9011}
    assert "not found on this customer's account" in ev["decisions"][0]["title"]
    assert "Bob" not in json.dumps(ev) and "UPS" not in json.dumps(ev)

def test_evidence_of_an_unprocessed_ticket_is_none(store):
    add_ticket(9904, "hello", BOB)
    assert evidence.build_evidence(9904) is None
