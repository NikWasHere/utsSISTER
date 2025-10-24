"""
Script untuk mendemonstrasikan sistem
Simulasi publisher yang mengirim events dengan duplikasi
"""
import requests
import time
import uuid
from datetime import datetime
import random


BASE_URL = "http://localhost:8080"


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def publish_event(topic, event_id, payload):
    """Publish single event"""
    event = {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "demo-publisher",
        "payload": payload
    }
    
    try:
        response = requests.post(f"{BASE_URL}/publish", json=event)
        return response.json()
    except Exception as e:
        print(f"Error publishing event: {e}")
        return None


def get_stats():
    """Get current stats"""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        return response.json()
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None


def get_events(topic):
    """Get events by topic"""
    try:
        response = requests.get(f"{BASE_URL}/events", params={"topic": topic})
        return response.json()
    except Exception as e:
        print(f"Error getting events: {e}")
        return None


def demo_basic_publish():
    """Demo 1: Basic event publishing"""
    print_section("Demo 1: Basic Event Publishing")
    
    print("\n1. Publishing 5 unique events...")
    for i in range(5):
        event_id = str(uuid.uuid4())
        payload = {"user_id": f"user-{i}", "action": "login"}
        
        result = publish_event("user-activity", event_id, payload)
        if result:
            print(f"   Event {i+1}: {result['status']} - {result['processed']} processed")
        
        time.sleep(0.5)
    
    print("\n2. Check stats...")
    stats = get_stats()
    if stats:
        print(f"   Received: {stats['received']}")
        print(f"   Processed: {stats['unique_processed']}")
        print(f"   Duplicates: {stats['duplicate_dropped']}")
        print(f"   Topics: {stats['topics']}")


def demo_duplicate_detection():
    """Demo 2: Duplicate detection"""
    print_section("Demo 2: Duplicate Detection (Idempotency)")
    
    event_id = str(uuid.uuid4())
    topic = "duplicate-test"
    
    print(f"\n1. Publishing same event 3 times (event_id: {event_id[:8]}...)...")
    
    for attempt in range(3):
        payload = {"attempt": attempt + 1, "message": "This is a duplicate test"}
        result = publish_event(topic, event_id, payload)
        
        if result:
            status = "✓ ACCEPTED" if result['processed'] > 0 else "✗ REJECTED (Duplicate)"
            print(f"   Attempt {attempt + 1}: {status}")
            print(f"      - Processed: {result['processed']}, Duplicates: {result['duplicates']}")
        
        time.sleep(0.5)
    
    print("\n2. Verify only 1 event processed...")
    events = get_events(topic)
    if events:
        print(f"   Topic '{topic}' has {events['count']} event(s)")
        if events['count'] == 1:
            print("   ✓ SUCCESS: Idempotency working correctly!")
        else:
            print("   ✗ FAILED: Multiple events detected!")


def demo_at_least_once():
    """Demo 3: At-least-once delivery simulation"""
    print_section("Demo 3: At-Least-Once Delivery Simulation")
    
    print("\n1. Simulating network retry scenario...")
    print("   Publisher sends event, doesn't receive ack, retries...")
    
    event_id = str(uuid.uuid4())
    topic = "at-least-once-test"
    payload = {"order_id": "12345", "amount": 100.00}
    
    # First attempt
    print("\n   First send:")
    result1 = publish_event(topic, event_id, payload)
    if result1:
        print(f"      Status: {result1['status']}")
        print(f"      Processed: {result1['processed']}")
    
    time.sleep(1)
    
    # Retry (simulating timeout and retry)
    print("\n   Retry after timeout:")
    result2 = publish_event(topic, event_id, payload)
    if result2:
        print(f"      Status: {result2['status']}")
        print(f"      Duplicates: {result2['duplicates']}")
    
    print("\n2. Checking final state...")
    events = get_events(topic)
    if events:
        print(f"   Events in system: {events['count']}")
        print("   ✓ Idempotent consumer prevented duplicate processing!")


def demo_batch_processing():
    """Demo 4: Batch processing with duplicates"""
    print_section("Demo 4: Batch Processing with Duplicates")
    
    topic = "batch-test"
    batch_size = 20
    duplicate_ratio = 0.3  # 30% duplicates
    
    print(f"\n1. Preparing batch of {batch_size} events...")
    print(f"   - {int(batch_size * (1 - duplicate_ratio))} unique events")
    print(f"   - {int(batch_size * duplicate_ratio)} duplicates")
    
    events = []
    unique_ids = []
    
    # Generate unique events
    unique_count = int(batch_size * (1 - duplicate_ratio))
    for i in range(unique_count):
        event_id = str(uuid.uuid4())
        unique_ids.append(event_id)
        events.append({
            "topic": topic,
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "batch-publisher",
            "payload": {"index": i}
        })
    
    # Add duplicates
    duplicate_count = batch_size - unique_count
    for i in range(duplicate_count):
        dup_id = random.choice(unique_ids)
        events.append({
            "topic": topic,
            "event_id": dup_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "batch-publisher",
            "payload": {"index": i, "duplicate": True}
        })
    
    print(f"\n2. Publishing batch...")
    try:
        response = requests.post(f"{BASE_URL}/publish", json=events)
        result = response.json()
        
        print(f"   Received: {result['received']}")
        print(f"   Processed: {result['processed']}")
        print(f"   Duplicates: {result['duplicates']}")
        print(f"   Duplicate rate: {result['duplicates']/result['received']*100:.1f}%")
        
    except Exception as e:
        print(f"   Error: {e}")


def demo_query_events():
    """Demo 5: Query events by topic"""
    print_section("Demo 5: Query Events by Topic")
    
    topic = "query-test"
    
    print(f"\n1. Publishing events to topic '{topic}'...")
    for i in range(5):
        event_id = str(uuid.uuid4())
        payload = {"message": f"Event {i+1}", "value": i * 10}
        publish_event(topic, event_id, payload)
    
    time.sleep(2)  # Wait for processing
    
    print(f"\n2. Querying events for topic '{topic}'...")
    events = get_events(topic)
    
    if events:
        print(f"   Found {events['count']} event(s)")
        for idx, event in enumerate(events['events'][:5], 1):  # Show first 5
            print(f"\n   Event {idx}:")
            print(f"      ID: {event['event_id'][:12]}...")
            print(f"      Timestamp: {event['timestamp']}")
            print(f"      Source: {event['source']}")
            print(f"      Payload: {event['payload']}")


def demo_stress_test():
    """Demo 6: Stress test with many events"""
    print_section("Demo 6: Stress Test (1000 events)")
    
    topic = "stress-test"
    total_events = 1000
    duplicate_ratio = 0.20
    
    print(f"\n1. Generating {total_events} events...")
    print(f"   - Unique: {int(total_events * (1 - duplicate_ratio))}")
    print(f"   - Duplicates: {int(total_events * duplicate_ratio)}")
    
    events = []
    unique_ids = []
    
    # Generate unique events
    unique_count = int(total_events * (1 - duplicate_ratio))
    for i in range(unique_count):
        event_id = str(uuid.uuid4())
        unique_ids.append(event_id)
        events.append({
            "topic": topic,
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "stress-test",
            "payload": {"index": i}
        })
    
    # Add duplicates
    for i in range(total_events - unique_count):
        dup_id = random.choice(unique_ids)
        events.append({
            "topic": topic,
            "event_id": dup_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "stress-test",
            "payload": {"index": i}
        })
    
    print(f"\n2. Publishing batch...")
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/publish", json=events)
        result = response.json()
        
        elapsed = time.time() - start_time
        throughput = total_events / elapsed
        
        print(f"   Status: {result['status']}")
        print(f"   Received: {result['received']}")
        print(f"   Processed: {result['processed']}")
        print(f"   Duplicates: {result['duplicates']}")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Throughput: {throughput:.0f} events/second")
        
    except Exception as e:
        print(f"   Error: {e}")


def demo_final_stats():
    """Show final statistics"""
    print_section("Final Statistics")
    
    stats = get_stats()
    if stats:
        print(f"\n  Total received:      {stats['received']}")
        print(f"  Unique processed:    {stats['unique_processed']}")
        print(f"  Duplicates dropped:  {stats['duplicate_dropped']}")
        print(f"  Duplicate rate:      {stats['duplicate_rate']*100:.2f}%")
        print(f"  Active topics:       {len(stats['topics'])}")
        print(f"  Uptime:              {stats['uptime_seconds']:.2f} seconds")
        print(f"\n  Topics:")
        for topic in stats['topics']:
            print(f"    - {topic}")


def main():
    """Run all demos"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   UTS Sistem Terdistribusi - Demo Script                  ║")
    print("║   Pub-Sub Log Aggregator dengan Idempotency & Dedup       ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("\n✗ Server not responding. Please start the server first:")
            print("  docker run -p 8080:8080 uts-aggregator")
            return
    except:
        print("\n✗ Cannot connect to server at", BASE_URL)
        print("  Please start the server first:")
        print("  docker run -p 8080:8080 uts-aggregator")
        return
    
    print("\n✓ Server is running")
    
    # Run demos
    time.sleep(1)
    
    demo_basic_publish()
    time.sleep(2)
    
    demo_duplicate_detection()
    time.sleep(2)
    
    demo_at_least_once()
    time.sleep(2)
    
    demo_batch_processing()
    time.sleep(2)
    
    demo_query_events()
    time.sleep(2)
    
    demo_stress_test()
    time.sleep(3)
    
    demo_final_stats()
    
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   Demo Complete!                                           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("\n")


if __name__ == "__main__":
    main()
