
import os
import logging
from pathlib import Path

# Base directory for data
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
CONFLUENCE_DATA_DIR = DATA_DIR / "confluence"
RAW_DIR = CONFLUENCE_DATA_DIR / "raw"
META_DIR = CONFLUENCE_DATA_DIR / "meta"
STATE_DIR = CONFLUENCE_DATA_DIR / "state"

# Concfluence Settings
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

# Sync State
SYNC_STATE_FILE = STATE_DIR / "sync_state.json"
DEFAULT_SYNC_DATE = "1970-01-01 00:00" # Default sync date only for first extraction, later it will be updated to last sync date

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# Confluence Client Settings
CONFLUENCE_CLIENT_PAGE_LIMIT = int(os.getenv("CONFLUENCE_CLIENT_PAGE_LIMIT", 50))
CONFLUENCE_CLIENT_RETRIES = int(os.getenv("CONFLUENCE_CLIENT_RETRIES", 3))

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
