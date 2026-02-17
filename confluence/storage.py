import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from config import MONGO_URI, MONGO_DB_NAME, DEFAULT_SYNC_DATE

logger = logging.getLogger(__name__)

class MongoStorage:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.pages_col = self.db["pages"]
        self.versions_col = self.db["page_versions"]
        self.sync_state_col = self.db["sync_state"]
        
    async def ensure_indexes(self):
        """Create necessary indexes for performance."""
        # Pages: query by space and update date
        await self.pages_col.create_index("space_key")
        await self.pages_col.create_index("updated_at")
        
        # Versions: query by page_id and version
        await self.versions_col.create_index([("page_id", 1), ("version", 1)], unique=True)
        
    async def get_last_sync_date(self) -> str:
        """Retrieve the last sync timestamp."""
        doc = await self.sync_state_col.find_one({"_id": "global_confluence_sync"})
        if doc and "last_sync_date" in doc:
            return doc["last_sync_date"]
        return DEFAULT_SYNC_DATE

    async def update_last_sync_date(self, timestamp: str):
        """Update the last sync timestamp."""
        await self.sync_state_col.update_one(
            {"_id": "global_confluence_sync"},
            {"$set": {"last_sync_date": timestamp}},
            upsert=True
        )
        logger.info(f"Updated sync state to {timestamp}")

    async def get_metadata(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific page."""
        return await self.pages_col.find_one({"_id": page_id})

    async def save_page(self, page_id: str, metadata: Dict[str, Any], content: str, version: int, content_hash: str):
        """
        Save both content (versioned) and metadata (current state) in a transaction-like manner.
        """
        # 1. Save Content Version
        version_id = f"{page_id}_v{version}"
        version_doc = {
            "_id": version_id,
            "page_id": page_id,
            "version": version,
            "content": content,
            "content_hash": content_hash,
            "collected_at": datetime.utcnow().isoformat()
        }
        
        try:
            await self.versions_col.replace_one(
                {"_id": version_id}, 
                version_doc, 
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save version {version_id}: {e}")
            raise

        # 2. Update Page Metadata
        # Ensure _id is set for the document
        metadata["_id"] = page_id
        
        # Add references to latest version
        metadata["latest_version_id"] = version_id
        metadata["last_updated_at"] = datetime.utcnow().isoformat()

        try:
            await self.pages_col.replace_one(
                {"_id": page_id},
                metadata,
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save metadata for {page_id}: {e}")
            raise

