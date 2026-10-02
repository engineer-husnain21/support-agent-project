"""
promises.py -- finds replies that PROMISE a human follow-up ("I'll forward this to a specialist").

An automatic reply must never promise something the system will not do: if nobody is really handed the ticket,
the customer waits for a call that never comes. The agent is blocked from sending such a reply, and the
evaluation counts it as wrong. NO AI here, only regex.
"""
import re

_PATTERNS = [
    r"\b(?:i|we)(?:'ll| will| am going to|'m going to)\s+(?:forward|escalate|pass|hand|route|send)\b",
    r"\b(?:forward(?:ed|ing)?|escalat(?:e|ed|ing))\b[^.]{0,60}\b(?:specialist|team|colleague|human|agent|manager|department)\b",
    r"\b(?:specialist|colleague|team member|someone from)\b[^.]{0,40}\b(?:will|shall)\b[^.]{0,30}\b(?:contact|reach|get back|follow|review|assist|help)\b",
    r"\bget back to you\b",
    r"\bfollow up with you\b",
    r"\bcontact you (?:shortly|soon|directly|personally)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def promises_handoff(reply: str | None) -> list:
    """Returns the matching phrases (empty list = the reply makes no such promise)."""
    text = (reply or "").replace("\u2019", "'").replace("\u2018", "'")   # curly apostrophes -> normal ones
    found = []
    for pattern in _COMPILED:
        m = pattern.search(text)
        if m:
            found.append(m.group(0).strip())
    return found
