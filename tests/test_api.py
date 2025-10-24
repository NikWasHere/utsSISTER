"""
Test API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.api import create_app
from src.dedup_store import DedupStore
from src.event_processor import EventProcessor
import tempfile
import os
from datetime import datetime


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


@pytest.fixture
def client(processor):
    """Fixture untuk test client"""
    app = create_app(processor)
    return TestClient(app)


def test_root_endpoint(client):
    """Test: Root endpoint mengembalikan informasi API"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Pub-Sub Log Aggregator"
    assert "endpoints" in data


def test_health_endpoint(client):
    """Test: Health endpoint mengembalikan status healthy"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_publish_single_event(client):
    """Test: Publish single event berhasil"""
    event = {
        "topic": "test",
        "event_id": "evt-001",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "test",
        "payload": {"key": "value"}
    }
    
    response = client.post("/publish", json=event)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["received"] == 1
    assert data["processed"] >= 0


def test_publish_batch_events(client):
    """Test: Publish batch events berhasil"""
    events = [
        {
            "topic": "test",
            "event_id": f"evt-{i}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "test",
            "payload": {"index": i}
        }
        for i in range(5)
    ]
    
    response = client.post("/publish", json=events)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["received"] == 5


def test_publish_duplicate_rejected(client):
    """Test: Event duplikat ditolak"""
    event = {
        "topic": "test",
        "event_id": "evt-duplicate",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "test",
        "payload": {}
    }
    
    # Publish pertama kali
    response1 = client.post("/publish", json=event)
    assert response1.status_code == 200
    
    # Publish duplikat
    response2 = client.post("/publish", json=event)
    assert response2.status_code == 200
    data = response2.json()
    assert data["duplicates"] >= 1


def test_get_events_by_topic(client):
    """Test: Query events berdasarkan topic"""
    # Publish beberapa events
    events = [
        {
            "topic": "query-test",
            "event_id": f"evt-{i}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "test",
            "payload": {"index": i}
        }
        for i in range(3)
    ]
    
    for event in events:
        client.post("/publish", json=event)
    
    # Query events
    response = client.get("/events?topic=query-test")
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "query-test"
    assert "events" in data
    assert "count" in data


def test_get_events_invalid_topic(client):
    """Test: Query dengan topic yang tidak ada"""
    response = client.get("/events?topic=non-existent")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert len(data["events"]) == 0


def test_get_stats(client):
    """Test: Stats endpoint mengembalikan metrik"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "received" in data
    assert "unique_processed" in data
    assert "duplicate_dropped" in data
    assert "topics" in data
    assert "uptime_seconds" in data
    assert "duplicate_rate" in data


def test_invalid_event_schema(client):
    """Test: Event dengan schema invalid ditolak"""
    invalid_event = {
        "topic": "test",
        # Missing event_id
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "test"
    }
    
    response = client.post("/publish", json=invalid_event)
    assert response.status_code == 422  # Validation error


def test_empty_event_list(client):
    """Test: Empty event list ditolak"""
    response = client.post("/publish", json=[])
    assert response.status_code == 400
