"""
run_server.py -- starts the helpdesk web app.

Run:  python run_server.py
Then open  http://127.0.0.1:8000  in your browser.   Stop with Ctrl+C.
"""
import uvicorn

if __name__ == "__main__":
    print("Helpdesk UI: http://127.0.0.1:8000   (Ctrl+C to stop)")
    uvicorn.run("app.api:app", host="127.0.0.1", port=8000, log_level="warning")
