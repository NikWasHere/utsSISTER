"""
Event Processor - Consumer yang memproses event secara asynchronous
dengan idempotency dan deduplication
"""
import asyncio
import logging
from typing import List
from datetime import datetime
from src.models import Event, Stats
from src.dedup_store import DedupStore

logger = logging.getLogger(__name__)


class EventProcessor:
    """
    Idempotent event processor dengan deduplication
    
    Memproses event dari internal queue dan memastikan setiap event
    hanya diproses sekali (idempotency) menggunakan dedup store.
    """
    
    def __init__(self, dedup_store: DedupStore):
        """
        Inisialisasi event processor
        
        Args:
            dedup_store: Instance DedupStore untuk deduplication
        """
        self.dedup_store = dedup_store
        self.queue: asyncio.Queue[Event] = asyncio.Queue()
        self.stats = Stats()
        self.start_time = datetime.utcnow()
        self.is_running = False
        self._processor_task = None
        
        logger.info("EventProcessor initialized")
    
    async def start(self):
        """Start background processing task"""
        if not self.is_running:
            self.is_running = True
            self._processor_task = asyncio.create_task(self._process_events())
            logger.info("EventProcessor started")
    
    async def stop(self):
        """Stop background processing task"""
        if self.is_running:
            self.is_running = False
            if self._processor_task:
                await self._processor_task
            logger.info("EventProcessor stopped")
    
    async def submit_event(self, event: Event) -> dict:
        """
        Submit single event untuk diproses
        
        Args:
            event: Event object
            
        Returns:
            Dict dengan status processing
        """
        self.stats.received += 1
        await self.queue.put(event)
        return {"status": "queued", "event_id": event.event_id}
    
    async def submit_events(self, events: List[Event]) -> dict:
        """
        Submit batch events untuk diproses
        
        Args:
            events: List of Event objects
            
        Returns:
            Dict dengan statistik processing
        """
        received = len(events)
        self.stats.received += received
        
        for event in events:
            await self.queue.put(event)
        
        logger.info(f"Queued {received} events for processing")
        return {
            "status": "queued",
            "received": received
        }
    
    async def _process_events(self):
        """
        Background task untuk memproses event dari queue
        
        Menerapkan idempotency: check duplikasi sebelum processing
        """
        logger.info("Event processing loop started")
        
        while self.is_running:
            try:
                # Ambil event dari queue dengan timeout
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Check duplikasi
                if self.dedup_store.is_duplicate(event):
                    self.stats.duplicate_dropped += 1
                    logger.info(
                        f"Duplicate dropped: {event.get_dedup_key()} "
                        f"(total duplicates: {self.stats.duplicate_dropped})"
                    )
                    continue
                
                # Proses event (idempotent)
                await self._process_single_event(event)
                
                # Mark sebagai processed di dedup store
                if self.dedup_store.mark_processed(event):
                    self.stats.unique_processed += 1
                    logger.debug(
                        f"Event processed: {event.get_dedup_key()} "
                        f"(total processed: {self.stats.unique_processed})"
                    )
                else:
                    # Race condition: event sudah dimark oleh thread lain
                    self.stats.duplicate_dropped += 1
                    logger.warning(f"Race condition detected for: {event.get_dedup_key()}")
                
            except asyncio.TimeoutError:
                # Timeout normal, lanjutkan loop
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
        
        logger.info("Event processing loop stopped")
    
    async def _process_single_event(self, event: Event):
        """
        Proses single event (business logic)
        
        Di sini bisa ditambahkan logic seperti:
        - Transformasi data
        - Aggregation
        - Forwarding ke downstream services
        - Etc.
        
        Args:
            event: Event object untuk diproses
        """
        # Simulasi processing time
        await asyncio.sleep(0.001)
        
        # Log event untuk audit trail
        logger.debug(
            f"Processing event: topic={event.topic}, "
            f"event_id={event.event_id}, source={event.source}"
        )
        
        # Business logic di sini...
        # Untuk aggregator, kita hanya menyimpan event
    
    def get_stats(self) -> Stats:
        """
        Ambil statistik real-time
        
        Returns:
            Stats object dengan metrik terkini
        """
        # Update uptime
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        self.stats.uptime_seconds = round(uptime, 2)
        
        # Update topics
        self.stats.topics = list(self.dedup_store.get_all_topics())
        
        # Calculate duplicate rate
        self.stats.calculate_duplicate_rate()
        
        return self.stats
    
    def get_events_by_topic(self, topic: str, limit: int = 1000) -> List[Event]:
        """
        Ambil events berdasarkan topic
        
        Args:
            topic: Nama topic
            limit: Maksimal events yang dikembalikan
            
        Returns:
            List of Event objects
        """
        return self.dedup_store.get_events_by_topic(topic, limit)
