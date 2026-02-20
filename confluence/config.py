
import os
import logging
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
load_dotenv(find_dotenv())

# MongoDB Settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "confluence_ingestion")

# Concfluence Settings
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

# Sync State
DEFAULT_SYNC_DATE = "1970-01-01 00:00" # Default sync date only for first extraction, later it will be updated to last sync date

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()



# Confluence Client Settings
CONFLUENCE_CLIENT_PAGE_LIMIT = int(os.getenv("CONFLUENCE_CLIENT_PAGE_LIMIT", 50))
CONFLUENCE_CLIENT_RETRIES = int(os.getenv("CONFLUENCE_CLIENT_RETRIES", 3))

# Ollama Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# Vector Store Settings
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "confluence_chunks")


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
