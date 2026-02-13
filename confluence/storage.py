"""
THis is a temp storage module, as the data grows storage will probably move to s3/back to confluence or some db
"""


import json
import os
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from config import RAW_DIR, META_DIR, STATE_DIR, SYNC_STATE_FILE, DEFAULT_SYNC_DATE

logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [RAW_DIR, META_DIR, STATE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

def get_last_sync_date() -> str:
    """Read the last sync date from state file, or return default."""
    if not SYNC_STATE_FILE.exists():
        return DEFAULT_SYNC_DATE
    
    try:
        with open(SYNC_STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("last_sync_date", DEFAULT_SYNC_DATE)
    except Exception as e:
        logger.error(f"Failed to read sync state: {e}")
        return DEFAULT_SYNC_DATE

def update_last_sync_date(timestamp: str):
    """Update the last sync date only on full success."""
    temp_file = SYNC_STATE_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, 'w') as f:
            json.dump({"last_sync_date": timestamp}, f, indent=2)
        temp_file.replace(SYNC_STATE_FILE)
        logger.info(f"Updated sync state to {timestamp}")
    except Exception as e:
        logger.error(f"Failed to update sync state: {e}")
        if temp_file.exists():
            os.remove(temp_file)

def get_metadata(page_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve existing metadata for a page if it exists."""
    meta_path = META_DIR / f"{page_id}.json"
    if not meta_path.exists():
        return None
    
    try:
        with open(meta_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read metadata for page {page_id}: {e}")
        return None

async def save_raw_content(space_key: str, page_id: str, version: int, content: str) -> str:
    """Save raw HTML content to disk."""
    directory = RAW_DIR / space_key / page_id
    directory.mkdir(parents=True, exist_ok=True)
    
    filename = directory / f"version_{version}.json"
    async with aiofiles.open(filename, 'w') as f:
        await f.write(json.dumps(content))
    
    return str(filename)

async def save_metadata(space_key: str, page_id: str, metadata: Dict[str, Any]):
    """Save structured metadata to disk."""

    directory = RAW_DIR / space_key / page_id
    filename = directory / f"metadata.json"
    async with aiofiles.open(filename, 'w') as f:
        await f.write(json.dumps(metadata, indent=2))

    #dedeicated metadata directory for metadata storage    
    meta_path = META_DIR / f"{page_id}.json"
    async with aiofiles.open(meta_path, 'w') as f:
        await f.write(json.dumps(metadata, indent=2))
