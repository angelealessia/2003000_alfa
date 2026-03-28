1. System Overview
The year is 2038. This system is a distributed, fault-tolerant seismic analysis platform designed to monitor ground vibrations in a high-tension geopolitical landscape. The platform ingests real-time data from geographically distributed sensors , redistributes it across replicated processing services , performs frequency-domain analysis (FFT) , and persists detected events in a duplicate-safe manner. A real-time dashboard provides the command center with critical intelligence to initiate defensive protocols.


2. User Stories
AREA 1 — Data ingestion & broker

US1
As a system, I want the Broker to connect to the simulator WebSocket streams so that real-time seismic measurements can be captured.

US2
As a system, I want the Broker to distribute each incoming measurement to multiple processing replicas using a broadcast model.

US3
As a developer, I want the Broker to act only as a routing component without performing data processing.

US4
As a system, I want the Broker to continuously receive sensor data so that the analysis pipeline is always active.

US5
As a developer, I want the Broker to support multiple connected replicas so that the system can scale horizontally.

AREA 2 — Processing & frequency analysis

US6
As a system, I want each processing replica to maintain a sliding window of recent sensor samples in memory.

US7
As a system, I want each replica to apply FFT (Fast Fourier Transform) to identify the dominant frequency of the signal.

US8
As a commander, I want signals with dominant frequency between 0.5 and 3 Hz to be classified as an earthquake.

US9
As a commander, I want signals with dominant frequency between 3 and 8 Hz to be classified as an explosion.

US10
As a commander, I want signals with dominant frequency greater or equal to 8 Hz to be classified as a nuclear-like event.

US11
As a system, I want multiple replicas of the processing service so that the system is scalable and fault tolerant.

US12
As a system, I want each replica to process incoming data independently.

US13
As a developer, I want the processing service to work in real time so that events are detected quickly.

AREA 3 — Persistence & data integrity

US14
As a system, I want detected events to be stored in a shared database so that historical data can be preserved.

US15
As a system, I want the persistence layer to prevent duplicate event storage when multiple replicas process similar inputs.

US16
As an analyst, I want each stored event to include timestamp, sensor ID, dominant frequency, and event type.

US17
As an analyst, I want to retrieve stored events from the database.

US18
As a developer, I want the database to be shared between replicas so that all events are stored in one place.

AREA 4 — Fault tolerance

US19
As a system, I want processing replicas to be able to shut down when receiving a shutdown command from the control stream.

US20
As a commander, I want the system to continue operating even if one or more replicas fail.

US21
As a system administrator, I want the architecture to avoid a single point of failure in the processing layer.

AREA 5 — Dashboard & visualization

US22
As an operator, I want a dashboard to visualize detected seismic events in real time.

US23
As an analyst, I want to see historical events stored in the database.

US24
As a user, I want to filter events by event type so that I can focus on specific threats.

US25
As a user, I want the dashboard to update automatically when new events are detected.

3. Standard Event Schema
Incoming data from the simulator:

sensor_id: Unique identifier of the seismic device.

timestamp: UTC timestamp of the measurement.

value: Ground vibration intensity measured in mm/s.

4. Rule Model
Events are classified based on the dominant frequency f:

Earthquake: 0.5≤f<3.0 Hz.

Conventional Explosion: 3.0≤f<8.0 Hz.

Nuclear-like event: f≥8.0 Hz.

## Standard Event Schema
The system uses a unified JSON format for measurements forwarded by the Broker to the Processing replicas:

| Field | Type | Description |
| :--- | :--- | :--- |
| `sensor_id` | String | [cite_start]Unique identifier of the source sensor  |
| `timestamp` | String (ISO8601) | [cite_start]UTC time of the measurement [cite: 47] |
| `value` | Float | [cite_start]Ground vibration intensity in mm/s [cite: 47] |
| `unit` | String | [cite_start]Measurement unit (fixed to "mm/s") [cite: 47] |

## Rule Model for Classification
[cite_start]Events are classified based on the dominant frequency ($f$) identified via FFT[cite: 86, 89]:
* [cite_start]**Earthquake**: $0.5 \le f < 3.0$ Hz [cite: 90]
* [cite_start]**Conventional Explosion**: $3.0 \le f < 8.0$ Hz [cite: 91]
* [cite_start]**Nuclear-like event**: $f \ge 8.0$ Hz [cite: 92]