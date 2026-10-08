import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_BIN = BASE_DIR / "bin" / "ffmpeg.exe"
FFMPEG_PATH = str(FFMPEG_BIN) if FFMPEG_BIN.exists() else "ffmpeg"
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

def get_gemini_api_key():
    return os.getenv("GEMINI_API_KEY", "").strip()

def save_gemini_api_key(key: str):
    os.environ["GEMINI_API_KEY"] = key
    lines = []
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if not l.startswith("GEMINI_API_KEY=")]
    lines.append(f"GEMINI_API_KEY={key}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
