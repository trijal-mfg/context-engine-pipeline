
import logging
import hashlib
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from confluence_client import ConfluenceClient
from storage import (
    get_metadata, 
    save_raw_content, 
    save_metadata, 
    get_last_sync_date,
    update_last_sync_date
)

logger = logging.getLogger(__name__)

class Extractor:
    def __init__(self):
        self.client = ConfluenceClient()
        self.stats = {
            "fetched": 0,
            "skipped": 0,
            "updated": 0,
            "errors": 0
        }

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _extract_metadata(self, page_data: Dict[str, Any], raw_path: str, content_hash: str) -> Dict[str, Any]:
        """
        Transform Confluence API response into stored metadata format.
        """
        ancestors = page_data.get("ancestors", [])
        ancestor_ids = [str(a["id"]) for a in ancestors]
        parent_id = ancestor_ids[-1] if ancestor_ids else None
        
        version_data = page_data.get("version", {})
        
        return {
            "page_id": str(page_data["id"]),
            "space_key": page_data.get("space", {}).get("key", "UNKNOWN"),
            "title": page_data["title"],
            "version": version_data.get("number", 1),
            "last_modified": version_data.get("when"),
            "parent_id": parent_id,
            "ancestor_ids": ancestor_ids,
            "depth": len(ancestor_ids),
            "content_hash": content_hash,
            "raw_path": str(raw_path),
            "is_deleted": False, # Basic search doesn't return deleted pages
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

    async def process_page(self, page: Dict[str, Any]):
        """
        Process a single page: compare version, save if necessary.
        """
        page_id = str(page["id"])
        new_version = page.get("version", {}).get("number", 1)
        
        # Check existing metadata
        existing_meta = get_metadata(page_id)
        
        if existing_meta:
            if existing_meta.get("version") == new_version:
                logger.info(f"Skipping page {page_id} (version {new_version} up to date)")
                self.stats["skipped"] += 1
                return

        # Extract content
        try:
            body = page.get("body", {}).get("storage", {}).get("value", "")
            space_key = page.get("space", {}).get("key", "UNKNOWN")
            
            # Save Raw
            raw_path = await save_raw_content(space_key, page_id, new_version, body)
            
            # Compute Hash
            content_hash = self._compute_hash(body)
            
            # Build and Save Metadata
            metadata = self._extract_metadata(page, raw_path, content_hash)
            await save_metadata(page_id, metadata)
            
            logger.info(f"Updated page {page_id} to version {new_version}")
            self.stats["updated"] += 1
            
        except Exception as e:
            logger.error(f"Failed to process page {page_id}: {e}")
            self.stats["errors"] += 1

    async def run(self):
        """
        Main execution loop.
        """
        last_sync = get_last_sync_date()
        logger.info(f"Starting sync from {last_sync}")
        
        try:
            async for page in self.client.get_updated_pages(last_sync):
                self.stats["fetched"] += 1
                await self.process_page(page)
                
            # Only update sync state if no critical system errors occurred.
            # Page-level errors are logged but don't stop the sync date update 
            # (unless we want to strict retry, but specs say "If one page fails, log and continue")
            # "If system-level failure occurs, exit with error" -> Caught in main.
            
            # We use the current time for the next sync, or the max LastModified seen? 
            # Using current time is safer to avoid gaps, but might re-fetch if clocks skew.
            # Better to use the time the sync started.
            
            # Specs: "Only update last_sync_date AFTER successful full execution"
            new_sync_date = datetime.utcnow().isoformat() + "Z"
            update_last_sync_date(new_sync_date)
            
        except Exception as e:
            logger.error(f"System-level failure during sync: {e}")
            raise

        return self.stats
