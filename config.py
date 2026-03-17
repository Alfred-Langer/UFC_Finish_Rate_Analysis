import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
DATABASE_URL: str|None = os.getenv("DATABASE_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")



BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "html_data"
EVENT_HTML_DIR = DATA_DIR / "events"
FIGHTER_HTML_DIR = DATA_DIR / "fighters"

EVENT_NAMES_FILE = EVENT_HTML_DIR / "ufc_event_names.txt"
FAILED_EVENT_NAMES_FILE = EVENT_HTML_DIR / "ufc_failed_event_names.txt"
FIGHTER_URLS_FILE = FIGHTER_HTML_DIR / "ufc_fighter_tapology_links.txt"
FAILED_FIGHTER_URLS_FILE = FIGHTER_HTML_DIR / "ufc_failed_fighter_profile_names.txt"

SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"

