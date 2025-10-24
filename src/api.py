"""
FastAPI endpoints untuk Pub-Sub Log Aggregator
"""
from fastapi import FastAPI, HTTPException, Query
from typing import Union, List
import logging
from datetime import datetime
from src.models import (
    Event, 
    PublishResponse, 
    EventsResponse, 
    Stats, 
    HealthResponse
)
from src.event_processor import EventProcessor

logger = logging.getLogger(__name__)


def create_app(processor: EventProcessor) -> FastAPI:
    """
    Factory function untuk membuat FastAPI app
    
    Args:
        processor: Instance EventProcessor
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Pub-Sub Log Aggregator",
        description="Idempotent consumer dengan deduplication untuk log aggregation",
        version="1.0.0"
    )
    
    @app.post("/publish", response_model=PublishResponse, status_code=200)
    async def publish_events(events: Union[Event, List[Event]]):
        """
        Publish event(s) ke aggregator
        
        Mendukung single event atau batch events.
        Event yang duplikat (berdasarkan topic + event_id) akan di-drop.
        
        Args:
            events: Single Event atau List of Events
            
        Returns:
            PublishResponse dengan statistik processing
        """
        try:
            # Normalize input ke list
            if isinstance(events, Event):
                event_list = [events]
            else:
                event_list = events
            
            if not event_list:
                raise HTTPException(status_code=400, detail="No events provided")
            
            # Submit events untuk diproses
            received = len(event_list)
            
            # Track duplicates yang sudah ada di dedup store
            duplicates = 0
            processed = 0
            
            for event in event_list:
                if processor.dedup_store.is_duplicate(event):
                    duplicates += 1
                    processor.stats.received += 1
                    processor.stats.duplicate_dropped += 1
                    logger.info(f"Duplicate rejected immediately: {event.get_dedup_key()}")
                else:
                    await processor.submit_event(event)
                    processed += 1
            
            logger.info(
                f"Published {received} events: "
                f"{processed} queued, {duplicates} duplicates rejected"
            )
            
            return PublishResponse(
                status="success",
                received=received,
                processed=processed,
                duplicates=duplicates,
                message=f"Successfully queued {processed} unique events"
            )
            
        except Exception as e:
            logger.error(f"Error publishing events: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @app.get("/events", response_model=EventsResponse)
    async def get_events(
        topic: str = Query(..., description="Topic name to query"),
        limit: int = Query(1000, ge=1, le=10000, description="Maximum events to return")
    ):
        """
        Query events berdasarkan topic
        
        Args:
            topic: Nama topic
            limit: Maksimal jumlah events (default: 1000)
            
        Returns:
            EventsResponse dengan list of events
        """
        try:
            events = processor.get_events_by_topic(topic, limit)
            
            logger.debug(f"Query events for topic '{topic}': {len(events)} events found")
            
            return EventsResponse(
                topic=topic,
                count=len(events),
                events=events
            )
            
        except Exception as e:
            logger.error(f"Error querying events: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @app.get("/stats", response_model=Stats)
    async def get_stats():
        """
        Ambil statistik sistem untuk observability
        
        Returns:
            Stats object dengan metrik real-time
        """
        try:
            stats = processor.get_stats()
            logger.debug(f"Stats queried: {stats.received} received, {stats.unique_processed} processed")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """
        Health check endpoint
        
        Returns:
            HealthResponse dengan status sistem
        """
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    
    @app.get("/")
    async def root():
        """Root endpoint dengan informasi API"""
        return {
            "service": "Pub-Sub Log Aggregator",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "publish": "POST /publish",
                "query": "GET /events?topic=<topic>",
                "stats": "GET /stats",
                "health": "GET /health"
            }
        }
    
    return app
