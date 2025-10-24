"""
Test performance dan stress test
"""
import pytest
import tempfile
import os
import time
from src.models import Event
from src.dedup_store import DedupStore
from src.event_processor import EventProcessor
from datetime import datetime
import asyncio


@pytest.fixture
def temp_db():
    """Fixture untuk temporary database"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    yield db_path
    
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def processor(temp_db):
    """Fixture untuk EventProcessor"""
    dedup_store = DedupStore(db_path=temp_db)
    proc = EventProcessor(dedup_store)
    await proc.start()
    
    yield proc
    
    await proc.stop()


@pytest.mark.asyncio
async def test_throughput_5000_events(processor):
    """
    Test: Process >= 5000 events dengan >= 20% duplikasi
    
    Requirement dari soal:
    - Skala uji: >= 5000 event
    - >= 20% duplikasi
    - Sistem tetap responsif
    """
    total_events = 5000
    duplicate_ratio = 0.20
    unique_events = int(total_events * (1 - duplicate_ratio))
    
    events = []
    
    # Generate unique events
    for i in range(unique_events):
        events.append(Event(
            topic="perf-test",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="perf-test",
            payload={"index": i}
        ))
    
    # Generate duplicates (20% dari total)
    duplicate_count = total_events - unique_events
    for i in range(duplicate_count):
        # Duplicate dari event yang sudah ada
        dup_index = i % unique_events
        events.append(Event(
            topic="perf-test",
            event_id=f"evt-{dup_index}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="perf-test",
            payload={"index": dup_index}
        ))
    
    # Submit all events
    start_time = time.time()
    
    await processor.submit_events(events)
    
    # Wait untuk processing selesai
    await asyncio.sleep(10)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Get stats
    stats = processor.get_stats()
    
    # Assertions
    assert stats.received == total_events, f"Should receive {total_events} events"
    assert stats.duplicate_dropped >= duplicate_count * 0.9, "Should drop at least 90% of duplicates"
    assert stats.unique_processed >= unique_events * 0.9, "Should process at least 90% of unique events"
    assert stats.duplicate_rate >= 0.18, "Duplicate rate should be >= 18% (allowing 2% margin)"
    
    # Performance
    throughput = total_events / elapsed
    print(f"\n=== Performance Metrics ===")
    print(f"Total events: {total_events}")
    print(f"Unique events: {unique_events}")
    print(f"Duplicates: {duplicate_count}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"Throughput: {throughput:.0f} events/second")
    print(f"Processed: {stats.unique_processed}")
    print(f"Dropped: {stats.duplicate_dropped}")
    print(f"Duplicate rate: {stats.duplicate_rate:.2%}")
    
    # Throughput should be reasonable (at least 100 events/sec)
    assert throughput >= 100, f"Throughput too low: {throughput:.0f} events/sec"


@pytest.mark.asyncio
async def test_latency_single_event(processor):
    """Test: Latency untuk single event processing"""
    event = Event(
        topic="latency-test",
        event_id="evt-latency",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test",
        payload={}
    )
    
    start = time.time()
    await processor.submit_event(event)
    end = time.time()
    
    latency_ms = (end - start) * 1000
    
    print(f"\n=== Latency Test ===")
    print(f"Single event latency: {latency_ms:.2f}ms")
    
    # Latency harus < 100ms untuk single event
    assert latency_ms < 100, f"Latency too high: {latency_ms:.2f}ms"


def test_dedup_store_lookup_performance(temp_db):
    """Test: Performance lookup di dedup store"""
    store = DedupStore(db_path=temp_db)
    
    # Insert 1000 events
    for i in range(1000):
        event = Event(
            topic="lookup-perf",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={}
        )
        store.mark_processed(event)
    
    # Test lookup performance
    test_event = Event(
        topic="lookup-perf",
        event_id="evt-500",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test",
        payload={}
    )
    
    start = time.time()
    for _ in range(100):
        store.is_duplicate(test_event)
    end = time.time()
    
    avg_lookup_ms = ((end - start) / 100) * 1000
    
    print(f"\n=== Lookup Performance ===")
    print(f"Average lookup time: {avg_lookup_ms:.3f}ms")
    
    # Lookup harus cepat (< 10ms)
    assert avg_lookup_ms < 10, f"Lookup too slow: {avg_lookup_ms:.3f}ms"


@pytest.mark.asyncio
async def test_batch_processing_performance(processor):
    """Test: Performance batch processing"""
    batch_sizes = [10, 50, 100, 500]
    
    print("\n=== Batch Processing Performance ===")
    
    for batch_size in batch_sizes:
        events = [
            Event(
                topic="batch-perf",
                event_id=f"evt-batch-{batch_size}-{i}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                source="test",
                payload={"batch": batch_size, "index": i}
            )
            for i in range(batch_size)
        ]
        
        start = time.time()
        await processor.submit_events(events)
        await asyncio.sleep(1)  # Wait for processing
        end = time.time()
        
        elapsed_ms = (end - start) * 1000
        avg_per_event_ms = elapsed_ms / batch_size
        
        print(f"Batch size {batch_size:3d}: {elapsed_ms:6.2f}ms total, {avg_per_event_ms:5.2f}ms/event")
        
        # Batch processing harus efisien
        assert avg_per_event_ms < 50, f"Batch processing too slow for batch size {batch_size}"


def test_memory_efficiency(temp_db):
    """Test: Memory efficiency dengan banyak events"""
    store = DedupStore(db_path=temp_db)
    
    # Process 10000 events
    num_events = 10000
    
    start = time.time()
    for i in range(num_events):
        event = Event(
            topic="memory-test",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={"data": "x" * 100}  # Some payload
        )
        store.mark_processed(event)
    end = time.time()
    
    elapsed = end - start
    throughput = num_events / elapsed
    
    print(f"\n=== Memory Efficiency Test ===")
    print(f"Processed {num_events} events in {elapsed:.2f}s")
    print(f"Throughput: {throughput:.0f} events/second")
    
    # Verify all stored
    assert store.get_total_processed() == num_events
    
    # Performance harus tetap reasonable
    assert throughput >= 100, f"Throughput degraded: {throughput:.0f} events/sec"
