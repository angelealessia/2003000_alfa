import asyncio
import websockets
import json

async def connect_sensor():
    uri = "ws://localhost:8080/api/device/sensor-01/ws" # [cite: 46]
    async with websockets.connect(uri) as websocket:
        print("Connesso al sensore!")
        while True:
            data = await websocket.recv()
            measurement = json.loads(data)
            # Qui riceverai timestamp e valore in mm/s [cite: 47]
            print(f"Dato ricevuto: {measurement}")

asyncio.run(connect_sensor())
