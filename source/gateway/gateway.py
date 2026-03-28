from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROCESSORS = ["http://processor_1:5000", "http://processor_2:5000"]

@app.get("/health")
def system_health():
    status = {}
    for p in PROCESSORS:
        try:
            r = requests.get(f"{p}/health", timeout=0.5)
            status[p] = "online" if r.status_code == 200 else "error"
        except:
            status[p] = "offline"
    return {"gateway": "online", "processors": status}

@app.get("/events")
def get_events():
    for p in PROCESSORS:
        try:
            r = requests.get(f"{p}/events", timeout=1)
            if r.status_code == 200:
                return r.json()
        except:
            continue
    return {"error": "Nessun processor disponibile"}, 503

@app.get("/")
def root():
    return {"message": "Seismic Gateway Active"}
