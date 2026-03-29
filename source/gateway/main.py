"""
Gateway Service - Single entry point for the frontend.
- Routes requests to healthy processing replicas (round-robin)
- Health checks replicas periodically
- Exposes SSE stream for real-time events to the dashboard
"""

import asyncio
import os
import json
import logging
import time
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

REPLICAS = os.getenv(
    "PROCESSING_REPLICAS",
    "http://processing-1:8001,http://processing-2:8001,http://processing-3:8001"
).split(",")

HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "5"))

# Track which replicas are alive
replica_health: dict[str, bool] = {r: True for r in REPLICAS}
_rr_index = 0

# SSE subscribers for real-time event push
sse_subscribers: list[asyncio.Queue] = []


def get_healthy_replicas() -> list[str]:
    return [r for r, ok in replica_health.items() if ok]


def next_replica() -> str | None:
    """Round-robin over healthy replicas."""
    global _rr_index
    healthy = get_healthy_replicas()
    if not healthy:
        return None
    _rr_index = _rr_index % len(healthy)
    chosen = healthy[_rr_index]
    _rr_index = (_rr_index + 1) % len(healthy)
    return chosen


async def health_checker():
    """Periodically check replica health."""
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            for replica in REPLICAS:
                try:
                    resp = await client.get(f"{replica}/health")
                    is_healthy = resp.status_code == 200
                except Exception:
                    is_healthy = False

                was_healthy = replica_health.get(replica, True)
                replica_health[replica] = is_healthy

                if was_healthy and not is_healthy:
                    logger.warning(f"Replica DOWN: {replica}")
                elif not was_healthy and is_healthy:
                    logger.info(f"Replica RECOVERED: {replica}")

            await asyncio.sleep(HEALTH_CHECK_INTERVAL)


async def event_poller():
    """Poll events from a healthy replica and push to SSE subscribers."""
    last_seen_id = 0
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            replica = next_replica()
            if replica:
                try:
                    resp = await client.get(
                        f"{replica}/events",
                        params={"limit": 100}
                    )
                    if resp.status_code == 200:
                        events = resp.json()
                        new_events = [e for e in events if e.get("id", 0) > last_seen_id]
                        if new_events:
                            last_seen_id = max(e["id"] for e in new_events)
                            for subscriber in list(sse_subscribers):
                                try:
                                    await subscriber.put(new_events)
                                except Exception:
                                    pass
                except Exception as e:
                    logger.debug(f"Poll error: {e}")
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(health_checker())
    asyncio.create_task(event_poller())
    logger.info("Gateway started")
    yield


app = FastAPI(title="Seismic Gateway", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    healthy = get_healthy_replicas()
    return {
        "status": "ok" if healthy else "degraded",
        "healthy_replicas": healthy,
        "all_replicas": REPLICAS,
    }


@app.get("/api/events")
async def get_events(
    limit: int = Query(50, le=200),
    sensor_id: str = Query(None),
    event_type: str = Query(None),
):
    """Proxy event queries to a healthy replica."""
    replica = next_replica()
    if not replica:
        raise HTTPException(503, "No healthy replicas available")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            params = {"limit": limit}
            if sensor_id:
                params["sensor_id"] = sensor_id
            if event_type:
                params["event_type"] = event_type
            resp = await client.get(f"{replica}/events", params=params)
            return resp.json()
    except Exception as e:
        raise HTTPException(502, f"Replica error: {e}")


@app.get("/api/replicas")
async def get_replicas():
    return {
        r: {"healthy": replica_health[r]} for r in REPLICAS
    }


@app.get("/api/events/stream")
async def event_stream():
    """SSE stream of real-time detected events."""
    queue: asyncio.Queue = asyncio.Queue()
    sse_subscribers.append(queue)

    async def generate():
        try:
            # Send initial ping
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    events = await asyncio.wait_for(queue.get(), timeout=15.0)
                    for event in events:
                        # Convert datetime objects to strings for JSON
                        event_copy = {
                            k: str(v) if hasattr(v, 'isoformat') else v
                            for k, v in event.items()
                        }
                        yield f"data: {json.dumps(event_copy)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            sse_subscribers.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
