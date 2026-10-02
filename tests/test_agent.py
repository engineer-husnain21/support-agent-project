"""Tests for agent.py -- uses a scripted fake LLM, so no internet or key is needed."""
import json
import pytest
from app import agent, db, tickets
from tests.conftest import ALICE, BOB, ScriptedClient, add_ticket


def run(ticket_id, script, order_id, intents, monkeypatch=None):
    client = ScriptedClient(script)
    return agent.run_agent(tickets.get_ticket(ticket_id), order_id, intents, client=client), client


def address_of(oid):
    con = db.get_conn()
    try:
        return con.execute("SELECT shipping_address FROM orders WHERE order_id=?", (oid,)).fetchone()["shipping_address"]
    finally:
        con.close()


def test_tool_schemas_never_expose_email_or_amount():
    # the LLM must not be able to choose WHOSE order to read or HOW MUCH to refund
    for t in agent.TOOL_SCHEMAS:
        props = t["function"]["parameters"]["properties"]
        assert not ({"email", "customer_email", "amount", "approved_by_human"} & set(props)), t["function"]["name"]

def test_auto_refund_then_reply(store):
    add_ticket(9301, "Refund order #9001 please", ALICE)
    r, _ = run(9301, [{"tool_calls": [("issue_refund", {"order_id": 9001})]},
                      "Hi Alice, your refund of $24.99 for order #9001 was issued. Support Team"], 9001, ["refund"])
    assert r.final_reply.startswith("Hi Alice") and r.ungrounded == []
    assert r.tool_log[0]["result"]["executed"] is True

def test_large_refund_stops_and_waits_for_human(store):
    add_ticket(9302, "Refund order #9002 please", ALICE)
    r, client = run(9302, [{"tool_calls": [("issue_refund", {"order_id": 9002})]}], 9002, ["refund"])
    assert r.pending_refund == {"type": "refund", "order_id": 9002, "amount": 119.99, "item": "Test Item"}
    assert r.final_reply is None and client.calls == 1

def test_agent_cannot_read_someone_elses_order(store):
    add_ticket(9303, "Where is order #9011?", ALICE)
    r, _ = run(9303, [{"tool_calls": [("lookup_order", {"order_id": 9011})]}, "Sorry, I could not find that order."],
               9011, ["track"])
    assert r.tool_log[0]["result"] == {"found": False, "reason": "order_not_found_on_account"}

def test_invented_address_is_rejected(store):
    add_ticket(9304, "Please change my address for order #9008 to 55 New Street, Seattle, WA", ALICE)
    before = address_of(9008)
    r, _ = run(9304, [{"tool_calls": [("update_address", {"order_id": 9008, "new_address": "999 Fake Road, Nowhere"})]},
                      "Sorry, I could not change the address."], 9008, ["address_change"])
    assert r.tool_log[0]["result"]["reason"] == "address_not_in_ticket"
    assert address_of(9008) == before

def test_real_address_is_applied(store):
    add_ticket(9305, "Please change my address for order #9008 to 55 New Street, Seattle, WA", ALICE)
    r, _ = run(9305, [{"tool_calls": [("update_address", {"order_id": 9008, "new_address": "55 New Street, Seattle, WA"})]},
                      "Done, the address for order #9008 was updated. Support Team"], 9008, ["address_change"])
    assert r.tool_log[0]["result"]["executed"] is True
    assert address_of(9008) == "55 New Street, Seattle, WA"

def test_ungrounded_reply_is_retried_and_can_recover(store):
    add_ticket(9306, "Where is my order #9011?", BOB)
    r, client = run(9306, [{"tool_calls": [("track_shipment", {"order_id": 9011})]},
                           "Your order #9011 arrived on 2026-01-01.",
                           "Your order #9011 was delivered. Support Team"], 9011, ["track"])
    assert r.ungrounded == [] and "delivered" in r.final_reply
    assert "not in the tool results" in client.requests[-1]["messages"][-1]["content"]

def test_ungrounded_reply_twice_is_flagged(store):
    add_ticket(9307, "Where is my order #9011?", BOB)
    r, _ = run(9307, [{"tool_calls": [("track_shipment", {"order_id": 9011})]},
                      "Arrived on 2026-01-01.", "It arrived on 2026-01-02."], 9011, ["track"])
    assert r.ungrounded

def test_escalate_tool(store):
    add_ticket(9308, "Where is my order #9011?", BOB)
    r, _ = run(9308, [{"tool_calls": [("escalate_to_human", {"reason": "customer wants a custom gift wrap"})]}],
               9011, ["track"])
    assert r.escalate_reason == "customer wants a custom gift wrap"

def test_tool_failure_stops_the_run(store, monkeypatch):
    monkeypatch.setenv("FAIL_TOOL", "track_shipment")
    add_ticket(9309, "Where is my order #9011?", BOB)
    r, _ = run(9309, [{"tool_calls": [("track_shipment", {"order_id": 9011})]}, "never reached"], 9011, ["track"])
    assert r.tool_failed and r.final_reply is None

def test_step_limit(store):
    add_ticket(9310, "Where is my order #9001?", ALICE)
    script = [{"tool_calls": [("lookup_order", {"order_id": 9001 + i})]} for i in range(agent.MAX_STEPS + 2)]
    r, client = run(9310, script, 9001, ["track"])
    assert r.step_limit_hit and client.calls == agent.MAX_STEPS

def test_bad_tool_arguments_do_not_crash(store):
    add_ticket(9311, "Where is my order?", BOB)
    r, _ = run(9311, [{"tool_calls": [("lookup_order", {"order_id": "abc"})]}, "Sorry, I need the order number."], 9011, ["track"])
    assert r.tool_log[0]["result"]["error"] == "invalid_arguments"

def test_same_tool_call_is_cached(store):
    add_ticket(9312, "Where is my order #9011?", BOB)
    r, _ = run(9312, [{"tool_calls": [("track_shipment", {"order_id": 9011}), ("track_shipment", {"order_id": 9011})]},
                      "Your order #9011 was delivered. Support Team"], 9011, ["track"])
    assert len(r.tool_log) == 2 and r.tool_log[0]["result"] == r.tool_log[1]["result"]


def test_reply_that_promises_a_human_is_rewritten_once(store):
    add_ticket(9313, "Where is order #9011?", ALICE)
    r, client = run(9313, [{"tool_calls": [("lookup_order", {"order_id": 9011})]},
                           "I can't find order #9011. I'll forward this to a specialist.",
                           "I could not find order #9011 on your account. Please check the number. Support Team"], 9011, ["track"])
    assert r.promised_handoff is False and "forward" not in r.final_reply
    assert "promises that the request will be forwarded" in client.requests[-1]["messages"][-1]["content"]

def test_reply_that_keeps_promising_is_flagged(store):
    add_ticket(9314, "Where is order #9011?", ALICE)
    r, _ = run(9314, [{"tool_calls": [("lookup_order", {"order_id": 9011})]},
                      "A specialist will contact you.", "We will forward this to our team."], 9011, ["track"])
    assert r.promised_handoff is True

def test_reply_may_name_the_order_that_our_code_resolved(store):
    # the customer gave no order number; our code found order 9003, so naming it is not a made-up fact
    add_ticket(9315, "I want a refund, I ordered something a while ago.", ALICE)
    r, _ = run(9315, [{"tool_calls": [("issue_refund", {"order_id": 9003})]},
                      "Sorry, order #9003 is past the 30-day refund window. Support Team"], 9003, ["refund"])
    assert r.ungrounded == [] and "9003" in r.final_reply

def test_prompt_contains_the_new_rules():
    p = agent.SYSTEM_PROMPT.lower()
    assert "name the order" in p and "never promise" in p and "not found on this account" in p
