from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, Optional, List, Type
import logging
from pydantic import BaseModel

from config import MONGO_URI, MONGO_DB_NAME
from model_factory import ModelFactory

logger = logging.getLogger(__name__)

class SchemaLoader:
    """
    Loads schemas from MongoDB and converts them to Pydantic models.
    """
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.schemas_col = self.db["schemas"]
        self._model_cache: List[Type[BaseModel]] = []

    async def get_all_models(self) -> List[Type[BaseModel]]:
        """
        Retrieve all available schemas as Pydantic models.
        """
        # Refresh cache if empty (simple caching strategy)
        if not self._model_cache:
            cursor = self.schemas_col.find({})
            models = []
            async for doc in cursor:
                try:
                    model = ModelFactory.create_pydantic_model(doc)
                    models.append(model)
                except Exception as e:
                    logger.error(f"Failed to create model for schema {doc.get('_id')}: {e}")
            
            self._model_cache = models
        
        return self._model_cache

    async def refresh_cache(self):
        """Force refresh of the schema cache."""
        self._model_cache = []
        await self.get_all_models()
