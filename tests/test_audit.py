from app import audit


def test_trail_is_in_order_and_keeps_details(store):
    audit.log(1, "ticket_received", {"subject": "Hi"})
    audit.log(1, "screen", {"action": "pass"})
    audit.log(2, "screen", {"action": "escalate"})
    trail = audit.get_trail(1)
    assert [t["step"] for t in trail] == ["ticket_received", "screen"]
    assert trail[1]["detail"] == {"action": "pass"}

def test_empty_trail(store):
    assert audit.get_trail(999) == []
