"""Tests for promises.py -- an automatic reply must not promise a human follow-up that will not happen."""
import pytest
from app.promises import promises_handoff


@pytest.mark.parametrize("reply", [
    "I\u2019m sorry, but I can\u2019t locate order #1007 in our system. I\u2019ll forward this to a specialist who can help you further.",
    "We will forward your request to our support team.",
    "I'll escalate this to a manager.",
    "A specialist will contact you tomorrow.",
    "Someone from our team will get back to you shortly.",
    "We will get back to you as soon as possible.",
])
def test_promises_are_found(reply):
    assert promises_handoff(reply)


@pytest.mark.parametrize("reply", [
    "Your refund of $24.99 for order #1043 was issued. It will reach your payment method in 5-7 business days.\n\nSupport Team",
    "Your package was delivered on 2026-09-29 by USPS. Tracking number TRK123.",
    "Order #1042 has shipped, so the address can no longer be changed. You can contact the carrier to redirect the parcel.",
    "I could not find order #1007 on your account. Please check the number and try again.",
    "Sorry, order #1013 is past the 30-day refund window.",
])
def test_normal_replies_are_fine(reply):
    assert promises_handoff(reply) == []


def test_empty_reply():
    assert promises_handoff(None) == [] and promises_handoff("") == []
