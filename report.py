"""
report.py -- builds the client report from the saved evaluation runs.

Reads reports/run_*.json (complete runs only) and writes
    reports/REPORT.md       the report (every number is calculated here, none is typed by hand)
    reports/summary.json    the same numbers for the slides

Run:  python report.py
"""
import glob
import json
import os

from app.evaluation import render_report, run_metrics

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(ROOT, "reports")

runs = []
for path in sorted(glob.glob(os.path.join(REPORTS, "run_*.json"))):
    with open(path, encoding="utf-8") as f:
        run = json.load(f)
    if not run["meta"].get("complete"):
        print(f"Skipping {os.path.basename(path)}: not complete ({len(run['tickets'])} tickets). Finish it with --resume.")
        continue
    runs.append(run)

if not runs:
    raise SystemExit("No complete run found in reports/. Run `python run_eval.py --run 1` first.")

text, summary = render_report(runs)
with open(os.path.join(REPORTS, "REPORT.md"), "w", encoding="utf-8") as f:
    f.write(text)
with open(os.path.join(REPORTS, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=1)

print(f"Report written from {len(runs)} run(s): reports/REPORT.md and reports/summary.json\n")
for t in summary["targets"]:
    print(f"  {'MET    ' if t['met'] else 'NOT MET'}  {t['target']:<52} per run: {', '.join(t['per_run'])}")
print()
for m, r in zip(summary["per_run"], runs):
    print(f"  Run {r['meta']['run']}: correct {m['correct']}, safe miss {m['safe_miss']}, wrong {m['wrong']} "
          f"| auto-resolved correctly {m['auto_correct']} of {m['tickets']} ({m['auto_correct_pct']}%)")
print(f"\n  Tickets that were not scored correct in some run: {len(summary['failed_tickets'])} (listed in the report)")
