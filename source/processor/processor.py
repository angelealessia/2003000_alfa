import asyncio
import json
import numpy as np
import requests
from flask import Flask, request
import threading
import os

app = Flask(__name__)

# Memoria temporanea per i dati dei sensori (Sliding Window)
# Teniamo gli ultimi 100 campioni per ogni sensore
sensor_data = {} 
WINDOW_SIZE = 100

def classify_event(frequency):
    if 0.5 <= frequency < 3.0:
        return "Earthquake"
    elif 3.0 <= frequency < 8.0:
        return "Conventional Explosion"
    elif frequency >= 8.0:
        return "Nuclear-like Event"
    return "Background Noise"

@app.route('/ingest', methods=['POST'])
def ingest():
    content = request.json
    s_id = content['sensor_id']
    val = content['data']['value']
    
    if s_id not in sensor_data:
        sensor_data[s_id] = []
    
    sensor_data[s_id].append(val)
    
    # Se abbiamo abbastanza dati, calcoliamo la FFT
    if len(sensor_data[s_id]) >= WINDOW_SIZE:
        window = sensor_data[s_id][-WINDOW_SIZE:]
        # Calcolo FFT
        fft_vals = np.abs(np.fft.rfft(window))
        freqs = np.fft.rfftfreq(WINDOW_SIZE, d=0.1) # Assumendo 10Hz di campionamento
        idx_max = np.argmax(fft_vals[1:]) + 1 # Escludiamo la componente DC
        dom_freq = freqs[idx_max]
        
        event = classify_event(dom_freq)
        if event != "Background Noise":
            print(f"!!! RILEVATO EVENTO su {s_id}: {event} (Freq: {dom_freq:.2f} Hz) !!!")
            # Qui domani aggiungeremo la scrittura su Postgres
            
    return {"status": "ok"}, 200

# Funzione per gestire lo SHUTDOWN (SSE)
def listen_control():
    try:
        response = requests.get("http://simulator:8080/api/control", stream=True)
        for line in response.iter_lines():
            if line:
                msg = json.loads(line.decode('utf-8').replace('data: ', ''))
                if msg.get("command") == "SHUTDOWN":
                    print("Comando SHUTDOWN ricevuto! Spegnimento replica...")
                    os._exit(0) # Uscita forzata come richiesto
    except:
        pass

if __name__ == "__main__":
    # Avvia il thread di controllo per lo spegnimento
    threading.Thread(target=listen_control, daemon=True).start()
    # Avvia il server per ricevere dati dal broker
    app.run(host='0.0.0.0', port=5000)
