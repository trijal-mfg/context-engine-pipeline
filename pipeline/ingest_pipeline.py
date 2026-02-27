import asyncio
import logging
import sys
from typing import List

from confluence.local_storage import LocalStorage
from transform.confluence_to_canonical import AdfToCanonicalConverter
from chunking.chunker import Chunker, Chunk
from embedding.embedder import OllamaEmbedder
from embedding.embedder import OllamaEmbedder
from embedding.qdrant_vector_store import QdrantVectorStore

from confluence.config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

class IngestPipeline:
    def __init__(self):
        self.storage = LocalStorage()
        self.converter = AdfToCanonicalConverter()
        self.chunker = Chunker()
        self.embedder = OllamaEmbedder()
        self.vector_store = QdrantVectorStore()

    async def process_page(self, metadata, content):
        page_id = metadata.get("page_id")
        title = metadata.get("title", "Unknown")
        
        logger.info(f"Processing page: {title} ({page_id})")
        
        try:
            import json
            if isinstance(content, str):
                try:
                    adf_json = json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse ADF JSON for {page_id}")
                    return False
            else:
                adf_json = content
            
            canonical_doc = self.converter.convert(metadata, adf_json)
            
            # 2. Clean (Implicit in Transform layer)
            
            # 3. Chunk
            chunks = self.chunker.chunk_document(canonical_doc)
            logger.info(f"Generated {len(chunks)} chunks for {page_id}")
            
            if not chunks:
                return True

            # 4. Embed
            texts_to_embed = [chunk.text for chunk in chunks]
            embeddings = self.embedder.embed_texts(texts_to_embed)
            
            # 5. Store
            await self.vector_store.upsert(chunks, embeddings)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing page {page_id}: {e}", exc_info=True)
            return False

    async def run(self):
        logger.info("Starting ingestion pipeline...")
        
        processed_count = 0
        
        async for metadata, content in self.storage.get_all_pages():
            success = await self.process_page(metadata, content)
            if success:
                processed_count += 1
                
        logger.info(f"Pipeline finished. Processed {processed_count} pages.")

async def main():
    pipeline = IngestPipeline()
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
