"""
list_models.py -- prints the model names your API key can use.

Run:  python list_models.py        (first LLM)
      python list_models.py 2      (second LLM from LLM2_* in .env)
"""
import os
import sys

from dotenv import load_dotenv
from app import llm

load_dotenv()
llm.use_profile(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
client = llm.get_client()
print("Provider:", os.environ["LLM_BASE_URL"])
for m in client.models.list():
    print(m.id)
