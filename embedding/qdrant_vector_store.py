import logging
import uuid
from typing import List, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from chunking.chunker import Chunk
from embedding.vector_store import VectorStore
from confluence.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME

logger = logging.getLogger(__name__)

class QdrantVectorStore(VectorStore):
    def __init__(self):
        self.client = AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.collection_name = QDRANT_COLLECTION_NAME
        self._collection_initialized = False

    async def _ensure_collection(self, vector_size: int):
        if self._collection_initialized:
            return

        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)

        if not exists:
            logger.info(f"Creating Qdrant collection '{self.collection_name}' with size {vector_size}")
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
        
        self._collection_initialized = True

    async def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]):
        if not chunks:
            return

        # Ensure collection exists (assume all embeddings have same dim)
        vector_size = len(embeddings[0])
        await self._ensure_collection(vector_size)

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            # Qdrant requires UUIDs or integers for IDs. 
            # If chunk.id is a valid UUID string, we use it directly. 
            # Otherwise we generate a UUID from it.
            try:
                point_id = str(uuid.UUID(chunk.id))
            except ValueError:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.id))

            payload = {
                "chunk_id": chunk.id,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                **chunk.metadata
            }

            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            ))

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Upserted {len(points)} chunks to Qdrant collection '{self.collection_name}'")

    async def search(self, query_embedding: List[float], limit: int = 5, space_key: Optional[str] = None) -> List[Chunk]:
        # Create filter if space_key is provided
        query_filter = None
        if space_key:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="space_key",
                        match=models.MatchValue(value=space_key)
                    )
                ]
            )

        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=query_filter
        )

        chunks = []
        for point in results:
            payload = point.payload
            
            # Reconstruct Chunk object
            # Note: total_chunks is not stored in payload currently, setting to 0
            chunk = Chunk(
                id=payload.get("chunk_id"),
                doc_id=payload.get("doc_id"),
                chunk_index=payload.get("chunk_index"),
                total_chunks=0, 
                text=payload.get("text"),
                metadata={k: v for k, v in payload.items() if k not in ["chunk_id", "doc_id", "chunk_index", "text"]}
            )
            chunks.append(chunk)

        return chunks
