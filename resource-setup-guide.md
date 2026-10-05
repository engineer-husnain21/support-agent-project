# Resource setup guide (POC-13: Support Ticket Resolution Agent)

This guide lists every external resource the project uses, where it comes from, how it was configured, and the steps for someone else to rebuild the same environment from zero. **Everything used is free. No API keys or credentials are included in this ZIP.** You create your own free key (section 3).

## 1. Resources used

| Resource | What it is used for | Cost | Where it comes from |
|---|---|---|---|
| **Groq free tier** (OpenAI-compatible API) | Runs the LLM that classifies the ticket and writes the reply | $0 (free tier, rate limits apply) | https://console.groq.com |
| **LLM model `openai/gpt-oss-120b`** | The model behind the agent (supports tool calling). It is an open-weight model that Groq hosts under this id | $0 on the free tier | Served by Groq; no download needed |
| **Python 3.12.7** (3.10 or newer is required) | Runs everything | $0 | https://www.python.org/downloads/ (on Windows it was installed with pyenv-win) |
| **SQLite** | The store database (customers, orders, shipments, tickets, audit log) | $0 | Built into Python, nothing to install |
| **Python packages** | `openai` (API client), `python-dotenv`, `fastapi`, `uvicorn` (web server), `pytest` (tests) | $0 | PyPI, via `pip install -r requirements.txt` |
| **Mock store data** | 60 customers, 130 orders, 100 shipments, 150 tickets and a written refund policy | $0 | Generated locally by `make_mock_data.py` (no download) |
| **Web UI** | The helpdesk screens | $0 | Plain HTML, CSS and JavaScript in `web/`. No Node.js, no external libraries, no CDN |
| **Git and GitHub** | Version control (optional for running the project) | $0 | https://git-scm.com and https://github.com |

Not used: no paid helpdesk, email, payment or hosting service, no embeddings, no vector database, no other AI service. The screen, the policy rules, the fact check and the evaluation scoring are plain Python code.

Versions seen when the project was built: openai 3.22.1, python-dotenv 1.2.3, pytest 9.1.1, fastapi 0.142.2, starlette 1.7.0, uvicorn 0.54.0.

Development tools (not part of the running system): an AI chat assistant (Claude) was used to help write the code and the tests; the code was then run and checked by the author.

## 2. What is simulated

Refunds and emails are **simulated**: a refund only marks the order as refunded in the local database, and a reply is only saved (it is never emailed). The UI labels this ("Simulated mode", "SIMULATED SEND"). Everything else (LLM calls, policy rules, fact check, human queue, audit log) is real.

## 3. Get and configure the free LLM key (Groq)

1. Open https://console.groq.com and sign up (email, Google or GitHub). No payment method was needed for the free tier when this project was built.
2. Open **API Keys** and press **Create API Key**. Give it a name (for example `support-agent`) and choose an expiry (30 days was used). Copy the key right away; it is shown only once.
3. In the project folder, copy the template and fill in your values:

   ```
   copy .env.example .env          (Windows PowerShell)
   cp .env.example .env            (macOS / Linux)
   ```

   Edit `.env` so that it contains:

   ```
   LLM_API_KEY=your_groq_key
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=openai/gpt-oss-120b
   LLM_REASONING_EFFORT=low
   ```

   - `LLM_REASONING_EFFORT=low` makes this reasoning model think less, which saves free tokens. If the provider rejects it, remove the line.
   - Model names change over time. Run `python list_models.py` after step 5 below and copy a chat model that supports tool calling (the agent needs tool calling).
4. Never commit `.env`. It is listed in `.gitignore`, and `.env.example` contains only placeholders.

## 4. Install and run the project

All commands are for Windows PowerShell; on macOS/Linux use `python3`, and `source .venv/bin/activate` instead of the activate line.

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python make_mock_data.py          # creates data/store.db
python -m pytest                  # all tests pass; no internet or key needed (a fake LLM is used)
python list_models.py             # confirms that your key works and shows the model names
python llm_test.py                # checks chat AND tool calling with your key
python run_server.py              # then open http://127.0.0.1:8000
```

In the web app: open the **Inbox**, choose a ticket and press **Process with agent**. The **Human queue** tab has Approve / Edit / Reject, and the **Dashboard** tab shows the live numbers.

## 5. Reproduce the demo and the evaluation

```
python reset_store.py             # a clean store (wipes refunds, results and the audit log)
python demo_cases.py              # tickets 201 to 216: the 14 client-ready test cases of the brief
python demo_grounding.py          # case 14: a simulated LLM mistake blocked by the grounding check
```

Case 13 (a tool fails): stop the server, run `$env:FAIL_TOOL="track_shipment"` in the same terminal, start the server again, and process ticket 213. Remove the switch afterwards with `Remove-Item Env:FAIL_TOOL`.

Evaluation on the 40 labelled tickets (definitions are in `METRICS.md`):

```
python run_eval.py --run 1        # repeat with --run 2 and --run 3
python report.py                  # writes reports/REPORT.md and reports/summary.json
```

## 6. Free-tier limits and what to expect

- Free tiers have rate limits and a daily token limit. Limits change, so read them on the Limits page of your Groq console.
- One 40-ticket evaluation run used roughly 57,000 to 59,000 tokens in our runs, and a single ticket that reaches the LLM uses about 1,700 to 3,700 tokens. Tickets stopped by the screen use none.
- If the provider hits its limit during `run_eval.py`, the run stops by itself and keeps the finished tickets. Continue later with `python run_eval.py --run N --resume`.

## 7. Using another free provider instead of Groq

The code talks to any OpenAI-compatible endpoint, so only `.env` changes. The model must support **tool calling**.

| Provider | `LLM_BASE_URL` | Key from |
|---|---|---|
| Google AI Studio (Gemini) | `https://generativelanguage.googleapis.com/v1beta/openai/` | https://aistudio.google.com |
| OpenRouter (free models) | `https://openrouter.ai/api/v1` | https://openrouter.ai |
| Ollama (runs locally, no key) | `http://localhost:11434/v1` | https://ollama.com (key can be any text) |

Put the second provider in `.env` as `LLM2_API_KEY`, `LLM2_BASE_URL` and `LLM2_MODEL`, and use `--profile 2` with `llm_test.py`, `list_models.py` and `run_eval.py`. These alternatives were not used for the reported evaluation: all three official runs used Groq with `openai/gpt-oss-120b`.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `model_not_found` (404) | The model name changed. Run `python list_models.py` and copy a current chat model into `LLM_MODEL`. |
| `llm_test.py` says the model did not make a tool call | Choose another model that supports tool calling. |
| `401` or invalid key | Re-copy the key into `.env` with no quotes and no spaces, and save the file. |
| `429` or rate-limit messages | The free limit is used up. Wait for the reset, or use another provider (section 7). |
| PowerShell: "running scripts is disabled" | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate the environment again. |
| `python` shows an old version (pyenv) | Install Python 3.12 and run `pyenv local 3.12.7` in the project folder. |
| The UI shows old results | Stop the server, run `python reset_store.py` and `python demo_cases.py`, start the server and refresh the browser. |
