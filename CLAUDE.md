# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in credentials
```

### Run Infrastructure
```bash
docker-compose up -d          # Start Qdrant (6333/6334)
docker-compose down           # Stop services
```

### Run the Pipeline
```bash
# Full pipeline: extract from Confluence → transform → chunk → embed → store in Qdrant
python -m pipeline.unified_ingestion

# Re-process all pages already stored in MongoDB (skip Confluence extraction)
python -m pipeline.ingest_pipeline
```

### Export docs to Markdown
```bash
python scripts/export_to_markdown.py   # Converts data/confluence/ → docs/*.md
```

### Test Qdrant Search
```bash
python test.py   # Query Qdrant for "confluence" and print top-5 results
```

### Ollama (must be running locally)
```bash
ollama pull nomic-embed-text   # Embedding model (768 dimensions)
ollama pull qwen2.5            # LLM model (used by transformer layer)
```

## Configuration

All config lives in `confluence/config.py`, loaded from `.env` via `python-dotenv`. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CONFLUENCE_URL` | — | Atlassian Cloud base URL (e.g. `https://your-domain.atlassian.net/wiki`) |
| `CONFLUENCE_USERNAME` | — | Email address for Basic Auth |
| `CONFLUENCE_API_TOKEN` | — | Atlassian API token |
| `LOCAL_STORAGE_PATH` | `data/confluence` | Directory for local page/version JSON files |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION_NAME` | `confluence_chunks` | Qdrant collection |
| `CONFLUENCE_CLIENT_PAGE_LIMIT` | `50` | Pages per API request |
| `CONFLUENCE_CLIENT_RETRIES` | `3` | HTTP retry attempts |

## Confluence Docs

4,775 Confluence pages exported as clean Markdown in `docs/`. Use these to answer questions about the company's processes, features, and systems.

**See `docs-guide.md` for the full search guide** — space keys, doc type prefixes, search patterns by question type, and recency filtering.

### Quick reference
- Files named `{page_id}_{title}.md` with YAML frontmatter (`title`, `space`, `page_id`, `url`)
- 18.6 MB / ~4.8M tokens total — always grep first, then read 2–5 matching files
- Higher page ID = more recently created (>3B = 2023–2025, <1B = pre-2021)

```bash
grep -ril "KEYWORD" docs/ | sort -t_ -k1 -rn | head -10   # keyword search, newest first
grep -rl "^space: SRE" docs/ | xargs grep -il "KEYWORD"    # filter by space then keyword
ls docs/*RCA*.md | sort -t_ -k1 -rn | head -10             # recent RCAs
```

## Architecture

### Data Flow
```
Confluence REST API
    ↓ (CQL query: pages modified since last sync)
ConfluenceClient        [confluence/confluence_client.py]
    ↓ (raw page JSON with ADF body + metadata)
Extractor               [confluence/extractor.py]
    ↓ (change detection via version number; saves raw ADF to local disk)
LocalStorage            [confluence/local_storage.py]
    ↓ (yields (metadata, adf_json) for new/updated pages only)
AdfToCanonicalConverter [transform/confluence_to_canonical.py]
    ↓ (CanonicalDocument: sections → blocks)
Chunker                 [chunking/chunker.py]
    ↓ (Chunk list, 512 token max, block-boundary-aware)
OllamaEmbedder          [embedding/embedder.py]
    ↓ (List[List[float]], one embedding per chunk)
QdrantVectorStore       [embedding/qdrant_vector_store.py]
    ↓ (upsert with payload: text + all metadata)
Qdrant collection
```

### Key Design Decisions

**Incremental sync**: `Extractor.yield_updates()` queries Confluence via CQL for pages modified since the last sync timestamp stored in `data/confluence/sync_state.json`. On first run it uses epoch (`1970-01-01 00:00`).

**ADF → CanonicalDocument**: Confluence pages use Atlassian Document Format (ADF) JSON. `AdfToCanonicalConverter` walks the ADF tree recursively, grouping blocks under `Section` objects split by headings. Content before the first heading goes into a synthetic "Introduction" section. Code blocks preserve internal whitespace; all other text is run through `clean_text()`.

**Chunking strategy**: `Chunker` iterates blocks within each section, accumulating them until the next block would exceed 512 tokens (`cl100k_base` encoding). Block boundaries are never split mid-block. Each `Chunk` carries full provenance metadata: `doc_id`, `title`, `url`, `version`, `section_heading`, `space_key`, `parent_id`, `ancestor_ids`, and `depth`.

**Local storage layout** (under `LOCAL_STORAGE_PATH`, default `data/confluence/`):
- `pages/{page_id}.json` — current metadata per page (includes `latest_version_id`)
- `versions/{page_id}_v{version}.json` — versioned raw ADF content
- `sync_state.json` — `{ "last_sync_date": "..." }`

**Qdrant IDs**: Chunk IDs are UUIDs; if a chunk ID is not a valid UUID string, a deterministic UUID v5 is derived from it.

**Two entry points**:
- `pipeline/unified_ingestion.py` — pulls live from Confluence then processes
- `pipeline/ingest_pipeline.py` — reads from MongoDB (already-extracted pages) then processes; useful for re-embedding without hitting Confluence

### Module Map

| Module | Responsibility |
|--------|---------------|
| `confluence/config.py` | Central config, `setup_logging()` |
| `confluence/confluence_client.py` | Async Confluence REST client with pagination, retry, rate-limit handling |
| `confluence/extractor.py` | Orchestrates fetch + change detection + MongoDB persistence |
| `confluence/local_storage.py` | Local JSON file storage (pages, versions, sync state) |
| `transform/canonical_models.py` | Dataclasses: `CanonicalDocument`, `Section`, `Block`, `BlockType` |
| `transform/confluence_to_canonical.py` | ADF JSON → `CanonicalDocument` |
| `transform/cleaner.py` | Text normalization applied during ADF conversion |
| `chunking/chunker.py` | Token-limited chunking; defines `Chunk` dataclass |
| `embedding/embedder.py` | `Embedder` ABC + `OllamaEmbedder` (synchronous httpx calls) |
| `embedding/vector_store.py` | `VectorStore` ABC + `InMemoryVectorStore` stub |
| `embedding/qdrant_vector_store.py` | Async Qdrant upsert + search |
| `embedding/mongo_vector_store.py` | Alternative MongoDB Atlas vector search (not used in main pipeline) |
| `pipeline/ingest_pipeline.py` | `IngestPipeline` class: wires transform → chunk → embed → store |
| `pipeline/unified_ingestion.py` | Main entry point: extract → ingest pipeline |
