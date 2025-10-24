"""
Main entry point untuk Pub-Sub Log Aggregator
"""
import asyncio
import logging
import sys
import uvicorn
from src.dedup_store import DedupStore
from src.event_processor import EventProcessor
from src.api import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def startup_event(processor: EventProcessor):
    """Startup event handler"""
    logger.info("=" * 60)
    logger.info("Starting Pub-Sub Log Aggregator")
    logger.info("=" * 60)
    
    await processor.start()
    logger.info("✓ Event processor started")
    
    logger.info("=" * 60)
    logger.info("Service is ready to accept requests")
    logger.info("=" * 60)


async def shutdown_event(processor: EventProcessor):
    """Shutdown event handler"""
    logger.info("=" * 60)
    logger.info("Shutting down gracefully...")
    logger.info("=" * 60)
    
    if processor:
        await processor.stop()
        logger.info("✓ Event processor stopped")
        
        # Log final stats
        stats = processor.get_stats()
        logger.info(f"Final stats:")
        logger.info(f"  - Received: {stats.received}")
        logger.info(f"  - Unique processed: {stats.unique_processed}")
        logger.info(f"  - Duplicates dropped: {stats.duplicate_dropped}")
        logger.info(f"  - Duplicate rate: {stats.duplicate_rate:.2%}")
        logger.info(f"  - Uptime: {stats.uptime_seconds:.2f}s")
    
    logger.info("=" * 60)
    logger.info("Shutdown complete")
    logger.info("=" * 60)


def main():
    """Main function untuk menjalankan aplikasi"""
    # Initialize components
    dedup_store = DedupStore(db_path="data/dedup.db")
    logger.info(f"✓ Dedup store initialized: {dedup_store.get_total_processed()} events in store")
    
    processor = EventProcessor(dedup_store)
    
    # Create FastAPI app
    app = create_app(processor)
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def on_startup():
        await startup_event(processor)
    
    @app.on_event("shutdown")
    async def on_shutdown():
        await shutdown_event(processor)
    
    # Configuration
    host = "0.0.0.0"
    port = 8080
    
    logger.info(f"Starting server at http://{host}:{port}")
    
    # Run uvicorn server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
