from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, Optional
import logging

from config import MONGO_URI, MONGO_DB_NAME

logger = logging.getLogger(__name__)

class SchemaLoader:
    """
    Loads and caches schemas from MongoDB.
    """
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.schemas_col = self.db["schemas"]
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a schema by ID. Uses in-memory cache to reduce DB hits.
        """
        if schema_id in self._cache:
            return self._cache[schema_id]

        schema_doc = await self.schemas_col.find_one({"_id": schema_id})
        
        if schema_doc:
            self._cache[schema_id] = schema_doc
            return schema_doc
        
        logger.warning(f"Schema not found: {schema_id}")
        return None

    async def get_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve all available schemas. Useful for the classifier.
        """
        # Refresh cache if empty or on demand (could make this smarter later)
        if not self._cache:
            cursor = self.schemas_col.find({})
            async for doc in cursor:
                self._cache[doc["_id"]] = doc
        
        return self._cache
