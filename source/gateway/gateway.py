from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()

# Permette al frontend di chiamare il gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# indirizzo database (docker compose service name)
DATABASE_URL = "http://database:8000"

# lista processor replicas
PROCESSORS = [
    "http://processor_1:5000",
    "http://processor_2:5000",
    "http://processor_3:5000"
]

# -------------------------
# health check sistema
# -------------------------

@app.get("/health")
def system_health():

    status = {}

    for p in PROCESSORS:
        try:
            r = requests.get(p + "/health", timeout=1)
            status[p] = "online"
        except:
            status[p] = "offline"

    return {
        "gateway": "online",
        "processors": status
    }

# -------------------------
# eventi salvati
# -------------------------

@app.get("/events")
def get_events():

    try:
        r = requests.get(f"{DATABASE_URL}/events")
        return r.json()

    except:
        return {"error": "database not reachable"}

# -------------------------
# eventi filtrati per tipo
# -------------------------

@app.get("/events/{event_type}")
def filter_events(event_type: str):

    try:
        r = requests.get(f"{DATABASE_URL}/events?type={event_type}")
        return r.json()

    except:
        return {"error": "database not reachable"}

# -------------------------
# endpoint base
# -------------------------

@app.get("/")
def root():
    return {"message": "Seismic Gateway running"}