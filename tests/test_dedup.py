"""
Test deduplication functionality
"""
import pytest
import tempfile
import os
from src.models import Event
from src.dedup_store import DedupStore
from datetime import datetime


@pytest.fixture
def temp_db():
    """Fixture untuk temporary database"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def dedup_store(temp_db):
    """Fixture untuk DedupStore instance"""
    return DedupStore(db_path=temp_db)


@pytest.fixture
def sample_event():
    """Fixture untuk sample event"""
    return Event(
        topic="test-topic",
        event_id="test-event-001",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test-source",
        payload={"key": "value"}
    )


def test_dedup_store_initialization(dedup_store):
    """Test: DedupStore berhasil diinisialisasi"""
    assert dedup_store is not None
    assert dedup_store.get_total_processed() == 0


def test_first_event_not_duplicate(dedup_store, sample_event):
    """Test: Event pertama kali tidak dianggap duplikasi"""
    assert not dedup_store.is_duplicate(sample_event)


def test_mark_processed_success(dedup_store, sample_event):
    """Test: Event berhasil di-mark sebagai processed"""
    result = dedup_store.mark_processed(sample_event)
    assert result is True
    assert dedup_store.get_total_processed() == 1


def test_duplicate_detection(dedup_store, sample_event):
    """Test: Duplikasi terdeteksi dengan benar"""
    # Mark event pertama
    dedup_store.mark_processed(sample_event)
    
    # Event kedua dengan event_id sama adalah duplikasi
    assert dedup_store.is_duplicate(sample_event)


def test_duplicate_prevention(dedup_store, sample_event):
    """Test: Duplikasi tidak bisa di-mark lagi"""
    # Mark pertama berhasil
    assert dedup_store.mark_processed(sample_event) is True
    
    # Mark kedua gagal (duplikasi)
    assert dedup_store.mark_processed(sample_event) is False
    
    # Total tetap 1
    assert dedup_store.get_total_processed() == 1


def test_different_topics_not_duplicate(dedup_store):
    """Test: Event dengan topic berbeda tidak dianggap duplikasi"""
    event1 = Event(
        topic="topic1",
        event_id="evt-001",
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test",
        payload={}
    )
    
    event2 = Event(
        topic="topic2",
        event_id="evt-001",  # Same event_id but different topic
        timestamp=datetime.utcnow().isoformat() + "Z",
        source="test",
        payload={}
    )
    
    dedup_store.mark_processed(event1)
    assert not dedup_store.is_duplicate(event2)


def test_get_events_by_topic(dedup_store):
    """Test: Query events berdasarkan topic"""
    # Add events dengan berbagai topic
    events = [
        Event(
            topic="topic1",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={"index": i}
        )
        for i in range(5)
    ]
    
    for event in events:
        dedup_store.mark_processed(event)
    
    # Query topic1
    retrieved = dedup_store.get_events_by_topic("topic1")
    assert len(retrieved) == 5
    
    # Query non-existent topic
    retrieved = dedup_store.get_events_by_topic("non-existent")
    assert len(retrieved) == 0


def test_get_all_topics(dedup_store):
    """Test: Ambil semua topics yang pernah diproses"""
    topics = ["topic1", "topic2", "topic3"]
    
    for topic in topics:
        event = Event(
            topic=topic,
            event_id=f"evt-{topic}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={}
        )
        dedup_store.mark_processed(event)
    
    all_topics = dedup_store.get_all_topics()
    assert len(all_topics) == 3
    assert set(topics) == all_topics


def test_dedup_key_format(sample_event):
    """Test: Format dedup key sesuai spec (topic:event_id)"""
    key = sample_event.get_dedup_key()
    assert key == f"{sample_event.topic}:{sample_event.event_id}"
    assert ":" in key


def test_batch_processing(dedup_store):
    """Test: Batch processing dengan duplikasi"""
    events = []
    
    # 10 event unik
    for i in range(10):
        events.append(Event(
            topic="batch",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={"index": i}
        ))
    
    # 5 duplikasi
    for i in range(5):
        events.append(Event(
            topic="batch",
            event_id=f"evt-{i}",  # Duplicate
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="test",
            payload={"index": i}
        ))
    
    # Process all
    unique_count = 0
    duplicate_count = 0
    
    for event in events:
        if not dedup_store.is_duplicate(event):
            if dedup_store.mark_processed(event):
                unique_count += 1
        else:
            duplicate_count += 1
    
    assert unique_count == 10
    assert duplicate_count == 5
    assert dedup_store.get_total_processed() == 10
