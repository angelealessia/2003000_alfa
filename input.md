1. System Overview
The year is 2038. This system is a distributed, fault-tolerant seismic analysis platform designed to monitor ground vibrations in a high-tension geopolitical landscape. The platform ingests real-time data from geographically distributed sensors , redistributes it across replicated processing services , performs frequency-domain analysis (FFT) , and persists detected events in a duplicate-safe manner. A real-time dashboard provides the command center with critical intelligence to initiate defensive protocols.


2. User Stories
AREA 1 - Data Ingestion & Distribution (Broker)

As a system operator, I want the Broker to connect to sensor WebSockets so that it can capture incoming real-time measurements.


As a system administrator, I want the Broker to redistribute measurements to multiple processing replicas simultaneously using a broadcast model.


As a security officer, I want the Broker to be hosted in a neutral region, performing only lightweight routing without data processing.

As a developer, I want the Broker to discover available sensors via the /api/devices/ endpoint.

As a system, I want to receive measurements at a default frequency of 20 Hz to ensure high-fidelity signal analysis.

AREA 2 - Processing & Analysis (Replicated Services)

As a military analyst, I want the system to apply Discrete Fourier Transform (DFT) or FFT to identify dominant frequency components.

As a developer, I want each replica to maintain an in-memory sliding window of recent samples for each sensor.

As a commander, I want events with a dominant frequency between 0.5 and 3.0 Hz to be classified as an "Earthquake".

As a commander, I want events with a dominant frequency between 3.0 and 8.0 Hz to be classified as a "Conventional Explosion".

As a commander, I want events with a dominant frequency ≥ 8.0 Hz to be classified as a "Nuclear-like event".

As a developer, I want each processing replica to listen to the SSE control stream to receive system commands.

As a system, I want a replica to terminate immediately (forced shutdown) upon receiving a {"command":"SHUTDOWN"} message.

AREA 3 - Persistence & Data Integrity

As a data scientist, I want detected events to be stored in a shared relational or NoSQL database for long-term storage.

As a system administrator, I want the persistence layer to handle requests idempotently to prevent duplicate event storage from different replicas.
+1

As a user, I want each persisted event to include a UTC timestamp, value in mm/s, and the sensor ID.
+1

As an analyst, I want to be able to query historical seismic events stored in the database.

AREA 4 - Fault Tolerance & Gateway

As a frontend user, I want to access the backend through a single entry point (Gateway) that routes requests to available replicas.
+1

As a system administrator, I want the Gateway to use health checks to detect and exclude failed replicas automatically.

As a commander, I want the system to remain operational even if one or more processing replicas fail abruptly.

As a developer, I want to ensure that all components except the processing replicas are considered reliable by design.

AREA 5 - Dashboard & UX

As an operator, I want a real-time dashboard to visualize detected seismic events as they happen.

As an analyst, I want to receive real-time updates via WebSocket or SSE to minimize latency in threat detection.

As an analyst, I want to filter detected events by sensor ID or event type for better exploration.

As a user, I want the frontend to be responsive and capable of displaying historical data trends.

As a developer, I want the entire system to be deployable with a single docker compose up command.

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