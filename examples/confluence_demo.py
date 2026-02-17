import json
import logging
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from confluence.transform import adf_to_sections, chunk_sections

def main():
    logging.basicConfig(level=logging.INFO)
    
    # Sample ADF
    sample_adf = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Project Overview"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "This project aims to implement a robust ingestion pipeline."}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Phase 1: Ingestion"}]}]
                    },
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Phase 2: RAG Integration"}]}]
                    }
                ]
            }
        ]
    }
    
    metadata = {
        "id": "12345",
        "title": "Ingestion Pipeline Design",
        "version": {"number": 1},
        "space": {"key": "PROJ"},
        "ancestors": [{"id": "999"}]
    }
    
    print("--- 1. Converting ADF to Sections ---")
    page_data = adf_to_sections(sample_adf, metadata)
    print(json.dumps(page_data, indent=2))
    
    print("\n--- 2. Chunking Sections ---")
    chunks = chunk_sections(page_data, max_tokens=50)
    
    for chunk in chunks:
        print(f"\nChunk ID: {chunk['chunk_id']}")
        print(f"Parent ID: {chunk['parent_id']}")
        print(f"Embedding Text:\n---\n{chunk['embedding_text']}\n---")

if __name__ == "__main__":
    main()
