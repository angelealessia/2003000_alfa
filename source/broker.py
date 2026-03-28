import asyncio
import websockets
import json
import requests

# URL del simulatore
SIMULATOR_URL = "http://simulator:8080"
WS_URL = "wws://simulator:8080"

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
            for replica_url in REPLICAS:
                try:
                    # Invio asincrono o semplice post
                    requests.post(replica_url, json={"sensor_id": sensor_id, "data": measurement})
                except:
                    pass # Se una replica è giù (crash), il broker continua! [cite: 107]

async def main():
    # Recupera la lista dei sensori all'avvio 
    response = requests.get(f"{SIMULATOR_URL}/api/devices/")
    devices = response.json()
    
    # Crea un task per ogni sensore
    tasks = [handle_sensor(d['id']) for d in devices]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
