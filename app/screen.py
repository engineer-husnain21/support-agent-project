"""
screen.py -- the first, cheap filter. NO AI, only rules (regex). Every ticket passes through here BEFORE it reaches the agent.

Benefits: angry / legal / spam / injection tickets never trigger an LLM call (saves money and time),
and things like "ignore your rules" never reach the LLM at all.
"""
import re
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ScreenResult:
    action: str     # "pass" or "escalate"
    reason: str     # spam / prompt_injection / legal_threat / angry_customer / unclear_request / ok
    priority: str   # high / normal / low
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


SPAM = [r"click here", r"bit\.ly", r"https?://", r"free (iphone|gift|prize)", r"you(?:'ve| have)? won\b",
        r"congratulations", r"make \$\d+", r"seo services", r"no experience needed", r"\d+% discount"]

INJECTION = [r"ignore (all |any |your |the |previous |prior |above )+(rules|instructions|polic)",
             r"forget (all |any |your |the |previous |prior )+(rules|instructions)",
             r"disregard (all |any |your |the |previous |prior )+(rules|instructions|polic)",
             r"\bsystem\s*:", r"admin mode", r"developer mode", r"you are now",
             r"without (any )?(checks|verification|approval)", r"override (the )?(policy|rules|limit)", r"jailbreak"]

LEGAL = [r"\bsue\b", r"\bsuing\b", r"\blawsuit", r"\blawyer", r"\battorney", r"legal action", r"\bcourt\b",
         r"\bfraud\b", r"consumer protection"]

ANGRY = [r"unacceptable", r"furious", r"outraged", r"worst (service|company|experience)",
         r"terrible (company|service)", r"\bsick of\b", r"\bmanager\b", r"ridiculous", r"disgusting",
         r"\bscam\b", r"is a joke", r"fed up", r"(never|won't) (buy|order|shop)", r"done with you"]

# If none of these words appear, the ticket is 'unclear'
TOPIC_WORDS = ["order", "refund", "return", "track", "where", "package", "parcel", "address", "deliver",
               "ship", "status", "cancel", "money back", "charge", "payment", "arrive", "received"]


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def _shouting(raw: str) -> bool:
    """3+ exclamation marks, or at least 2 fully CAPITALISED words (4+ letters) = shouting."""
    caps = [w for w in re.findall(r"[A-Za-z']+", raw) if len(w) >= 4 and w.isupper()]
    return "!!!" in raw or len(caps) >= 2


def screen(subject: str, body: str, known_sender: bool) -> ScreenResult:
    raw = f"{subject or ''}\n{body or ''}"
    text = raw.lower()

    if not known_sender and _any(SPAM, text):
        return ScreenResult("escalate", "spam", "low", "Looks like spam from an unknown sender.")
    if _any(INJECTION, text):
        return ScreenResult("escalate", "prompt_injection", "high",
                            "Message tries to override the rules or give system instructions.")
    if _any(LEGAL, text):
        return ScreenResult("escalate", "legal_threat", "high", "Legal threat; needs a human immediately.")
    if _any(ANGRY, text) or _shouting(raw):
        return ScreenResult("escalate", "angry_customer", "high", "Customer is angry; needs a human.")

    word_count = len((body or "").split())
    if word_count <= 2 or not any(w in text for w in TOPIC_WORDS):
        return ScreenResult("escalate", "unclear_request", "normal", "Request is too unclear for the agent.")

    return ScreenResult("pass", "ok", "normal", "Passed screening.")
