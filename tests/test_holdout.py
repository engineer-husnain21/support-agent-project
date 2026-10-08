"""Tests for the held-out set: it must be a fair, separate test."""
import json
import os

from app import evalsets

ROOT = os.path.join(os.path.dirname(__file__), "..")


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)["tickets"]


def test_holdout_set_shares_no_ticket_with_the_first_set():
    first, hold = load("eval_set.json"), load("holdout_set.json")
    assert len(hold) == 40
    assert not {t["ticket_id"] for t in first} & {t["ticket_id"] for t in hold}


def test_holdout_set_has_the_same_mix_of_categories():
    first, hold = load("eval_set.json"), load("holdout_set.json")
    count = lambda ts: sorted((t["category"], sum(1 for x in ts if x["category"] == t["category"])) for t in ts)
    assert {c for c, _ in count(first)} == {c for c, _ in count(hold)}
    assert [n for _, n in count(first)] == [n for _, n in count(hold)]


def test_tickets_that_reach_the_agent_never_share_an_order_or_customer(pristine_db, monkeypatch):
    monkeypatch.setenv("STORE_DB", str(pristine_db))
    import sqlite3
    con = sqlite3.connect(pristine_db)
    emails = {r[0]: r[1] for r in con.execute("SELECT ticket_id, customer_email FROM tickets")}
    con.close()
    hold = [t for t in load("holdout_set.json") if t["category"] not in evalsets.SCREENED]
    orders = [t["order_id"] for t in hold if t["order_id"] is not None]
    assert len(orders) == len(set(orders))
    mails = [emails[t["ticket_id"]] for t in hold]
    assert len(mails) == len(set(mails))


def test_the_draw_is_repeatable_and_respects_the_exclusion(pristine_db, monkeypatch):
    monkeypatch.setenv("STORE_DB", str(pristine_db))
    first = {t["ticket_id"] for t in load("eval_set.json")}
    a = evalsets.build_set(2027, exclude_ids=first)
    b = evalsets.build_set(2027, exclude_ids=first)
    assert a == b and len(a) == 40 and not {t["ticket_id"] for t in a} & first
    assert a == load("holdout_set.json")                  # the committed file is exactly what the script draws
