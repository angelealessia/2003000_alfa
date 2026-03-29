"""
Broker Service - Fan-out component (neutral region).
Connects to all sensors via WebSocket and redistributes
measurements to all processing replicas. NO data processing here.
"""

import asyncio
import httpx
import websockets
import json
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("broker")

SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://simulator:8080")
PROCESSING_REPLICAS = os.getenv(
    "PROCESSING_REPLICAS",
    "http://processing-1:8001,http://processing-2:8001,http://processing-3:8001"
).split(",")

# Connected dashboard clients (for forwarding raw measurements if needed)
dashboard_clients: list[WebSocket] = []

# Queue of measurements to fan-out
measurement_queue: asyncio.Queue = asyncio.Queue()


async def get_sensors() -> list[dict]:
    """Discover available sensors from simulator."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{SIMULATOR_URL}/api/devices/")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get sensors: {e}")
            return []


async def consume_sensor(sensor_id: str):
    """Connect to a sensor WebSocket and push measurements to queue."""
    ws_url = SIMULATOR_URL.replace("http", "ws") + f"/api/device/{sensor_id}/ws"
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                logger.info(f"Connected to sensor {sensor_id}")
                async for raw in ws:
                    measurement = json.loads(raw)
                    measurement["sensor_id"] = sensor_id
                    await measurement_queue.put(measurement)
        except Exception as e:
            logger.warning(f"Sensor {sensor_id} disconnected: {e}. Reconnecting in 2s...")
            await asyncio.sleep(2)


async def fan_out_worker():
    """Dequeue measurements and POST to all processing replicas."""
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            measurement = await measurement_queue.get()
            tasks = []
            for replica_url in PROCESSING_REPLICAS:
                url = f"{replica_url}/ingest"
                tasks.append(
                    client.post(url, json=measurement)
                )
            # Fire and forget - we don't block on replica failures
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for replica_url, result in zip(PROCESSING_REPLICAS, results):
                if isinstance(result, Exception):
                    logger.debug(f"Replica {replica_url} unreachable: {result}")

            # Also forward to dashboard clients for raw stream
            if dashboard_clients:
                dead = []
                for ws in dashboard_clients:
                    try:
                        await ws.send_text(json.dumps(measurement))
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    dashboard_clients.remove(ws)

            measurement_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start sensor consumers and fan-out worker
    sensors = await get_sensors()
    if not sensors:
        logger.warning("No sensors found, retrying in 5s...")
        await asyncio.sleep(5)
        sensors = await get_sensors()

    tasks = []
    for sensor in sensors:
        sid = sensor.get("id") or sensor.get("sensor_id") or str(sensor)
        tasks.append(asyncio.create_task(consume_sensor(sid)))

    tasks.append(asyncio.create_task(fan_out_worker()))
    logger.info(f"Broker started: {len(sensors)} sensors, {len(PROCESSING_REPLICAS)} replicas")
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="Seismic Broker", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "replicas": PROCESSING_REPLICAS}


@app.websocket("/ws/raw")
async def raw_stream(ws: WebSocket):
    """Forward raw measurements to dashboard clients."""
    await ws.accept()
    dashboard_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        dashboard_clients.remove(ws)
