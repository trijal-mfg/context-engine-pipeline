
import logging
import hashlib
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone

from confluence_client import ConfluenceClient
from storage import MongoStorage

logger = logging.getLogger(__name__)

class Extractor:
    def __init__(self):
        self.client = ConfluenceClient()
        self.storage = MongoStorage()
        self.stats = {
            "fetched": 0,
            "skipped": 0,
            "updated": 0,
            "errors": 0
        }

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _extract_metadata(self, page_data: Dict[str, Any], content_hash: str) -> Dict[str, Any]:
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
            "is_deleted": False, 
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

    async def process_page(self, page: Dict[str, Any]):
        """
        Process a single page: compare version, save if necessary.
        """
        page_id = str(page["id"])
        new_version = page.get("version", {}).get("number", 1)
        
        # Check existing metadata
        existing_meta = await self.storage.get_metadata(page_id)
        
        if existing_meta:
            if existing_meta.get("version") == new_version:
                logger.info(f"Skipping page {page_id} (version {new_version} up to date)")
                self.stats["skipped"] += 1
                return

        # Extract content
        try:
            body = page.get("body", {}).get("atlas_doc_format", {}).get("value", "")
            
            # Compute Hash
            content_hash = self._compute_hash(body)
            
            # Build Metadata
            metadata = self._extract_metadata(page, content_hash)
            
            # Save using MongoStorage Transaction-like method
            await self.storage.save_page(
                page_id=page_id,
                metadata=metadata,
                content=body,
                version=new_version,
                content_hash=content_hash
            )
            
            logger.info(f"Updated page {page_id} to version {new_version}")
            self.stats["updated"] += 1
            
        except Exception as e:
            logger.error(f"Failed to process page {page_id}: {e}")
            self.stats["errors"] += 1

    async def run(self):
        """
        Main execution loop.
        """
        # Ensure indexes
        await self.storage.ensure_indexes()

        last_sync = await self.storage.get_last_sync_date()
        logger.info(f"Starting sync from {last_sync}")
        
        try:
            async for page in self.client.get_updated_pages(last_sync):
                self.stats["fetched"] += 1
                await self.process_page(page)
                
            # Update sync state
            new_sync_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            await self.storage.update_last_sync_date(new_sync_date)
            
        except Exception as e:
            logger.error(f"System-level failure during sync: {e}")
            raise

        return self.stats
