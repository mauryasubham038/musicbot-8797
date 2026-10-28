import os
from dotenv import load_dotenv

load_dotenv()


def _int(key, default=0):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


API_ID = _int("API_ID")
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").replace(" ", "").split(",") if x.lstrip("-").isdigit()]
LOG_CHAT_ID = _int("LOG_CHAT_ID")
DB_PATH = os.getenv("DB_PATH", "musicbot.db")
SESSION_DIR = os.getenv("SESSION_DIR", ".")  # persistent disk ho to /data
COOKIES_FILE = os.getenv("COOKIES_FILE", "")
if COOKIES_FILE and os.path.exists(COOKIES_FILE) and not os.access(COOKIES_FILE, os.W_OK):
    import shutil  # Render Secret File read-only hoti hai, yt-dlp ko writable copy chahiye
    shutil.copy(COOKIES_FILE, "/tmp/cookies.txt")
    COOKIES_FILE = "/tmp/cookies.txt"
QUERIES_DIR = "queries"
POOL_REFRESH_MINUTES = _int("POOL_REFRESH_MINUTES", 60)
QUERIES_PER_REFRESH = _int("QUERIES_PER_REFRESH", 12)
MAX_SONG_MINUTES = _int("MAX_SONG_MINUTES", 10)
