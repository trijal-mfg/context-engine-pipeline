import unittest
import json
import logging
from confluence.transform import adf_to_sections, chunk_sections, get_embedding_text

# Configure logging
logging.basicConfig(level=logging.INFO)

class TestConfluenceTransform(unittest.TestCase):
    
    def test_adf_to_sections_simple(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello World"}]
                }
            ]
        }
        metadata = {
            "id": "123",
            "title": "Test Page",
            "version": {"number": 1},
            "space": {"key": "TEST"},
            "ancestors": []
        }
        
        result = adf_to_sections(adf, metadata)
        
        self.assertEqual(result["page_id"], "123")
        self.assertEqual(len(result["sections"]), 1)
        self.assertEqual(result["sections"][0]["heading"], None)
        self.assertIn("Hello World", result["sections"][0]["content"])

    def test_adf_to_sections_headings(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Preamble"}]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Section 1"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Content 1"}]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Subsection"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Content Sub"}]
                }
            ]
        }
        metadata = {
            "id": "123", 
            "title": "Headings",
            "version": {"number": 1}, 
            "space": {"key": "TEST"}
        }
        
        result = adf_to_sections(adf, metadata)
        self.assertEqual(len(result["sections"]), 3)
        
        self.assertIsNone(result["sections"][0]["heading"])
        self.assertIn("Preamble", result["sections"][0]["content"])
        
        self.assertEqual(result["sections"][1]["heading"], "Section 1")
        self.assertEqual(result["sections"][1]["level"], 1)
        
        self.assertEqual(result["sections"][2]["heading"], "Subsection")
        self.assertEqual(result["sections"][2]["level"], 2)

    def test_chunk_sections_ancestors_and_parents(self):
        page_data = {
            "page_id": "100",
            "version": 2,
            "space_key": "S",
            "title": "Child Page",
            "ancestors": [{"id": "10"}, {"id": "50"}],
            "sections": [
                {"heading": "Intro", "level": 1, "content": "Just text."}
            ]
        }
        
        chunks = chunk_sections(page_data, max_tokens=100)
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        
        self.assertEqual(chunk["ancestor_ids"], ["10", "50"])
        self.assertEqual(chunk["parent_id"], "50")
        self.assertEqual(chunk["depth"], 1)

    def test_chunk_splitting(self):
        long_text = "Word " * 200  # 1000 chars -> ~250 tokens
        page_data = {
            "page_id": "1",
            "version": 1,
            "space_key": "S",
            "title": "Long",
            "ancestors": [],
            "sections": [
                {"heading": None, "level": None, "content": long_text}
            ]
        }
        
        # Set max_tokens to 50
        chunks = chunk_sections(page_data, max_tokens=50)
        self.assertTrue(len(chunks) > 1, "Should split chunks")
        
        # Verify IDs form sequence
        ids = [c["chunk_id"] for c in chunks]
        self.assertEqual(ids[0], "1_v1_s0_c0")
        self.assertEqual(ids[1], "1_v1_s0_c1")

    def test_embedding_format(self):
        chunk = {
            "title": "My Page",
            "heading": "Overview",
            "content": "This is content."
        }
        text = get_embedding_text(chunk)
        expected = "Title: My Page\nSection: Overview\n\nThis is content."
        self.assertEqual(text, expected)

    def test_determinism(self):
        adf = {
            "type": "doc",
            "content": [
                {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "H1"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Text"}]}
            ]
        }
        metadata = {"id": "999", "title": "D", "version": 1, "space": "K"}
        
        res1 = adf_to_sections(adf, metadata)
        chunks1 = chunk_sections(res1)
        
        res2 = adf_to_sections(adf, metadata)
        chunks2 = chunk_sections(res2)
        
        self.assertEqual(chunks1, chunks2)
        self.assertEqual(chunks1[0]["chunk_id"], chunks2[0]["chunk_id"])

if __name__ == "__main__":
    unittest.main()
