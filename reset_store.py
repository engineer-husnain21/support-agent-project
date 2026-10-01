"""
reset_store.py -- gives you a clean demo store again.
It regenerates data/store.db, so all refunds, audit logs and ticket results are wiped.

Run:  python reset_store.py
"""
import runpy

runpy.run_path("make_mock_data.py", run_name="__main__")
print("Store reset. All refunds, audit logs and results are cleared.")
