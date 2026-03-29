# input.md — Seismic Intelligence Platform

## System Overview

A fault-tolerant, distributed seismic analysis platform designed to provide
continuous intelligence to a command center even under partial system failure.

The system ingests real-time seismic sensor data, performs frequency-domain
analysis (FFT) to classify events, persists results in a shared database,
and exposes a real-time dashboard to operators.

---

## Architecture Summary

```
[Seismic Simulator]
       │  WebSocket (per sensor)
       ▼
    [BROKER]           ← neutral region, fan-out only, no processing
    /   |   \
   ▼    ▼    ▼
[P-1][P-2][P-3]       ← processing replicas (subject to failure)
    \   |   /
       ▼
  [PostgreSQL]         ← shared persistence, deduplication via UNIQUE
       │
   [GATEWAY]           ← health-check routing, SSE to frontend
       │
  [FRONTEND]           ← real-time dashboard
```

---

## Standard Event Schema

Events detected by a processing replica are stored in the `events` table:

```json
{
  "id":            1,
  "sensor_id":     "sensor-abc-123",
  "event_type":    "EARTHQUAKE",
  "dominant_freq": 1.42,
  "detected_at":   "2038-03-15T14:22:00Z",
  "replica_id":    "processing-1",
  "created_at":    "2038-03-15T14:22:00.123Z"
}
```

### Event Classification Rules

| Event Type  | Frequency Range         |
|-------------|------------------------|
| EARTHQUAKE  | 0.5 Hz ≤ f < 3.0 Hz   |
| EXPLOSION   | 3.0 Hz ≤ f < 8.0 Hz   |
| NUCLEAR     | f ≥ 8.0 Hz             |
| (ignored)   | f < 0.5 Hz             |

---

## User Stories

### Epic 1 — Data Ingestion

| ID  | Story | Priority |
|-----|-------|----------|
| US01 | As the system, I want to discover available sensors at startup so I can subscribe to all active streams. | HIGH |
| US02 | As the system, I want the broker to maintain persistent WebSocket connections to sensors and reconnect on failure. | HIGH |
| US03 | As the system, I want each sensor measurement to be forwarded to all active processing replicas within 500ms. | HIGH |
| US04 | As the system, I want the broker to not perform any data processing, only routing. | HIGH |
| US05 | As the system, I want the broker to recover gracefully if a replica is temporarily unavailable. | MEDIUM |

### Epic 2 — Processing & Analysis

| ID  | Story | Priority |
|-----|-------|----------|
| US06 | As the system, I want each replica to maintain an in-memory sliding window of the last N samples per sensor. | HIGH |
| US07 | As the system, I want each replica to apply FFT to the sliding window when full to extract frequency components. | HIGH |
| US08 | As the system, I want each replica to identify the dominant frequency component from FFT output. | HIGH |
| US09 | As the system, I want to classify detected events into EARTHQUAKE, EXPLOSION, or NUCLEAR based on dominant frequency. | HIGH |
| US10 | As the system, I want events below 0.5 Hz to be ignored as background noise. | MEDIUM |

### Epic 3 — Fault Tolerance

| ID  | Story | Priority |
|-----|-------|----------|
| US11 | As the system, I want each replica to connect to the simulator control stream (SSE) and receive shutdown commands. | HIGH |
| US12 | As the system, I want a replica to terminate itself immediately upon receiving a SHUTDOWN command. | HIGH |
| US13 | As the system, I want terminated replicas to restart automatically via Docker's restart policy. | HIGH |
| US14 | As the gateway, I want to perform periodic health checks on all replicas and mark unavailable ones as offline. | HIGH |
| US15 | As the gateway, I want to route requests only to healthy replicas (round-robin over healthy set). | HIGH |
| US16 | As the system, I want overall operation to continue uninterrupted when up to N-1 replicas have failed. | HIGH |

### Epic 4 — Persistence

| ID  | Story | Priority |
|-----|-------|----------|
| US17 | As the system, I want detected events to be stored in a shared PostgreSQL database. | HIGH |
| US18 | As the system, I want duplicate events (same sensor_id + detected_at) to be silently ignored (idempotent insert). | HIGH |
| US19 | As an operator, I want to query historical events filtered by sensor or event type. | MEDIUM |
| US20 | As the system, I want the database schema to be created automatically at startup. | MEDIUM |

### Epic 5 — Dashboard & API

| ID  | Story | Priority |
|-----|-------|----------|
| US21 | As an operator, I want to see a real-time feed of detected events on the dashboard. | HIGH |
| US22 | As an operator, I want events to appear on the dashboard within seconds of detection. | HIGH |
| US23 | As an operator, I want to filter events by type (EARTHQUAKE / EXPLOSION / NUCLEAR). | MEDIUM |
| US24 | As an operator, I want to see a frequency distribution chart of the last 50 events. | MEDIUM |
| US25 | As an operator, I want to see the live status (online/offline) of all processing replicas. | MEDIUM |

---

## LoFi Mockups

See `/booklets/mockups.md` for wireframe descriptions.
