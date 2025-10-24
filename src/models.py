"""
Data models untuk event dan statistik sistem
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class Event(BaseModel):
    """
    Model event untuk Pub-Sub log aggregator
    
    Attributes:
        topic: Nama topic/channel untuk event
        event_id: Identifier unik untuk event (collision-resistant)
        timestamp: Waktu event dalam format ISO8601
        source: Sumber event (aplikasi/service yang mengirim)
        payload: Data payload event (flexible JSON)
    """
    topic: str = Field(..., min_length=1, max_length=255, description="Topic name")
    event_id: str = Field(..., min_length=1, max_length=255, description="Unique event identifier")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    source: str = Field(..., min_length=1, max_length=255, description="Event source")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validasi format timestamp ISO8601"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid ISO8601 timestamp: {v}")
        return v
    
    @field_validator('event_id')
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validasi event_id tidak kosong"""
        if not v or v.strip() == "":
            raise ValueError("event_id cannot be empty")
        return v
    
    def get_dedup_key(self) -> str:
        """
        Generate deduplication key berdasarkan (topic, event_id)
        
        Returns:
            String key untuk deduplication
        """
        return f"{self.topic}:{self.event_id}"
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "user-activity",
                "event_id": str(uuid.uuid4()),
                "timestamp": "2025-10-22T10:00:00Z",
                "source": "web-app",
                "payload": {
                    "user_id": "123",
                    "action": "login"
                }
            }
        }


class PublishResponse(BaseModel):
    """Response model untuk endpoint /publish"""
    status: str = Field(..., description="Status hasil publish")
    received: int = Field(..., description="Jumlah event yang diterima")
    processed: int = Field(..., description="Jumlah event unik yang diproses")
    duplicates: int = Field(..., description="Jumlah duplikasi yang di-drop")
    message: Optional[str] = Field(None, description="Pesan tambahan")


class EventsResponse(BaseModel):
    """Response model untuk endpoint /events"""
    topic: str = Field(..., description="Topic yang di-query")
    count: int = Field(..., description="Jumlah event")
    events: List[Event] = Field(default_factory=list, description="List of events")


class Stats(BaseModel):
    """
    Model statistik sistem untuk observability
    
    Attributes:
        received: Total event yang diterima sejak startup
        unique_processed: Total event unik yang diproses
        duplicate_dropped: Total duplikasi yang di-drop
        topics: List of topics yang pernah diproses
        uptime_seconds: Waktu sistem berjalan dalam detik
        duplicate_rate: Rate duplikasi (0.0 - 1.0)
    """
    received: int = Field(default=0, description="Total events received")
    unique_processed: int = Field(default=0, description="Unique events processed")
    duplicate_dropped: int = Field(default=0, description="Duplicates dropped")
    topics: List[str] = Field(default_factory=list, description="Active topics")
    uptime_seconds: float = Field(default=0.0, description="System uptime")
    duplicate_rate: float = Field(default=0.0, description="Duplicate rate (0.0-1.0)")
    
    def calculate_duplicate_rate(self):
        """Hitung duplicate rate"""
        if self.received > 0:
            self.duplicate_rate = round(self.duplicate_dropped / self.received, 4)
        else:
            self.duplicate_rate = 0.0


class HealthResponse(BaseModel):
    """Response model untuk endpoint /health"""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Current timestamp")
