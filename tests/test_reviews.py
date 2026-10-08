"""Tests for reviews.py -- a human validates the tickets the AI resolved."""
import pytest
from app import reviews, results, stats
from tests.conftest import add_ticket, BOB


def resolved(tid, reply="Your order #9011 was delivered.", status="auto_resolved"):
    add_ticket(tid, "Where is my order #9011?", BOB)
    results.save_result(tid, status, status if status != "waiting_for_human" else "escalated", "handled_by_agent", reply=reply, reply_sent=True)


def test_save_and_read_a_review(store):
    resolved(9801)
    rv = reviews.save_review(9801, "correct", note="  looks fine ", reviewer="zubair")
    assert (rv["verdict"], rv["note"], rv["reviewer"], rv["stale"]) == ("correct", "looks fine", "zubair", False)

def test_incorrect_needs_a_known_reason(store):
    resolved(9802)
    with pytest.raises(ValueError):
        reviews.save_review(9802, "incorrect")
    with pytest.raises(ValueError):
        reviews.save_review(9802, "incorrect", reason="made_up")
    assert reviews.save_review(9802, "incorrect", reason="wrong_action")["reason_text"] == "Wrong action (refund or address)"

def test_a_reason_is_dropped_when_the_verdict_is_not_incorrect(store):
    resolved(9803)
    assert reviews.save_review(9803, "correct", reason="wrong_fact")["reason"] is None

def test_unknown_verdict_and_non_ai_tickets_are_refused(store):
    resolved(9804)
    with pytest.raises(ValueError):
        reviews.save_review(9804, "great")
    resolved(9805, status="waiting_for_human")
    with pytest.raises(ValueError):
        reviews.save_review(9805, "correct")
    with pytest.raises(ValueError):
        reviews.save_review(123456, "correct")

def test_a_review_is_outdated_when_the_reply_changes(store):
    resolved(9806)
    reviews.save_review(9806, "correct")
    results.save_result(9806, "auto_resolved", "auto_resolved", "handled_by_agent", reply="A different reply.", reply_sent=True)
    assert reviews.get_review(9806)["stale"] is True
    assert reviews.all_states()[9806]["stale"] is True
    assert reviews.review_stats()["reviewed"] == 0                       # an outdated review does not count

def test_stats_and_agreement(store):
    for tid in (9811, 9812, 9813, 9814):
        resolved(tid)
    reviews.save_review(9811, "correct"); reviews.save_review(9812, "correct")
    reviews.save_review(9813, "incorrect", reason="wrong_fact"); reviews.save_review(9814, "unsure")
    s = reviews.review_stats()
    assert (s["ai_resolved"], s["reviewed"], s["unreviewed"]) == (4, 4, 0)
    assert (s["correct"], s["incorrect"], s["unsure"]) == (2, 1, 1)
    assert s["agreement_pct"] == 66.7                                     # 2 correct of 3 that were decided
    assert s["reasons"] == [{"reason": "wrong_fact", "text": "Wrong fact in the reply", "count": 1}]
    assert stats.compute_stats()["review"]["correct"] == 2                # the dashboard gets the same numbers

def test_delete(store):
    resolved(9815)
    reviews.save_review(9815, "correct")
    assert reviews.delete_review(9815) is True and reviews.get_review(9815) is None and reviews.delete_review(9815) is False

def test_no_ai_resolved_tickets_means_zero_percent(store):
    assert reviews.review_stats()["agreement_pct"] == 0.0
