import asyncio
import logging
import sys
from typing import List

from confluence.storage import MongoStorage
from transform.confluence_to_canonical import AdfToCanonicalConverter
from chunking.chunker import Chunker, Chunk
from embedding.embedder import OllamaEmbedder
from embedding.mongo_vector_store import MongoVectorStore

# Check if we should use existing logging setup or configure here
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IngestPipeline:
    def __init__(self):
        self.storage = MongoStorage()
        self.converter = AdfToCanonicalConverter()
        self.chunker = Chunker()
        self.embedder = OllamaEmbedder()
        self.vector_store = MongoVectorStore()

    async def run(self):
        logger.info("Starting ingestion pipeline...")
        
        processed_count = 0
        
        async for metadata, content in self.storage.get_all_pages():
            page_id = metadata.get("page_id")
            title = metadata.get("title", "Unknown")
            
            logger.info(f"Processing page: {title} ({page_id})")
            
            try:
                # 1. Transform
                # content is ADF string/dict - wait, storage saves it as 'content'
                # Mongo might have stored it as dict if we passed dict, or string.
                # In extractor.py: `body = page.get("body", {}).get("atlas_doc_format", {}).get("value", "")`
                # If value is string (serialized JSON), we need to parse it. 
                # ADF 'value' is usually a JSON string provided by Confluence API? 
                # Or dict?
                # Confluence API v2 returns ADF as object? 
                # Wait, `atlas_doc_format` value is usually JSON string.
                # Let's assume it's a JSON string and parse it, or check type.
                import json
                if isinstance(content, str):
                    try:
                        adf_json = json.loads(content)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse ADF JSON for {page_id}")
                        continue
                else:
                    adf_json = content
                
                canonical_doc = self.converter.convert(metadata, adf_json)
                
                # 2. Clean (Implicit in Transform layer)
                
                # 3. Chunk
                chunks = self.chunker.chunk_document(canonical_doc)
                logger.info(f"Generated {len(chunks)} chunks for {page_id}")
                
                if not chunks:
                    continue

                # 4. Embed
                texts_to_embed = [chunk.text for chunk in chunks]
                embeddings = self.embedder.embed_texts(texts_to_embed)
                
                # 5. Store
                self.vector_store.upsert(chunks, embeddings)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing page {page_id}: {e}", exc_info=True)
                
        logger.info(f"Pipeline finished. Processed {processed_count} pages.")

async def main():
    pipeline = IngestPipeline()
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
