import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

from pipeline.ingest_pipeline import IngestPipeline
from confluence.storage import MongoStorage

# Mock data
SAMPLE_ADF = {
    "version": 1,
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 1},
            "content": [{"type": "text", "text": "Test Page Title"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "This is a test paragraph with some content."}]
        },
        {
             "type": "heading",
             "attrs": {"level": 2},
             "content": [{"type": "text", "text": "Section 1"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Content for section 1."}]
        }
    ]
}

SAMPLE_METADATA = {
    "_id": "12345",
    "page_id": "12345",
    "title": "Test Page",
    "version": 1,
    "latest_version_id": "12345_v1"
}

async def mock_get_all_pages():
    import json
    yield SAMPLE_METADATA, json.dumps(SAMPLE_ADF)

async def test_pipeline():
    print("Setting up pipeline test...")
    pipeline = IngestPipeline()
    
    # Mock storage
    pipeline.storage = MagicMock(spec=MongoStorage)
    pipeline.storage.get_all_pages = mock_get_all_pages
    
    # Run pipeline
    print("Running pipeline...")
    await pipeline.run()
    
    # Verify
    print("\nVerifying results...")
    # Check vector store
    store = pipeline.vector_store
    if hasattr(store, "store"):
        chunks = list(store.store.values())
        print(f"Stored {len(chunks)} chunks.")
        for data in chunks:
            chunk = data["chunk"]
            print(f"Chunk ID: {chunk.id}")
            print(f"Indices: {chunk.chunk_index}/{chunk.total_chunks}")
            print(f"Section: {chunk.metadata['section_heading']}")
            print(f"Text Preview: {chunk.text[:50]}...")
            print("-" * 20)
            
    if len(chunks) > 0:
        print("SUCCESS: Pipeline processed data and stored chunks.")
    else:
        print("FAILURE: No chunks stored.")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
