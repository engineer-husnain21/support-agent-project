"""
run_eval.py -- runs the 40-ticket labelled test set ONCE with the real LLM and saves reports/run_<N>.json.

Do the three official runs like this:
    python run_eval.py --run 1
    python run_eval.py --run 2 --profile 2     (second provider, if the first one hit its daily limit)
    python run_eval.py --run 3 --profile 2
Then:  python report.py

Useful options:
    --limit 3      quick check of the setup on the first 3 tickets (saved as dryrun_N.json, ignored by the report)
    --resume       continue an interrupted run instead of starting it again
"""
import argparse

from dotenv import load_dotenv

from app import llm
from app.evalrun import run_eval

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run the labelled evaluation set once.")
    ap.add_argument("--run", type=int, required=True, help="run number (1, 2, 3)")
    ap.add_argument("--profile", type=int, default=1, help="1 = LLM_* in .env, 2 = LLM2_* in .env")
    ap.add_argument("--limit", type=int, default=None, help="only the first N tickets (dry run)")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run")
    args = ap.parse_args()

    load_dotenv()
    llm.use_profile(args.profile)
    run_eval(args.run, profile=args.profile, limit=args.limit, resume=args.resume)
