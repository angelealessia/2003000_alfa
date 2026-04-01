# Student_doc.md — Seismic Intelligence Platform

## Group Information

- **Course:** Laboratory of Advanced Programming 2025/2026
- **Exam:** Hackathon — March 28, 2026
- **Group size:** 4 students

---

## System Description

**Seismic CMD** is a fault-tolerant, distributed platform for real-time seismic signal analysis.
It ingests measurements from geographically distributed sensors, applies frequency-domain analysis
via FFT, classifies detected events, and exposes a live dashboard to command center operators.

The system is designed to remain operational even under partial infrastructure failure: all
processing replicas receive the full data stream, and the gateway automatically routes around
failed replicas.

---

## Services

### 1. Broker (`source/broker/`)

- **Language/Framework:** Python 3.11 + FastAPI + websockets + httpx
- **Port:** 8000 (exposed to host)
- **Role:** Fan-out component hosted in the neutral region. Performs **no** data transformation or analysis.
- **Responsibilities:**
  - Discovers sensors at startup via `GET /api/devices/` on the simulator.
  - Maintains persistent WebSocket connections to each sensor.
  - Forwards each measurement to **all** processing replicas via HTTP `POST /ingest`.
  - Fan-out uses `asyncio.gather(..., return_exceptions=True)` so a failed replica never blocks distribution to the others.
  - Reconnects to sensors on connection failure (exponential backoff, 2 s delay).
  - Exposes `/ws/raw` for optional raw measurement streaming to external consumers.

### 2. Processing Service (`source/processing/`)

- **Language/Framework:** Python 3.11 + FastAPI + NumPy + asyncpg
- **Port:** 8001 (internal only — **not** exposed to host)
- **Replicas:** 3 (`processing-1`, `processing-2`, `processing-3`)
- **Responsibilities:**
  - Maintains an in-memory sliding window (`deque`, `maxlen = SAMPLING_RATE × WINDOW_SECONDS`) per sensor.
  - FFT analysis is triggered only after at least **20 samples** have been buffered for a given sensor (early-buffering guard).
  - When sufficient data is present, applies `numpy.fft.rfft` to extract frequency components.
  - Identifies the dominant frequency (highest magnitude, DC component excluded).
  - Classifies the event and persists it to PostgreSQL using `ON CONFLICT DO NOTHING` for idempotency.
  - Applies a per-sensor **cooldown** (`EVENT_COOLDOWN_SECONDS`, default `1 s`) to avoid flooding the DB with repeated events from the same sensor.
  - For `EXPLOSION` events, additionally queries the shared DB to check whether another replica already persisted an explosion for the same sensor in the last 5 seconds, skipping the write if so (cross-replica deduplication beyond the `UNIQUE` constraint).
  - Connects to the simulator's `/api/control` SSE stream and calls `sys.exit(0)` on a `SHUTDOWN` command.
  - Exposes `/health` for gateway health checks and `/events` for event queries.

**FFT Parameters:**

| Parameter | Value |
|---|---|
| Sampling rate | 20 Hz |
| Window duration | 10 seconds |
| Window size (samples) | 200 |
| Frequency resolution | 0.1 Hz |
| Dominant frequency | `argmax` of `rfft` magnitude (DC index 0 excluded) |

### 3. Gateway (`source/gateway/`)

- **Language/Framework:** Python 3.11 + FastAPI + httpx
- **Port:** 8002 (exposed to host)
- **Responsibilities:**
  - Performs health checks on all replicas every **2 seconds** (`HEALTH_CHECK_INTERVAL`).
  - Routes `/api/events` queries via round-robin to **healthy** replicas only.
  - Polls events from a healthy replica every **1 second** and pushes batches to SSE subscribers.
  - Exposes `/api/events/stream` (SSE) for real-time event delivery to the dashboard.
  - Exposes `/api/replicas` for replica status monitoring.
  - Sends a `heartbeat` message every 15 seconds to keep SSE connections alive.

### 4. PostgreSQL

- **Image:** `postgres:16-alpine`
- **Schema:** Single `events` table with `UNIQUE (sensor_id, detected_at)` constraint.
- **Deduplication:** `INSERT ... ON CONFLICT DO NOTHING` ensures idempotent writes across all replicas.

### 5. Frontend (`source/frontend/`)

- **Technology:** Vanilla HTML5 / CSS3 / JavaScript + Chart.js
- **Served by:** Nginx (Alpine)
- **Port:** 3000 (exposed to host)
- **Pages:**
  - **`index.html`** — Real-time dashboard: SSE stream, frequency bar chart (last 50 events), event feed with type/region/sensor filters, replica status panel, nuclear alert banner, system activity log, counters (TOTAL / QUAKE / EXPLO / NUCLEAR).
  - **`storage.html`** — Historical event storage: paginated table (50 rows/page), sortable columns, dropdown filters (Type, Region, Sensor, Replica), dynamic summary counters that update with active filters.
- **Sensor metadata:** The 12 sensors (IDs `sensor-01` … `sensor-12`) with their human-readable names, regions, and categories are defined as a static lookup table in the frontend JavaScript. This data is not fetched from the simulator at runtime.

---

## Fault Tolerance Strategy

1. **Replica failure simulation:** The simulator sends a `SHUTDOWN` command via SSE to exactly one connected replica. That replica calls `sys.exit(0)`. Docker's `restart: unless-stopped` policy restarts it automatically within seconds.
2. **Gateway routing:** The gateway polls each replica's `/health` endpoint every **2 seconds**. Failed replicas are immediately excluded from the round-robin routing set. Requests continue to be served by surviving replicas with no interruption to the frontend.
3. **Broker resilience:** Fan-out is performed with `asyncio.gather(..., return_exceptions=True)`, so a failed or unreachable replica does not block distribution to the others.
4. **Database deduplication (primary):** All replicas process the same data stream. The `UNIQUE (sensor_id, detected_at)` constraint combined with `ON CONFLICT DO NOTHING` guarantees exactly-once persistence regardless of how many replicas attempt to write the same event.
5. **Cross-replica deduplication (secondary — EXPLOSION only):** Before writing an explosion event, the processing replica queries the DB for any explosion on the same sensor in the last 5 seconds. This reduces redundant DB round-trips when multiple replicas detect the same explosion simultaneously.
6. **Per-sensor cooldown:** Each replica enforces a minimum interval of `EVENT_COOLDOWN_SECONDS` (1 s in production configuration) between consecutive event writes for the same sensor, preventing event flooding during sustained signal bursts.

---

## Event Classification Rules

| Event Type | Frequency Range | Notes |
|---|---|---|
| EARTHQUAKE | 0.5 Hz ≤ f < 3.0 Hz | Low-frequency natural seismic |
| EXPLOSION | 3.0 Hz ≤ f < 8.0 Hz | Mid-frequency explosion anomaly |
| NUCLEAR | f ≥ 8.0 Hz | High-frequency critical event |
| *(ignored)* | f < 0.5 Hz | Below detection threshold |

---

## Event Schema

Each detected event persisted in PostgreSQL follows this structure:

| Field | Type | Description |
|---|---|---|
| `id` | BIGSERIAL (PK) | Auto-incremented unique identifier; used by the gateway for incremental polling (`after_id`) |
| `sensor_id` | TEXT | Sensor identifier (e.g., `sensor-01`) |
| `event_type` | TEXT | `EARTHQUAKE` / `EXPLOSION` / `NUCLEAR` |
| `dominant_freq` | FLOAT | Frequency peak detected via FFT (Hz) |
| `detected_at` | TIMESTAMPTZ | Timestamp of the last sample in the analysis window |
| `replica_id` | TEXT | ID of the replica that produced the event (e.g., `processing-1`) |
| `created_at` | TIMESTAMPTZ | Persistence timestamp (default `NOW()`) |

**Deduplication constraint:** `UNIQUE (sensor_id, detected_at)`

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
# Simulator:        http://localhost:8080
# Broker health:    http://localhost:8000/health
# Gateway health:   http://localhost:8002/health
# Events API:       http://localhost:8002/api/events
# Replica status:   http://localhost:8002/api/replicas
# SSE stream:       http://localhost:8002/api/events/stream
```

> **Note:** Processing replicas run on port 8001 internally but do **not** expose any port to the host. They are reachable only within the Docker network (by the broker and the gateway).

---

## Architecture Diagram

See `/booklets/architecture.md`.

---

## Tech Stack Summary

| Component | Technology |
|---|---|
| Broker | Python 3.11, FastAPI, websockets, httpx |
| Processing | Python 3.11, FastAPI, NumPy, asyncpg |
| Gateway | Python 3.11, FastAPI, httpx |
| Database | PostgreSQL 16 (Alpine) |
| Frontend | HTML5, CSS3, Vanilla JS, Chart.js, Nginx |
| Containerization | Docker, Docker Compose |

---

## Assumptions and Design Decisions

- **Broadcast model:** All replicas receive all measurements from all sensors. This maximises fault tolerance: any single surviving replica has the complete data stream and can continue processing without reconfiguration.
- **Sliding window reset on restart:** In-memory windows are lost when a replica is restarted after a `SHUTDOWN` command. This is acceptable because windows refill within `WINDOW_SECONDS` (10 s) of restart, after which analysis resumes normally.
- **Early-buffering guard:** FFT analysis is only triggered after at least 20 samples are available for a sensor (not necessarily a full window). This avoids noisy classifications during the warm-up phase immediately after startup or restart.
- **Gateway as stateless proxy:** The gateway does not store events itself; it proxies queries to a healthy replica and relays SSE data. This avoids state-synchronisation issues and keeps the component lightweight — consistent with the neutral-region constraint.
- **No external message broker:** Per the exam specification, Kafka/RabbitMQ are not used. The custom broker service fulfils the fan-out role entirely.
- **Sensor metadata as static frontend data:** Sensor names and regions are defined as a static lookup table in the frontend JavaScript (12 sensors, `sensor-01` to `sensor-12`). This avoids an additional API call and keeps the frontend self-contained.
- **SSE for real-time delivery:** The gateway exposes a Server-Sent Events stream (`/api/events/stream`) rather than WebSocket, which is simpler to implement and sufficient for unidirectional server-to-client event push. Heartbeat messages (every 15 s) keep the connection alive through proxies and load balancers.
