"""
fake_llm.py -- a rule-based stand-in for the LLM, used ONLY in tests.

It behaves like a sensible agent (classifies by keywords, calls the right tools, writes a reply from the tool results),
so the evaluation pipeline can be tested end to end without internet, keys or tokens.
Its results are never used in the real report.
"""
import json
import re
from types import SimpleNamespace


def _msg(content=None, calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=calls or None))],
                           usage=SimpleNamespace(total_tokens=100))


def _call(i, name, args):
    return SimpleNamespace(id=f"fake_{i}", type="function", function=SimpleNamespace(name=name, arguments=json.dumps(args)))


class SmartFakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.n = 0

    def _create(self, **kw):
        self.n += 1
        messages, tools = kw["messages"], kw.get("tools")
        return self._agent(messages) if tools else self._intent(messages)

    # --- intent classification
    def _intent(self, messages):
        text = messages[-1]["content"]
        low = text.lower()
        intents = []
        if re.search(r"track|where is|status|package|haven't got|hasn't arrived", low):
            intents.append("track")
        if re.search(r"refund|money back|return", low):
            intents.append("refund")
        if "address" in low or re.search(r"\bship order\b", low):
            intents.append("address_change")
        addr = None
        m = re.search(r"(?:address (?:for order #?\d+ )?to|ship order \d+ to|to) (\d+ [^?\n]+?)(?: instead)?[?.]?\s*$", text.strip(), re.I)
        if m:
            addr = m.group(1)
        return _msg(json.dumps({"intents": intents or ["other"], "new_address": addr}))

    # --- agent
    def _agent(self, messages):
        user = messages[1]["content"]
        order_id = int(re.search(r"Resolved order number: #(\d+)", user).group(1))
        intents = re.search(r"Detected request types: (.*)", user).group(1).split(", ")
        ticket_text = user.split("\n---\n")[0]
        tool_msgs = [m for m in messages if m["role"] == "tool"]
        if not tool_msgs:
            calls = []
            if "track" in intents:
                calls.append(_call(1, "track_shipment", {"order_id": order_id}))
            if "refund" in intents:
                calls.append(_call(2, "issue_refund", {"order_id": order_id}))
            if "address_change" in intents:
                m = re.search(r"\bto (\d+ [^?\n]+?)(?: instead)?[?.]?\s*$", ticket_text.strip())
                calls.append(_call(3, "update_address", {"order_id": order_id, "new_address": m.group(1) if m else "unknown"}))
            if not calls:
                calls.append(_call(4, "escalate_to_human", {"reason": "cannot classify"}))
            return _msg(None, calls)
        parts = []
        for tm in tool_msgs:
            r = json.loads(tm["content"])
            if r.get("found") is False:
                parts.append(f"I could not find order #{order_id} on your account.")
            elif "shipped" in r:
                parts.append(f"Order #{order_id} is {r['status'].replace('_', ' ')} with {r.get('carrier')}, expected {r.get('expected_date')}."
                             if r["shipped"] else f"Order #{order_id} has not shipped yet.")
            elif "executed" in r:
                parts.append(r["message"] if r["executed"] else f"Sorry, that is not possible: {r['message']}")
                if r.get("old_address") and r["executed"]:
                    parts[-1] = f"The delivery address for order #{order_id} was updated."
        return _msg("Hi, " + " ".join(parts) + "\n\nSupport Team")


class SloppyFakeClient(SmartFakeClient):
    """A deliberately bad agent: it SAYS the refund was processed but never calls the refund tool.
    Used to prove that the evaluation catches 'the reply claims something that did not happen'."""

    def _agent(self, messages):
        user = messages[1]["content"]
        if "refund" in re.search(r"Detected request types: (.*)", user).group(1) and not [m for m in messages if m["role"] == "tool"]:
            return _msg("Hi, your refund has been processed. Support Team")
        return super()._agent(messages)
