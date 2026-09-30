"""
llm_test.py  --  Day 1
Check karta hai ke tumhari LLM key kaam karti hai aur model TOOL CALLING support karta hai
(agent ke liye tool calling zaroori hai).

Chalao:  python llm_test.py
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])
MODEL = os.environ["LLM_MODEL"]

print("--- Test 1: simple chat")
r = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
)
print(r.choices[0].message.content)

print("\n--- Test 2: tool calling")
tools = [{
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": "Look up an order by its order number",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
}]
r = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Where is my order #1042?"}],
    tools=tools,
)
msg = r.choices[0].message
if msg.tool_calls:
    call = msg.tool_calls[0]
    print("OK! Model ne tool call ki:", call.function.name, call.function.arguments)
else:
    print("Model ne tool call NAHI ki. Koi aur model try karo jo tool calling support karta ho.")
