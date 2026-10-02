"""
llm.py -- the single place that talks to the LLM provider (OpenAI-compatible API).
Both intent.py and agent.py go through chat(), so retries and options live in one spot.
"""
import os

# Running totals, so the evaluation can report tokens per ticket.
USAGE = {"calls": 0, "tokens": 0}

PROFILE_KEYS = ("API_KEY", "BASE_URL", "MODEL", "REASONING_EFFORT")


def use_profile(n: int) -> None:
    """Switch to a second provider: copies LLM<n>_* from .env into LLM_* (profile 1 = the normal LLM_* values)."""
    if n == 1:
        return
    for key in ("API_KEY", "BASE_URL", "MODEL"):
        value = os.environ.get(f"LLM{n}_{key}")
        if not value:
            raise SystemExit(f"LLM{n}_{key} is missing in .env (needed for --profile {n}).")
        os.environ[f"LLM_{key}"] = value
    effort = os.environ.get(f"LLM{n}_REASONING_EFFORT")
    if effort:
        os.environ["LLM_REASONING_EFFORT"] = effort
    else:
        os.environ.pop("LLM_REASONING_EFFORT", None)   # the 'low' setting was meant for the first model


def get_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])


def chat(client, messages, tools=None):
    """One chat-completion call. Returns the raw response object."""
    kwargs = dict(model=os.environ.get("LLM_MODEL", "test-model"), messages=messages, temperature=0)
    if tools:
        kwargs["tools"] = tools
    effort = os.environ.get("LLM_REASONING_EFFORT")
    resp = None
    if effort:
        try:
            resp = client.chat.completions.create(**kwargs, extra_body={"reasoning_effort": effort})
        except Exception:
            resp = None   # this model rejected the option: retry without it
    if resp is None:
        resp = client.chat.completions.create(**kwargs)
    usage = getattr(resp, "usage", None)
    USAGE["calls"] += 1
    USAGE["tokens"] += int(getattr(usage, "total_tokens", 0) or 0)
    return resp
