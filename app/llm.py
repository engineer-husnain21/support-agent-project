"""
llm.py -- the single place that talks to the LLM provider (OpenAI-compatible API).
Both intent.py and agent.py go through chat(), so retries and options live in one spot.
"""
import os


def get_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])


def chat(client, messages, tools=None):
    """One chat-completion call. Returns the raw response object."""
    kwargs = dict(model=os.environ.get("LLM_MODEL", "test-model"), messages=messages, temperature=0)
    if tools:
        kwargs["tools"] = tools
    effort = os.environ.get("LLM_REASONING_EFFORT")
    if effort:
        try:
            return client.chat.completions.create(**kwargs, extra_body={"reasoning_effort": effort})
        except Exception:
            pass   # this model rejected the option: retry without it
    return client.chat.completions.create(**kwargs)
