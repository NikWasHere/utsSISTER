"""
Deduplication Store menggunakan SQLite untuk persistensi
Menyimpan event yang sudah diproses untuk mencegah duplikasi
"""
import sqlite3
import threading
import json
import logging
from datetime import datetime
from typing import Optional, List, Set
from pathlib import Path
from src.models import Event

logger = logging.getLogger(__name__)


class DedupStore:
    """
    Persistent deduplication store menggunakan SQLite
    
    Menyimpan (topic, event_id) yang sudah diproses untuk mencegah
    reprocessing event yang sama, bahkan setelah restart.
    
    Thread-safe dengan menggunakan threading.Lock untuk concurrent access.
    """
    
    def __init__(self, db_path: str = "data/dedup.db"):
        """
        Inisialisasi dedup store
        
        Args:
            db_path: Path ke SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # Buat direktori jika belum ada
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Inisialisasi database
        self._init_db()
        logger.info(f"DedupStore initialized at {db_path}")
    
    def _init_db(self):
        """Inisialisasi schema database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabel untuk menyimpan event yang sudah diproses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    topic TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT,
                    processed_at TEXT NOT NULL,
                    PRIMARY KEY (topic, event_id)
                )
            """)
            
            # Index untuk query cepat
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic 
                ON processed_events(topic)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON processed_events(processed_at)
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
    
    def is_duplicate(self, event: Event) -> bool:
        """
        Check apakah event sudah pernah diproses (duplikasi)
        
        Args:
            event: Event object untuk di-check
            
        Returns:
            True jika event adalah duplikasi, False jika unik
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM processed_events WHERE topic = ? AND event_id = ?",
                    (event.topic, event.event_id)
                )
                result = cursor.fetchone()
                
                is_dup = result is not None
                if is_dup:
                    logger.info(f"Duplicate detected: {event.get_dedup_key()}")
                
                return is_dup
    
    def mark_processed(self, event: Event) -> bool:
        """
        Mark event sebagai sudah diproses
        
        Args:
            event: Event object yang sudah diproses
            
        Returns:
            True jika berhasil disimpan, False jika duplikasi (sudah ada)
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    processed_at = datetime.utcnow().isoformat()
                    
                    cursor.execute("""
                        INSERT INTO processed_events 
                        (topic, event_id, timestamp, source, payload, processed_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        event.topic,
                        event.event_id,
                        event.timestamp,
                        event.source,
                        json.dumps(event.payload),
                        processed_at
                    ))
                    
                    conn.commit()
                    logger.debug(f"Event marked as processed: {event.get_dedup_key()}")
                    return True
                    
            except sqlite3.IntegrityError:
                # Duplikasi (PRIMARY KEY constraint violated)
                logger.warning(f"Attempted to mark duplicate event: {event.get_dedup_key()}")
                return False
    
    def get_events_by_topic(self, topic: str, limit: int = 1000) -> List[Event]:
        """
        Ambil semua event yang sudah diproses untuk topic tertentu
        
        Args:
            topic: Nama topic
            limit: Maksimal jumlah event yang dikembalikan
            
        Returns:
            List of Event objects
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT topic, event_id, timestamp, source, payload
                    FROM processed_events
                    WHERE topic = ?
                    ORDER BY processed_at DESC
                    LIMIT ?
                """, (topic, limit))
                
                events = []
                for row in cursor.fetchall():
                    try:
                        event = Event(
                            topic=row[0],
                            event_id=row[1],
                            timestamp=row[2],
                            source=row[3],
                            payload=json.loads(row[4]) if row[4] else {}
                        )
                        events.append(event)
                    except Exception as e:
                        logger.error(f"Failed to parse event from DB: {e}")
                
                return events
    
    def get_all_topics(self) -> Set[str]:
        """
        Ambil semua topic yang pernah diproses
        
        Returns:
            Set of topic names
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT topic FROM processed_events")
                topics = {row[0] for row in cursor.fetchall()}
                return topics
    
    def get_total_processed(self) -> int:
        """
        Hitung total event yang sudah diproses
        
        Returns:
            Total count of processed events
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM processed_events")
                count = cursor.fetchone()[0]
                return count
    
    def clear(self):
        """Hapus semua data (untuk testing)"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM processed_events")
                conn.commit()
                logger.info("DedupStore cleared")
