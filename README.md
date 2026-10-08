# POC-13: Support Ticket Resolution Agent

An agent that reads customer-support tickets (order tracking, refunds, address changes), uses the store's tools, checks every rule in code, and hands risky or unclear tickets to a human.

**Main idea: the AI reads and writes, code decides about money.**

Refunds and emails are **simulated** and labelled as such. Everything runs on free resources ($0): the free Groq LLM tier, SQLite, FastAPI and a plain HTML front end.

## How a ticket flows

```
Ticket -> Screen -> Intent -> Find the order -> Agent + tools -> Policy check -> Grounding check -> Reply
              |                                       |                |
              +--------------- Human queue <----------+----------------+        every step -> audit log -> dashboard
```

| Step | Uses an LLM? | What it does |
|---|---|---|
| Screen (`app/screen.py`) | No | Stops angry, legal, spam, prompt-injection and unclear tickets before any AI sees them. |
| Intent (`app/intent.py`) | Yes | Classifies the request. The order number is found with a regex, and an address is accepted only if it really appears in the ticket. |
| Agent (`app/agent.py`) | Yes | Calls the store tools and writes the reply. It cannot choose the customer's email or a refund amount. |
| Policy (`app/policy.py`, `app/actions.py`) | No | Refund up to $50 within 30 days of delivery; address change only before shipping. Every action checks the policy again inside itself. |
| Grounding (`app/grounding.py`) | No | Every order number, amount, date and tracking number in a reply must appear in a tool result, otherwise the reply is blocked. |
| Promise guard (`app/promises.py`) | No | A reply must not promise a human follow-up that will not happen. |
| Human queue (`app/human_queue.py`) | No | Approve or reject. Approval can lift the $50 limit only; the 30-day rule and "already refunded" still apply. |

> Which free resources are used, where to get them and how to set them up: see **`resource-setup-guide.md`**.

## Setup (Windows PowerShell)

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then put your LLM key, base URL and model name into .env
python make_mock_data.py        # creates data/store.db: 60 customers, 130 orders, 150 tickets
python llm_test.py              # checks the key and that the model supports tool calling
python -m pytest                # runs all tests (no internet or key needed)
```

## Run the web app

```
python run_server.py            # then open http://127.0.0.1:8000
```

Inbox with a three-column helpdesk view, a human queue (Approve / Edit / Reject), and a dashboard with live numbers from the database.

**Review AI** tab (self-validation): for every ticket the AI resolved, a reviewer sees what the customer wrote, what the AI replied,
whether every order number, amount and date in the reply was really returned by the system, what the AI did and why the rules allowed it,
and the data as it is now. The reviewer marks the ticket Correct, Incorrect (with a reason) or Not sure (keys 1, 2, 3; J and K move between tickets).
The Dashboard shows how many AI-resolved tickets were reviewed and how often the reviewer agrees.

## Honest evaluation

The definition of "resolved" was written **before** any run: see `METRICS.md`.

```
python run_eval.py --run 1      # 40 labelled tickets, real LLM; repeat for runs 2 and 3
python report.py                # builds reports/REPORT.md and reports/summary.json
```

- The 40 tickets were drawn at random with a fixed seed (`make_eval_set.py`, `data/eval_set.json`) and never changed afterwards.
- Every number in the report is calculated by `report.py`; none is typed by hand.
- Run 1 found three real problems (see `METRICS.md`, section 9). They were fixed and all three runs were repeated. The first run is kept in `reports/archive/`.
- Read the limitations in `reports/REPORT.md` before quoting any percentage.

## Demo

```
python reset_store.py           # a clean store
python demo_cases.py            # creates the tickets for the 14 test cases of the brief (ids 201 to 216)
python run_server.py
```

`DEMO_PLAN.md` has the order of the cases, what to say, and the special setups (tool failure, simulated LLM mistake).

## Project layout

```
app/            the agent, rules, tools, API, evaluation code
web/            the helpdesk front end (HTML, CSS, JavaScript)
tests/          automated tests (a fake LLM is used, so they run offline)
data/           eval_set.json and refund_policy.md (the databases are created by scripts)
reports/        evaluation runs, the report, and the archived first run
METRICS.md      what "resolved" means, written before the runs
DEMO_PLAN.md    the presentation plan
resource-setup-guide.md   the free resources used and how to set them up
```

## Known limits

- The mock tickets come from templates, and the screen rules were written while looking at them.
- 40 tickets is a small test set, and the agent was improved after run 1 using this same set, so the final numbers are optimistic.
- Reply checks are keyword checks; tone and writing quality are not scored.
- Free LLM tiers have daily token limits: one 40-ticket run uses about 60,000 tokens.

## Review AI without an API key

`data/sample_review_store.db` is a store in which 40 tickets were already processed by the real LLM (the held-out evaluation run). It lets you try the **Review AI** tab without any key:

```
$env:STORE_DB="data\sample_review_store.db"     (Windows PowerShell; macOS/Linux: export STORE_DB=data/sample_review_store.db)
python run_server.py                             # open http://127.0.0.1:8000 and click "Review AI"
Remove-Item Env:STORE_DB                         # afterwards: go back to the normal store
```

The reviews you save are written into that file.
