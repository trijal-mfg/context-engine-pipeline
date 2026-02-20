"""
tmp orchestration for testing
"""


import asyncio
import logging
import argparse
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import UpdateOne
from datetime import datetime, timezone

from config import MONGO_URI, MONGO_DB_NAME, TRANSFORM_RETRIES, OLLAMA_MODEL_TRANSFORMER
from ollama_client import OllamaClient
from schema_loader import SchemaLoader
from transformer import Transformer


logger = logging.getLogger(__name__)

class TransformOrchestrator:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.page_versions_col = self.db["page_versions"]
        self.transformed_col = self.db["transformed_documents"]
        
        self.ollama_client = OllamaClient()
        self.schema_loader = SchemaLoader()
        self.transformer = Transformer(self.ollama_client)


    async def run(self, batch_size: int = 10):
        """
        Main loop to process documents.
        """
        logger.info("Starting transformation pipeline...")
        
        cursor = self.page_versions_col.find({}).limit(batch_size) # TODO: Implement better diff logic
        
        tasks = []
        async for doc in cursor:
            tasks.append(self.process_document(doc))
            
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error in batch: {res}")
        
        logger.info("Batch processing complete.")

    async def process_document(self, source_doc: Dict[str, Any]):
        page_id = source_doc.get("page_id")
        doc_id = source_doc.get("_id")
        
        logger.info(f"Processing document: {doc_id}")

        try:
            canonical_doc = source_doc 

            available_models = await self.schema_loader.get_all_models()
            
            if not available_models:
                logger.error("No schemas found in database. Cannot proceed.")
                return

            extraction_result = await self.transformer.transform(canonical_doc, available_models)
            
            schema_id = getattr(extraction_result, "schema_type", "unknown")
            
            transformed_content = extraction_result.model_dump()
            
            logger.info(f"Extracted {doc_id} as {schema_id}")

            # Calculate hash
            transform_hash = self.transformer.compute_hash(canonical_doc, OLLAMA_MODEL_TRANSFORMER)
            
            result_doc = {
                "_id": doc_id, 
                "source": canonical_doc.get("source", "unknown"),
                "source_id": canonical_doc.get("source_id", "unknown"),
                "page_version": canonical_doc.get("page_version", "unknown"),
                "schema_id": schema_id,
                "transform_model": OLLAMA_MODEL_TRANSFORMER,
                "transform_hash": transform_hash,
                "content": transformed_content,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.transformed_col.replace_one({"_id": doc_id}, result_doc, upsert=True)
            logger.info(f"Successfully saved transformed document {doc_id}")

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            pass

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = TransformOrchestrator()
    asyncio.run(orchestrator.run())
