# UTS Sistem Terdistribusi - Pub-Sub Log Aggregator
[SHOW INFO SLIDE]
Nama: [NIKO AFANDI SAPUTRO]
NIM: [11221039]
GitHub: [LINK]
Video: [LINK]

## Deskripsi
Layanan Pub-Sub log aggregator dengan idempotent consumer dan deduplication. Sistem ini menerima event/log dari publisher dan memproses melalui subscriber yang bersifat idempotent, serta melakukan deduplication terhadap duplikasi event.

## Fitur Utama
- ✅ Idempotent consumer (tidak memproses ulang event yang sama)
- ✅ Deduplication berdasarkan (topic, event_id)
- ✅ Persistent dedup store menggunakan SQLite
- ✅ At-least-once delivery semantics
- ✅ Toleransi terhadap crash dan restart
- ✅ RESTful API untuk publish dan query events
- ✅ Observability melalui stats endpoint
- ✅ Unit tests dengan pytest

## Teknologi
- Python 3.11
- FastAPI (Web framework)
- SQLite (Persistent dedup store)
- Docker
- Pytest (Testing)

## Struktur Direktori
```
uts/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point aplikasi
│   ├── models.py               # Data models (Event, Stats)
│   ├── dedup_store.py          # Deduplication store dengan SQLite
│   ├── event_processor.py      # Event consumer & processor
│   └── api.py                  # FastAPI endpoints
├── tests/
│   ├── __init__.py
│   ├── test_dedup.py
│   ├── test_api.py
│   ├── test_persistence.py
│   └── test_performance.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml          # Bonus
├── report.md
└── README.md
```

## Cara Menjalankan

### Prasyarat
- Docker terinstall
- Python 3.11+ (untuk development/testing lokal)

### Build Docker Image
```powershell
docker build -t uts-aggregator .
```

### Run Container
```powershell
docker run -p 8080:8080 -v ${PWD}/data:/app/data uts-aggregator
```

### Run dengan Docker Compose (Bonus)
```powershell
docker-compose up --build
```

### Testing Lokal (Tanpa Docker)
```powershell
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run aplikasi
python -m src.main
```

## API Endpoints

### 1. Publish Event(s)
**POST** `/publish`

**Body (Single Event):**
```json
{
  "topic": "user-activity",
  "event_id": "evt-001",
  "timestamp": "2025-10-22T10:00:00Z",
  "source": "web-app",
  "payload": {
    "user_id": "123",
    "action": "login"
  }
}
```

**Body (Batch Events):**
```json
[
  {
    "topic": "user-activity",
    "event_id": "evt-001",
    "timestamp": "2025-10-22T10:00:00Z",
    "source": "web-app",
    "payload": {"user_id": "123", "action": "login"}
  },
  {
    "topic": "user-activity",
    "event_id": "evt-002",
    "timestamp": "2025-10-22T10:01:00Z",
    "source": "web-app",
    "payload": {"user_id": "456", "action": "logout"}
  }
]
```

**Response:**
```json
{
  "status": "success",
  "received": 2,
  "processed": 2,
  "duplicates": 0
}
```

### 2. Get Events by Topic
**GET** `/events?topic=user-activity`

**Response:**
```json
{
  "topic": "user-activity",
  "count": 2,
  "events": [
    {
      "topic": "user-activity",
      "event_id": "evt-001",
      "timestamp": "2025-10-22T10:00:00Z",
      "source": "web-app",
      "payload": {"user_id": "123", "action": "login"}
    }
  ]
}
```

### 3. Get Statistics
**GET** `/stats`

**Response:**
```json
{
  "received": 5000,
  "unique_processed": 4000,
  "duplicate_dropped": 1000,
  "topics": ["user-activity", "system-logs"],
  "uptime_seconds": 3600.5,
  "duplicate_rate": 0.20
}
```

### 4. Health Check
**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-22T10:00:00Z"
}
```

## Contoh Penggunaan

### Simulasi Duplicate Delivery (At-Least-Once)
```powershell
# Kirim event pertama kali
curl -X POST http://localhost:8080/publish `
  -H "Content-Type: application/json" `
  -d '{\"topic\":\"test\",\"event_id\":\"evt-001\",\"timestamp\":\"2025-10-22T10:00:00Z\",\"source\":\"test\",\"payload\":{}}'

# Kirim duplikat (akan di-drop)
curl -X POST http://localhost:8080/publish `
  -H "Content-Type: application/json" `
  -d '{\"topic\":\"test\",\"event_id\":\"evt-001\",\"timestamp\":\"2025-10-22T10:00:00Z\",\"source\":\"test\",\"payload\":{}}'

# Check stats
curl http://localhost:8080/stats
```

## Asumsi & Design Decisions

### 1. Idempotency Key
- Menggunakan kombinasi `(topic, event_id)` sebagai key unik
- `event_id` harus unik per topic, collision-resistant (UUID v4 recommended)

### 2. Deduplication Store
- SQLite embedded untuk persistensi
- Schema: `(topic, event_id, timestamp, processed_at)`
- Index pada `(topic, event_id)` untuk lookup cepat

### 3. Ordering
- Tidak menerapkan total ordering (tidak diperlukan untuk log aggregator)
- Event diproses berdasarkan arrival order
- Timestamp event disimpan untuk audit trail

### 4. Failure Handling
- Dedup store persisten mencegah reprocessing setelah restart
- Logging duplikasi untuk monitoring
- Graceful shutdown untuk memastikan semua event terproses

### 5. Performance
- Async processing dengan asyncio
- Batch insert untuk efisiensi database
- Connection pooling untuk SQLite

## Video Demo
[Link YouTube Demo](https://youtube.com/...)

Durasi: 5-8 menit
- Build dan run container
- Demonstrasi API endpoints
- Simulasi duplikasi dan idempotency
- Restart container & persistensi
- Penjelasan arsitektur

## Laporan
Lihat [report.md](./report.md) untuk:
- Analisis teori (Bab 1-7)
- Keputusan desain
- Analisis performa
- Sitasi buku utama

## Testing
```powershell
# Run all tests
pytest tests/ -v

# Run dengan coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/test_dedup.py -v
```

## Metrik Evaluasi
- **Throughput**: >= 1000 events/second
- **Latency**: < 10ms per event (p95)
- **Duplicate Rate**: Akurat 100% (tidak ada duplikasi terproses)
- **Uptime**: Tahan restart tanpa data loss

## Lisensi
MIT License - UTS Sistem Terdistribusi 2025
