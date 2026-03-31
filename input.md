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

The simulator generates real-time seismic signals coming from geographically
distributed sensors. Each sensor produces a continuous stream of measurements delivered
through WebSocket connections. 2. Broker The broker acts as a fan-out component. It receives the
incoming measurements from the simulator and redistributes each message to all available
processing replicas. The broker performs no data transformation or analysis. Its only responsibility
is message routing. 3. Processing Replicas (P1, P2, P3) Each processing replica maintains an
in-memory sliding window of recent sensor measurements. When the window is full, the replica
applies Fast Fourier Transform (FFT) to detect the dominant frequency component of the signal.
Based on the dominant frequency, the event is classified into: - Earthquake - Explosion -
Nuclear-like event Each replica processes the same input stream, ensuring fault tolerance in case
one replica fails. 4. PostgreSQL Database All detected events are stored in a shared PostgreSQL
database. The database ensures duplicate-safe persistence using a UNIQUE constraint on
sensor_id and timestamp. This guarantees idempotent writes when multiple replicas process
identical data. 5. Gateway The gateway provides a single entry point for the frontend. It routes
requests to healthy processing replicas using a round-robin strategy. The gateway also exposes a
Server-Sent Events (SSE) endpoint to deliver real-time updates. 6. Frontend Dashboard The
frontend displays detected seismic events in real time. It provides visualization tools such as event
lists, frequency charts, and replica health status. Data Flow Summary Simulator → Broker →
Processing Replicas → Database → Gateway → Frontend This distributed architecture ensures
fault tolerance, scalability, and continuous availability of the system.

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

### Epic 1 — System Status & Monitoring

| ID  | Story | Priority |
|-----|-------|----------|
| US01 | As an Operator, I want to see a live "STREAM ACTIVE" or "RECONNECTING" indicator so that I know if the real-time data feed is successfully connected. | HIGH |
| US02 | As an Operator, I want to view a "Replica Status" panel showing the state (ONLINE/OFFLINE) of each processing node (e.g., processing-1) so that I can monitor system health. | HIGH |
| US03 |As an Operator, I want to see the current system time in UTC at the top of the screen so that I can accurately correlate seismic events with a standard timezone. | MEDIUM |
| US04 | As an Operator, I want to view a continuously updating "System Log" on the right sidebar so that I can track background processes, stream connections, and system errors. | HIGH |
| US05 | As an Operator, I want each entry in the System Log to include a timestamp so that I can track exactly when connection losses or new events occurred. | MEDIUM |

### Epic 2 — Event Summary & Alerts

| ID  | Story | Priority |
|-----|-------|----------|
| US06 | As an Operator, I want to view a "ALL" event counter so that I have a quick overview of all recorded seismic activities in the current session. | HIGH |
| US07 | As an Operator, I want to see a dedicated "QUAKE" counter so that I can monitor the volume of low-frequency natural seismic events. | HIGH |
| US08 | As an Operator, I want to see a dedicated "EXPLO" counter so that I can track the volume of mid-frequency explosion anomalies. | HIGH |
| US09 | As an Operator, I want to see a dedicated "NUCLEAR" counter so that I am instantly aware of the volume of critical, high-frequency events. | HIGH |
| US10 | As an Operator, I want to see a prominent, flashing red alert banner (e.g., "A NUCLEAR-CLASS EVENT DETECTED") at the top of the screen when a critical event occurs to ensure immediate awareness. | HIGH |

### Epic 3 — Data Visualization & Historical Storage

| ID  | Story | Priority |
|-----|-------|----------|
| US11 | As an Operator, I want to view a "Frequency Distribution" bar chart on the main dashboard so that I can visually analyze the immediate patterns of the last 50 events. | HIGH |
| US12 | As an Operator, I want to hover over individual bars in the Frequency Distribution chart so that a tooltip appears showing the specific source sensor and dominant frequency. | MEDIUM |
| US13 | As an Operator, I want to navigate to a dedicated "Event Storage" screen via the sidebar so that I can browse a complete, paginated historical log of all recorded seismic events. | HIGH |
| US14 | As an Operator, I want the Event Storage table to display detailed columns (Type, Sensor, Name, Region, Frequency, Timestamp, and Replica) so that I have full technical context for every historical record. | HIGH |
| US15 | As an Operator, I want to use dedicated dropdown menus (Region, Sensor, Replica) within the Storage view so that I can cross-filter the historical data and isolate specific past anomalies. | HIGH |
| US16 | As an Operator, I want to see dynamic summary counters (Total, EQ, EX, NU) at the top of the Storage view that update automatically based on my active filters so that I instantly know the breakdown of the queried data. | MEDIUM |

### Epic 4 — Dynamic Filtering

| ID  | Story | Priority |
|-----|-------|----------|
| US17 | As an Operator, I want to use quick-filter buttons (ALL, EARTHQUAKE, EXPLOSION, NUCLEAR) so that I can instantly isolate specific types of events across the entire dashboard. | HIGH |
| US18 | As an Operator, I want to use a "REGION" dropdown so that I can filter data by geographical zones (e.g., Aegean Arc, East Africa) to monitor localized activity. | HIGH |
| US19 | As an Operator, I want to use a "SENSOR" dropdown so that I can drill down into the readings of a single specific hardware unit. | HIGH |
| US20 | As an Operator, I want the dashboard to display a clear "NO EVENTS DETECTED" message when my active filters yield no matching data so that I know the system is still responsive | LOW |

### Epic 5 — Real-time Event Feed

| ID  | Story | Priority |
|-----|-------|----------|
| US21 | As an Operator, I want to see a real-time scrolling feed of individual event cards below the filter bar so that I can review the details of recent detections. | HIGH |
| US22 | As an Operator, I want each event card to prominently display the classification type, source sensor name, and deployment location (e.g., sensor-11 — DC West Access Tunnel). | MEDIUM |
| US23 | As an Operator, I want each event card to explicitly state the Region, Category, and the specific Processing Node (e.g., processing-1) that handled the event. | MEDIUM |
| US24 | As an Operator, I want each event card to display the exact Dominant Frequency (FREQ) and the UTC Timestamp of the detection for accurate record-keeping. | HIGH |
| US25 | As an Operator, I want the event feed to dynamically update to only show cards that match my currently selected filters (Type, Category, Region, Sensor) so that I can analyze specific data subsets without clutter. | HIGH |

---

## LoFi Mockups

See `/booklets/mockups.md` for wireframe descriptions.
