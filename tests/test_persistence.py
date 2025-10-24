"""
Test persistence setelah restart
"""
import pytest
import tempfile
import os
from src.models import Event
from src.dedup_store import DedupStore
from datetime import datetime


@pytest.fixture
def temp_db_path():
    """Fixture untuk temporary database path"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    yield db_path
    
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_persistence_after_restart(temp_db_path):
    """
    Test: Dedup store persisten setelah restart
    
    Simulasi:
    1. Buat store, process events
    2. Close store
    3. Buat store baru dengan db yang sama
    4. Verify duplikasi masih terdeteksi
    """
    # Phase 1: Initial store
    store1 = DedupStore(db_path=temp_db_path)
    
    events = [
        Event(
            topic="persist-test",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={"index": i}
        )
        for i in range(5)
    ]
    
    # Process events
    for event in events:
        assert not store1.is_duplicate(event)
        store1.mark_processed(event)
    
    assert store1.get_total_processed() == 5
    
    # Simulate restart: create new store instance
    del store1
    
    # Phase 2: New store after "restart"
    store2 = DedupStore(db_path=temp_db_path)
    
    # Verify data persisted
    assert store2.get_total_processed() == 5
    
    # Verify duplicates still detected
    for event in events:
        assert store2.is_duplicate(event), f"Event {event.event_id} should be duplicate"
    
    # New event should not be duplicate
    new_event = Event(
        topic="persist-test",
        event_id="evt-new",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test",
        payload={}
    )
    
    assert not store2.is_duplicate(new_event)
    store2.mark_processed(new_event)
    assert store2.get_total_processed() == 6


def test_topics_persist_after_restart(temp_db_path):
    """Test: Topics list persisten setelah restart"""
    # Phase 1: Initial store
    store1 = DedupStore(db_path=temp_db_path)
    
    topics = ["topic1", "topic2", "topic3"]
    for topic in topics:
        event = Event(
            topic=topic,
            event_id=f"evt-{topic}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={}
        )
        store1.mark_processed(event)
    
    assert len(store1.get_all_topics()) == 3
    
    # Simulate restart
    del store1
    
    # Phase 2: New store
    store2 = DedupStore(db_path=temp_db_path)
    
    # Verify topics persisted
    persisted_topics = store2.get_all_topics()
    assert len(persisted_topics) == 3
    assert set(topics) == persisted_topics


def test_events_query_after_restart(temp_db_path):
    """Test: Events dapat di-query setelah restart"""
    # Phase 1: Initial store
    store1 = DedupStore(db_path=temp_db_path)
    
    events = [
        Event(
            topic="query-persist",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={"index": i}
        )
        for i in range(10)
    ]
    
    for event in events:
        store1.mark_processed(event)
    
    # Simulate restart
    del store1
    
    # Phase 2: New store
    store2 = DedupStore(db_path=temp_db_path)
    
    # Query events
    retrieved = store2.get_events_by_topic("query-persist")
    assert len(retrieved) == 10
    
    # Verify event data intact
    event_ids = {event.event_id for event in retrieved}
    expected_ids = {f"evt-{i}" for i in range(10)}
    assert event_ids == expected_ids


def test_concurrent_access_simulation(temp_db_path):
    """Test: Multiple store instances dapat akses db yang sama"""
    # Buat dua store instances dengan db yang sama
    store1 = DedupStore(db_path=temp_db_path)
    store2 = DedupStore(db_path=temp_db_path)
    
    # Store1 process event
    event = Event(
        topic="concurrent",
        event_id="evt-001",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test",
        payload={}
    )
    
    store1.mark_processed(event)
    
    # Store2 should see the event as duplicate
    assert store2.is_duplicate(event)
    
    # Both should have same count
    assert store1.get_total_processed() == store2.get_total_processed()
