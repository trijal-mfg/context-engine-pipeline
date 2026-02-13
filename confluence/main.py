
import asyncio
import logging
import sys
from datetime import datetime

from config import setup_logging, ensure_directories
from extractor import Extractor

# Setup logging immediately
setup_logging()
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Confluence Extraction Service")
    start_time = datetime.now()
    
    try:
        # Ensure data directories exist
        ensure_directories()
        
        # Initialize and run extractor
        extractor = Extractor()
        stats = await extractor.run()
        
        logger.info(f"Sync completed successfully.")
        logger.info(f"Stats: Fetched={stats['fetched']}, Skipped={stats['skipped']}, Updated={stats['updated']}, Errors={stats['errors']}")
        
    except Exception as e:
        logger.critical(f"Fatal error during execution: {e}", exc_info=True)
        sys.exit(1)
        
    duration = datetime.now() - start_time
    logger.info(f"Execution time: {duration}")

if __name__ == "__main__":
    asyncio.run(main())
