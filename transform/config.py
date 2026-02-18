import os
from dotenv import load_dotenv

load_dotenv()

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_CLASSIFIER = os.getenv("OLLAMA_MODEL_CLASSIFIER", "llama3")
OLLAMA_MODEL_TRANSFORMER = os.getenv("OLLAMA_MODEL_TRANSFORMER", "llama3")
OLLAMA_MODEL_EMBEDDING = os.getenv("OLLAMA_MODEL_EMBEDDING", "nomic-embed-text")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "confluence_ingestion")

# Timeout/Retry Configuration
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
TRANSFORM_RETRIES = int(os.getenv("TRANSFORM_RETRIES", "1"))
