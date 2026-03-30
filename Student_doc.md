# Student_doc.md — Seismic Intelligence Platform

## Group Information

- **Course:** Laboratory of Advanced Programming 2025/2026
- **Exam:** Hackathon — March 28, 2026
- **Group size:** 4 students

---

## System Description

The Seismic Intelligence Platform is a distributed, fault-tolerant system for
real-time seismic signal analysis. It ingests measurements from geographically
distributed sensors, applies frequency-domain analysis, classifies detected
events, and exposes a live dashboard to command center operators.

---

## Services

### 1. Broker (`source/broker/`)

- **Language/Framework:** Python 3.11 + FastAPI
- **Port:** 8000
- **Role:** Fan-out component hosted in the neutral region.
- **Responsibilities:**
  - Discovers sensors from the simulator `/api/devices/` endpoint at startup.
  - Maintains persistent WebSocket connections to each sensor.
  - Forwards each measurement to all processing replicas via HTTP POST `/ingest`.
  - Does **not** perform any data processing.
  - Reconnects to sensors on connection failure (exponential backoff).
  - Exposes `/ws/raw` for raw measurement streaming to optional consumers.

### 2. Processing Service (`source/processing/`)

- **Language/Framework:** Python 3.11 + FastAPI + NumPy + asyncpg
- **Port:** 8001 (per replica)
- **Replicas:** 3 (`processing-1`, `processing-2`, `processing-3`)
- **Responsibilities:**
  - Maintains an in-memory sliding window (deque) per sensor (`WINDOW_SIZE = SAMPLING_RATE × WINDOW_SECONDS`).
  - When the window is full, applies `numpy.fft.rfft` to extract frequency components.
  - Identifies the dominant frequency (highest magnitude, excluding DC component).
  - Classifies the event and persists it to PostgreSQL using `ON CONFLICT DO NOTHING` for idempotency.
  - Connects to the simulator's `/api/control` SSE stream and terminates on `SHUTDOWN` command.
  - Exposes `/health` for gateway health checks and `/events` for event queries.

**FFT Parameters:**
- Window size: 200 samples (20 Hz × 10 seconds)
- Frequency resolution: 0.1 Hz
- Dominant frequency: argmax of rfft magnitude (DC excluded)

### 3. Gateway (`source/gateway/`)

- **Language/Framework:** Python 3.11 + FastAPI
- **Port:** 8002
- **Responsibilities:**
  - Performs health checks on all replicas every 5 seconds.
  - Routes `/api/events` queries via round-robin to healthy replicas.
  - Polls events from a healthy replica every 2 seconds and pushes to SSE subscribers.
  - Exposes `/api/events/stream` (SSE) for real-time event delivery to the dashboard.
  - Exposes `/api/replicas` for replica status monitoring.

### 4. PostgreSQL

- **Image:** `postgres:16-alpine`
- **Schema:** Single `events` table with `UNIQUE (sensor_id, detected_at)` constraint.
- **Deduplication:** `INSERT ... ON CONFLICT DO NOTHING` ensures idempotent writes.

### 5. Frontend (`source/frontend/`)

- **Technology:** Vanilla HTML/CSS/JavaScript + Chart.js
- **Served by:** Nginx (Alpine)
- **Port:** 3000
- **Features:**
  - SSE connection to gateway for real-time events.
  - Bar chart of frequency distribution (last 50 events).
  - Event feed with filtering by type.
  - Replica status panel (live health check results).
  - Nuclear event alert banner.
  - System activity log.

---

## Fault Tolerance Strategy

1. **Replica failure:** The simulator sends `SHUTDOWN` via SSE to exactly one connected replica. That replica calls `sys.exit(0)`. Docker's `restart: unless-stopped` policy restarts it automatically.
2. **Gateway routing:** The gateway polls replica `/health` every 5 seconds. Failed replicas are excluded from the routing set. Requests continue to be served by surviving replicas.
3. **Broker resilience:** The broker fires fan-out requests with `gather(..., return_exceptions=True)`, so a failed replica does not block distribution to others.
4. **Database deduplication:** All replicas process the same data stream. The `UNIQUE (sensor_id, detected_at)` constraint and `ON CONFLICT DO NOTHING` ensure exactly-once persistence.

---

## How to Run

```bash
# 1. Load the simulator image
docker load -i seismic-signal-simulator-oci.tar

# 2. Start the full system
cd source
docker compose up --build

# 3. Open the dashboard
open http://localhost:3000

# 4. API endpoints
# Gateway health:   http://localhost:8002/health
# Events API:       http://localhost:8002/api/events
# Replica status:   http://localhost:8002/api/replicas
# SSE stream:       http://localhost:8002/api/events/stream
```

---

## Architecture Diagram

See `/booklets/architecture.md`.

---

## Tech Stack Summary

| Component  | Technology                     |
|------------|-------------------------------|
| Broker     | Python 3.11, FastAPI, websockets, httpx |
| Processing | Python 3.11, FastAPI, NumPy, asyncpg    |
| Gateway    | Python 3.11, FastAPI, httpx             |
| Database   | PostgreSQL 16                           |
| Frontend   | HTML5, CSS3, Vanilla JS, Chart.js       |
| Container  | Docker, Docker Compose                  |

---

## Assumptions and Design Decisions

- **Broadcast model:** All replicas receive all measurements. This simplifies fault tolerance since any surviving replica has the full data stream.
- **Sliding window reset on restart:** In-memory windows are lost on replica restart. This is acceptable because the system is designed for continuous streaming — windows refill within `WINDOW_SECONDS` seconds of restart.
- **Gateway as stateless proxy:** The gateway does not store events itself; it proxies queries to a healthy replica. This avoids state synchronization issues.
- **No external message broker:** Per the exam specification, Kafka/RabbitMQ are not used. The custom broker service fulfills the fan-out role.

### Event Schema

Each detected event persisted in PostgreSQL follows the structure:

| field | description |
|------|-------------|
| sensor_id | sensor identifier |
| event_type | EARTHQUAKE / EXPLOSION / NUCLEAR |
| dominant_freq | frequency peak detected via FFT |
| detected_at | timestamp of last sample in window |
| replica_id | replica that produced the event |
| created_at | persistence timestamp |