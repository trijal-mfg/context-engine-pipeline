import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator

from .config import LOCAL_STORAGE_PATH, DEFAULT_SYNC_DATE

logger = logging.getLogger(__name__)


class LocalStorage:
    def __init__(self, base_path: str = LOCAL_STORAGE_PATH):
        self.base = Path(base_path)
        self.pages_dir = self.base / "pages"
        self.versions_dir = self.base / "versions"
        self.sync_state_file = self.base / "sync_state.json"

        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    async def ensure_indexes(self):
        pass  # No-op for local storage

    async def get_last_sync_date(self) -> str:
        if self.sync_state_file.exists():
            data = json.loads(self.sync_state_file.read_text())
            return data.get("last_sync_date", DEFAULT_SYNC_DATE)
        return DEFAULT_SYNC_DATE

    async def update_last_sync_date(self, timestamp: str):
        self.sync_state_file.write_text(json.dumps({"last_sync_date": timestamp}))
        logger.info(f"Updated sync state to {timestamp}")

    async def get_metadata(self, page_id: str) -> Optional[Dict[str, Any]]:
        path = self.pages_dir / f"{page_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    async def save_page(self, page_id: str, metadata: Dict[str, Any], content: str, version: int, content_hash: str):
        version_id = f"{page_id}_v{version}"
        version_doc = {
            "page_id": page_id,
            "version": version,
            "content": content,
            "content_hash": content_hash,
            "collected_at": datetime.utcnow().isoformat()
        }
        version_path = self.versions_dir / f"{version_id}.json"
        version_path.write_text(json.dumps(version_doc, indent=2))

        metadata["_id"] = page_id
        metadata["latest_version_id"] = version_id
        metadata["last_updated_at"] = datetime.utcnow().isoformat()

        page_path = self.pages_dir / f"{page_id}.json"
        page_path.write_text(json.dumps(metadata, indent=2))

    async def get_all_pages(self) -> AsyncGenerator:
        for page_file in self.pages_dir.glob("*.json"):
            metadata = json.loads(page_file.read_text())
            page_id = metadata.get("_id") or page_file.stem
            latest_version_id = metadata.get("latest_version_id")

            if not latest_version_id:
                logger.warning(f"Page {page_id} has no latest_version_id, skipping.")
                continue

            version_path = self.versions_dir / f"{latest_version_id}.json"
            if not version_path.exists():
                logger.warning(f"Version file {latest_version_id}.json not found for page {page_id}, skipping.")
                continue

            version_doc = json.loads(version_path.read_text())
            content = version_doc.get("content")
            yield metadata, content
