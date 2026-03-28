# 2003000_alfa
# 🌐 SEISMIC-INTELL 2038
> **Global Surveillance & Nuclear Detection System**
> *Official Intelligence Software for the Neutral Region Strategic Command*

![Status](https://img.shields.io/badge/STATUS-OPERATIONAL-emerald)
![Docker](https://img.shields.io/badge/DOCKER-READY-blue)
![Environment](https://img.shields.io/badge/REGION-NEUTRAL-white)

## 📖 Overview
Seismic-Intell 2038 is a distributed, real-time seismic monitoring system designed to detect and classify ground vibrations in post-conflict scenarios. The system distinguishes between natural seismic activity, conventional explosions, and clandestine nuclear tests using high-performance frequency-domain analysis (**FFT**).

### Key Features
* **Massive Ingestion**: Asynchronous Broker with automatic sensor discovery.
* **High Availability**: Multi-replica architecture with load balancing and failover.
* **Real-Time Analytics**: Fast Fourier Transform (FFT) for instant event classification.
* **Idempotent Storage**: PostgreSQL-backed persistence with duplicate-safe logic.
* **Tactical Dashboard**: High-visibility "Military-Grade" UI for real-time threat monitoring.

---

## 🏗 Architecture
The system consists of containerized microservices orchestrated via Docker Compose:

1.  **Simulator**: The ground vibration signal generator (provided).
2.  **Broker (Fan-out)**: Handles WebSocket connections and redistributes data to processing units.
3.  **Processing Replicas**: Execute FFT calculations and classify events based on frequency.
4.  **Gateway**: Single entry point for the Frontend, managing traffic and health checks.
5.  **PostgreSQL**: Secure database for persistent logging of detected events.
6.  **Dashboard**: Tactical web interface for live data exploration.

---

## 🚀 Quick Start

Ensure you have **Docker** and **Docker Compose** installed.

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/seismic-intell-2038.git](https://github.com/your-username/seismic-intell-2038.git)
    cd seismic-intell-2038
    ```

2.  **Launch the ecosystem**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the Command Center**:
    Open your browser at `http://localhost:3000`

---

## 📡 Event Classification Logic
Events are classified based on the dominant frequency ($f$):

| Frequency ($f$) | Classification | Threat Level |
| :--- | :--- | :--- |
| $0.5 \le f < 3.0$ Hz | Earthquake | 🟢 LOW |
| $3.0 \le f < 8.0$ Hz | Conventional Explosion | 🟡 MEDIUM |
| $f \ge 8.0$ Hz | **NUCLEAR-LIKE EVENT** | 🔴 CRITICAL |

---

## 📂 Project Structure
```text
.
├── source/
│   ├── broker/        # Data ingestion (Python Async)
│   ├── processing/    # FFT Analysis & Classification logic
│   ├── gateway/       # API & WebSocket Hub
│   └── frontend/      # Tactical Dashboard (HTML5/Tailwind/JS)
├── booklets/          # Architecture Diagrams, Mockups, and Slides
├── input.md           # User Stories & Requirements
├── Student_doc.md     # Detailed Technical Documentation
└── docker-compose.yml # Container Orchestration
