"""Tests for intent.py -- uses a fake LLM client, no internet or key needed."""
import pytest
from app import intent
from tests.conftest import FakeClient


@pytest.mark.parametrize("text,ids", [
    ("Where is my order #1042?", [1042]),
    ("status of order 1080 please", [1080]),
    ("Order number 1043 is wrong", [1043]),
    ("refund $500 for order #1084", [1084]),
    ("see #1001 and order 1002, again #1001", [1001, 1002]),
    ("I paid $500 yesterday", []),
])
def test_extract_order_ids(text, ids):
    assert intent.extract_order_ids(text) == ids


def test_good_answer():
    c = FakeClient('{"intents": ["track"], "new_address": null}')
    r = intent.classify_intent("Where?", "Where is my order #1042?", client=c)
    assert r["ok"] and r["intents"] == ["track"] and r["order_id"] == 1042 and r["new_address"] is None

def test_answer_wrapped_in_code_fence():
    c = FakeClient('```json\n{"intents": ["refund"], "new_address": null}\n```')
    assert intent.classify_intent("x", "refund order #1043", client=c)["intents"] == ["refund"]

def test_two_intents_and_real_address():
    body = "Where is my order #1076? Also please change the delivery address to 422 Cedar Ln, Austin, TX."
    c = FakeClient('{"intents": ["track", "address_change"], "new_address": "422 Cedar Ln, Austin, TX"}')
    r = intent.classify_intent("Two", body, client=c)
    assert r["intents"] == ["track", "address_change"] and r["new_address"] == "422 Cedar Ln, Austin, TX"
    assert r["address_verified"] is True

def test_invented_address_is_dropped():
    # the LLM returned an address that was never in the ticket -> the code rejects it
    c = FakeClient('{"intents": ["address_change"], "new_address": "999 Fake Road, Nowhere"}')
    r = intent.classify_intent("x", "Please change my address for order #1044", client=c)
    assert r["new_address"] is None and r["address_verified"] is False

def test_weird_intents_are_filtered():
    c = FakeClient('{"intents": ["refund_everything", "refund"], "new_address": null}')
    assert intent.classify_intent("x", "refund order #1043", client=c)["intents"] == ["refund"]

def test_no_valid_intent_becomes_other():
    c = FakeClient('{"intents": ["hack"], "new_address": null}')
    assert intent.classify_intent("x", "hello order", client=c)["intents"] == ["other"]

def test_order_id_comes_from_text_not_from_llm():
    c = FakeClient('{"intents": ["refund"], "new_address": null, "order_id": 777}')
    assert intent.classify_intent("x", "refund order #1043", client=c)["order_id"] == 1043

def test_garbage_output_is_reported():
    r = intent.classify_intent("x", "refund order #1043", client=FakeClient("sorry I cannot help"))
    assert r["ok"] is False and r["error"] == "bad_llm_output"

def test_llm_failure_is_reported():
    r = intent.classify_intent("x", "refund order #1043", client=FakeClient(exc=TimeoutError("boom")))
    assert r["ok"] is False and r["error"].startswith("llm_call_failed")
    assert r["order_id"] == 1043   # the regex still works
