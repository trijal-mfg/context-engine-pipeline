import asyncio
import logging
import unittest
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

class TestIngestPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_flow(self):
        print("\nSetting up pipeline test...")
        pipeline = IngestPipeline()
        
        # Mock storage
        pipeline.storage = MagicMock(spec=MongoStorage)
        pipeline.storage.get_all_pages = mock_get_all_pages
        
        # Run pipeline
        print("Running pipeline...")
        await pipeline.run()
        
        # Verify
        print("Verifying results...")
        store = pipeline.vector_store
        
        # Verify upsert was called
        # We need to spy on the vector store or check if we Mocked it?
        # In this test setup, we instantiated IngestPipeline which creates real objects.
        # We should replace them with Mocks for the test to be isolated.
        
    async def test_pipeline_with_mocks(self):
        print("\nSetting up pipeline test with mocks...")
        pipeline = IngestPipeline()
        
        # Mock storage
        pipeline.storage = MagicMock(spec=MongoStorage)
        pipeline.storage.get_all_pages = mock_get_all_pages
        
        # Mock Vector Store to avoid real DB calls
        pipeline.vector_store = AsyncMock() 
        
        # Run pipeline
        print("Running pipeline...")
        await pipeline.run()
        
        # Verify Upsert
        pipeline.vector_store.upsert.assert_called()
        call_args = pipeline.vector_store.upsert.call_args
        chunks, embeddings = call_args[0]
        
        print(f"Upsert called with {len(chunks)} chunks.")
        self.assertEqual(len(chunks), 2)
        
        # Check first chunk
        chunk = chunks[0]
        self.assertEqual(chunk.doc_id, "12345")
        self.assertIn("This is a test paragraph", chunk.text)
        self.assertEqual(chunk.metadata["section_heading"], "Test Page Title")

if __name__ == "__main__":
    unittest.main()
