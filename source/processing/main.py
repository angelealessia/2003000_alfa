"""
Processing Service - Replicated seismic analysis node.
- Maintains sliding window per sensor
- Applies FFT to detect dominant frequency
- Classifies events (Earthquake / Explosion / Nuclear)
- Persists events to shared PostgreSQL (idempotent)
- Listens to simulator control stream and shuts down on SHUTDOWN command
"""

import asyncio
import sys
import os
import json
import logging
import httpx
import numpy as np
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("processing")

# ── Config ──────────────────────────────────────────────────────────────────
SIMULATOR_URL   = os.getenv("SIMULATOR_URL", "http://simulator:8080")
DATABASE_URL    = os.getenv("DATABASE_URL", "postgresql://seismic:seismic@postgres:5432/seismic")
SAMPLING_RATE   = int(os.getenv("SAMPLING_RATE_HZ", "20"))
WINDOW_SECONDS  = int(os.getenv("WINDOW_SECONDS", "10"))
WINDOW_SIZE     = SAMPLING_RATE * WINDOW_SECONDS
REPLICA_ID      = os.getenv("REPLICA_ID", "replica-1")

# ── State ────────────────────────────────────────────────────────────────────
windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))
last_event_time: dict[str, datetime] = {}
EVENT_COOLDOWN_SECONDS = int(os.getenv("EVENT_COOLDOWN_SECONDS", "15"))
db_pool = None


# ── Event classification ─────────────────────────────────────────────────────
def classify_event(dominant_freq: float) -> str | None:
    if 0.5 <= dominant_freq < 3.0:
        return "EARTHQUAKE"
    elif 3.0 <= dominant_freq < 8.0:
        return "EXPLOSION"
    elif dominant_freq >= 8.0:
        return "NUCLEAR"
    return None


def analyze_window(samples: list[float]) -> tuple[float, str | None]:
    """Run FFT on samples and return (dominant_freq, event_type)."""
    arr = np.array(samples)
    arr -= arr.mean()
    n = len(arr)
    fft_vals = np.abs(np.fft.rfft(arr))
    freqs    = np.fft.rfftfreq(n, d=1.0 / SAMPLING_RATE)

    fft_vals[0] = 0
    dominant_idx  = np.argmax(fft_vals)
    dominant_freq = float(freqs[dominant_idx])
    event_type    = classify_event(dominant_freq)
    return dominant_freq, event_type


# ── Persistence ───────────────────────────────────────────────────────────────
async def init_db():
    global db_pool
    for attempt in range(10):
        try:
            db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id          BIGSERIAL PRIMARY KEY,
                        sensor_id   TEXT        NOT NULL,
                        event_type  TEXT        NOT NULL,
                        dominant_freq FLOAT     NOT NULL,
                        detected_at TIMESTAMPTZ NOT NULL,
                        replica_id  TEXT        NOT NULL,
                        created_at  TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE (sensor_id, detected_at)
                    )
                """)
            logger.info("DB connection established")
            return
        except Exception as e:
            logger.warning(f"DB not ready (attempt {attempt+1}/10): {e}")
            await asyncio.sleep(3)
    logger.error("Could not connect to DB. Exiting.")
    sys.exit(1)


async def persist_event(sensor_id: str, event_type: str, dominant_freq: float, detected_at: datetime):
    """Insert event, silently ignore duplicates (idempotent)."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO events (sensor_id, event_type, dominant_freq, detected_at, replica_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (sensor_id, detected_at) DO NOTHING
        """, sensor_id, event_type, dominant_freq, detected_at, REPLICA_ID)


# ── Control stream (failure simulation) ──────────────────────────────────────
async def listen_control_stream():
    """Listen to simulator SSE control stream. Shutdown on command."""
    url = f"{SIMULATOR_URL}/api/control"
    headers = {"Accept": "text/event-stream"}
    logger.info(f"Connecting to control stream at {url}")
    async with httpx.AsyncClient(timeout=None) as client:
        while True:
            try:
                async with client.stream("GET", url, headers=headers) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        if data.get("command") == "SHUTDOWN":
                            logger.warning(f"[{REPLICA_ID}] SHUTDOWN command received. Terminating.")
                            sys.exit(0)
            except Exception as e:
                logger.warning(f"Control stream error: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(listen_control_stream())
    logger.info(f"Processing replica {REPLICA_ID} ready")
    yield
    if db_pool:
        await db_pool.close()


app = FastAPI(title=f"Processing Service ({REPLICA_ID})", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── API ───────────────────────────────────────────────────────────────────────
class Measurement(BaseModel):
    sensor_id: str
    timestamp: str
    value: float


@app.post("/ingest")
async def ingest(measurement: Measurement):
    """Receive a measurement from the broker and process it."""
    sensor_id = measurement.sensor_id
    windows[sensor_id].append(measurement.value)

    if len(windows[sensor_id]) < 20:
        return {"status": "buffering", "samples": len(windows[sensor_id])}

    dominant_freq, event_type = analyze_window(list(windows[sensor_id]))

    if event_type:
        try:
            detected_at = datetime.fromisoformat(measurement.timestamp.replace("Z", "+00:00"))
        except Exception:
            detected_at = datetime.now(timezone.utc)

        last = last_event_time.get(sensor_id)
        now = datetime.now(timezone.utc)
        if last is None or (now - last).total_seconds() >= EVENT_COOLDOWN_SECONDS:
            last_event_time[sensor_id] = now
            await persist_event(sensor_id, event_type, dominant_freq, detected_at)
            logger.info(f"[{REPLICA_ID}] {event_type} on {sensor_id} @ {dominant_freq:.2f} Hz")

    return {
        "status": "processed",
        "sensor_id": sensor_id,
        "dominant_freq": dominant_freq,
        "event_type": event_type,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "replica_id": REPLICA_ID, "sensors_tracked": len(windows)}


@app.get("/events")
async def get_events(
    limit: int = 50,
    sensor_id: str = None,
    event_type: str = None,
    after_id: int = 0,
):
    """Query detected events from the shared DB."""
    query = "SELECT * FROM events WHERE id > $1"
    params = [after_id]
    if sensor_id:
        params.append(sensor_id)
        query += f" AND sensor_id = ${len(params)}"
    if event_type:
        params.append(event_type)
        query += f" AND event_type = ${len(params)}"
    params.append(limit)
    query += f" ORDER BY id ASC LIMIT ${len(params)}"

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]
