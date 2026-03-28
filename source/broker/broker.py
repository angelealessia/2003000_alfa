import asyncio
import websockets
import json
import requests
import time

# URL del simulatore
SIMULATOR_URL = "http://simulator:8080"
WS_URL = "ws://simulator:8080"

# Lista degli indirizzi delle tue repliche (es. processor_1, processor_2)
# In Docker Compose userai i nomi dei servizi
REPLICAS = ["http://processor_1:5000/ingest", "http://processor_2:5000/ingest"]

async def handle_sensor(sensor_id):
    uri = f"{WS_URL}/api/device/{sensor_id}/ws"
    async with websockets.connect(uri) as websocket:
        print(f"Monitorando sensore: {sensor_id}")
        while True:
            data = await websocket.recv()
            # 1. Riceve il dato dal simulatore
            measurement = json.loads(data) 
            
            # 2. Fan-out: lo manda a tutte le repliche [cite: 80]
            # Nel file broker.py, dentro handle_sensor:
            for replica_url in REPLICAS:
                try:
                    # Aggiungiamo esplicitamente l'header JSON
                    requests.post(
                        replica_url, 
                        json={"sensor_id": sensor_id, "data": measurement},
                        headers={'Content-Type': 'application/json'} # <--- Fondamentale!
                    )
                except:
                    pass

async def main():
    # Prova a connettersi finché il simulatore non risponde
    devices = None
    while devices is None:
        try:
            response = requests.get(f"{SIMULATOR_URL}/api/devices/")
            devices = response.json()
        except Exception:
            print("In attesa del simulatore...")
            time.sleep(2) # Aspetta 2 secondi prima di riprovare
 
    
    # Crea un task per ogni sensore
    tasks = [handle_sensor(d['id']) for d in devices]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
