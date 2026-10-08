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

COOKIES_PATH = BASE_DIR / "cookies.txt"

# If YOUTUBE_COOKIES is provided via env var (e.g. Render dashboard), auto-write to cookies.txt
_env_cookies = os.getenv("YOUTUBE_COOKIES", "").strip()
if _env_cookies and not COOKIES_PATH.exists():
    try:
        with open(COOKIES_PATH, "w", encoding="utf-8") as _f:
            _f.write(_env_cookies)
    except Exception:
        pass

def has_youtube_cookies() -> bool:
    return COOKIES_PATH.exists() and COOKIES_PATH.stat().st_size > 10

def save_youtube_cookies(content: str):
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        f.write(content.strip())

def delete_youtube_cookies():
    if COOKIES_PATH.exists():
        try:
            os.remove(COOKIES_PATH)
        except Exception:
            pass

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

