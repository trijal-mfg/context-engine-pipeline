from typing import List, Dict, Any
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from chunking.chunker import Chunk
from embedding.vector_store import VectorStore
from confluence.config import MONGO_URI, MONGO_DB_NAME, MONGO_VECTOR_COLLECTION, MONGO_VECTOR_INDEX_NAME

logger = logging.getLogger(__name__)

class MongoVectorStore(VectorStore):
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.collection = self.db[MONGO_VECTOR_COLLECTION]
        
    async def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]):
        operations = []
        for chunk, embedding in zip(chunks, embeddings):
            doc = {
                "chunk_id": chunk.id,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "embedding": embedding,
                "metadata": chunk.metadata
            }
            operations.append(
                UpdateOne({"chunk_id": chunk.id}, {"$set": doc}, upsert=True)
            )
            
        if operations:
            result = await self.collection.bulk_write(operations)
            logger.info(f"Upserted {result.upserted_count + result.modified_count} chunks to MongoDB.")

    async def search(self, query_embedding: List[float], limit: int = 5) -> List[Chunk]:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": MONGO_VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 20,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "embedding": 0,
                     "_id": 0,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=limit)
        
        chunks = []
        for doc in results:
            chunk = Chunk(
                id=doc["chunk_id"],
                doc_id=doc["doc_id"],
                chunk_index=doc["chunk_index"],
                total_chunks=0, # Not strictly needed for search result
                text=doc["text"],
                metadata=doc["metadata"]
            )
            chunks.append(chunk)
            
        return chunks
