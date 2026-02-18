import asyncio
import logging
import sys
from datetime import datetime

from confluence.extractor import Extractor
from pipeline.ingest_pipeline import IngestPipeline
from confluence.config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Unified Ingestion Pipeline")
    start_time = datetime.now()
    
    try:
        # Initialize pipeline and extractor
        pipeline = IngestPipeline()
        extractor = Extractor()
        
        logger.info("Listening for updates from Confluence...")
        
        processed_count = 0
        
        # Iterate over updates as they are fetched
        async for metadata, content in extractor.yield_updates():
            success = await pipeline.process_page(metadata, content)
            if success:
                processed_count += 1
            
        stats = extractor.stats
        
        logger.info(f"Sync completed successfully.")
        logger.info(f"Stats: Fetched={stats['fetched']}, Skipped={stats['skipped']}, Updated={stats['updated']}, Errors={stats['errors']}")
        logger.info(f"Pipeline Processed: {processed_count} pages")
        
    except Exception as e:
        logger.critical(f"Fatal error during execution: {e}", exc_info=True)
        sys.exit(1)
        
    duration = datetime.now() - start_time
    logger.info(f"Execution time: {duration}")

if __name__ == "__main__":
    asyncio.run(main())
