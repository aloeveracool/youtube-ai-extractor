import sys
import os
import time
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Fix pythonw.exe stdout/stderr NoneType issue on Windows
if sys.stdout is None:
    sys.stdout = open(BASE_DIR / "server.log", "a", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(BASE_DIR / "server.log", "a", encoding="utf-8")

import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8500")

if __name__ == "__main__":
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8500, log_level="warning")
