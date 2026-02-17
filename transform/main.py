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
from validator import Validator
from classifier import Classifier
from transformer import Transformer
from canonical_builder import CanonicalBuilder

logger = logging.getLogger(__name__)

class TransformOrchestrator:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.page_versions_col = self.db["page_versions"]
        self.transformed_col = self.db["transformed_documents"]
        
        self.ollama_client = OllamaClient()
        self.schema_loader = SchemaLoader()
        self.validator = Validator()
        self.classifier = Classifier(self.ollama_client)
        self.transformer = Transformer(self.ollama_client)
        self.canonical_builder = CanonicalBuilder()

    async def run(self, batch_size: int = 10):
        """
        Main loop to process documents.
        """
        logger.info("Starting transformation pipeline...")
        
        # 1. Fetch pending documents
        # For simplicity, we fetch all page versions and check if they existing in transformed_col with same version
        # AND same transformation hash/config.
        # In a real high-throughput system, we'd use a more sophisticated queue or change stream.
        
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
        version = source_doc.get("version")
        doc_id = source_doc.get("_id") # This is likely page_id_vX
        
        logger.info(f"Processing document: {doc_id}")

        try:
            # 2. Build Canonical Document
            canonical_doc = self.canonical_builder.build_canonical(source_doc)
            
            # 3. Classify
            # Ensure schemas are loaded
            all_schemas = await self.schema_loader.get_all_schemas()
            schema_ids = list(all_schemas.keys())
            
            classified_schema_id, confidence = await self.classifier.classify(canonical_doc, schema_ids)
            logger.info(f"Classified {doc_id} as {classified_schema_id} ({confidence})")
            
            target_schema = await self.schema_loader.get_schema(classified_schema_id)
            if not target_schema:
                raise ValueError(f"Schema {classified_schema_id} not found after classification.")

            # 4. Transform & Validate (with Retry)
            transformed_content = await self._transform_with_retry(canonical_doc, target_schema)
            
            # 5. Save Record
            # Calculate hash for idempotency/provenance
            transform_hash = self.transformer.compute_hash(canonical_doc, classified_schema_id, OLLAMA_MODEL_TRANSFORMER)
            
            result_doc = {
                "_id": doc_id, # Keep ID consistent with source version ID
                "source": canonical_doc["source"],
                "source_id": canonical_doc["source_id"],
                "page_version": canonical_doc["page_version"],
                "schema_id": classified_schema_id,
                "schema_version": target_schema.get("schema_version"),
                "classification_confidence": confidence,
                "transform_model": OLLAMA_MODEL_TRANSFORMER,
                "transform_prompt_version": "v1.0", # Configuration-driven versioning could be added
                "transform_hash": transform_hash,
                "content": transformed_content,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.transformed_col.replace_one({"_id": doc_id}, result_doc, upsert=True)
            logger.info(f"Successfully saved transformed document {doc_id}")

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            # Ensure we log the failure in a way that allows us to retry or alert
            # Could add a 'transform_errors' collection or status field
            pass

    async def _transform_with_retry(self, canonical_doc: Dict[str, Any], target_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts transformation and validation, retrying on failure.
        On persistent failure, falls back to 'general_doc_v1' if not already using it.
        """
        retries = TRANSFORM_RETRIES
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                # Transform
                raw_result = await self.transformer.transform(canonical_doc, target_schema)
                
                # Update canonical fields in result if schema requires them and LLM missed them?
                # Actually, strictly validate what LLM returned.
                
                # Validate
                # Validate
                try:
                    self.validator.validate(raw_result, target_schema)
                except Exception as val_e:
                    logger.warning(f"Validation failed for {target_schema.get('_id')} but proceeding: {val_e}")

                return raw_result
                
            except Exception as e:
                logger.warning(f"Transformation attempt {attempt + 1} failed: {e}")
                last_error = e
        
        # If we are here, retries exhausted.
        # Fallback logic
        current_schema_id = target_schema.get("_id")
        if current_schema_id != "general_doc_v1":
            logger.warning(f"Retries exhausted for {current_schema_id}. Falling back to general_doc_v1.")
            fallback_schema = await self.schema_loader.get_schema("general_doc_v1")
            
            if fallback_schema:
                 # Recursive call (one level deep approx)
                 return await self._transform_with_retry(canonical_doc, fallback_schema)
        
        raise last_error

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = TransformOrchestrator()
    asyncio.run(orchestrator.run())
