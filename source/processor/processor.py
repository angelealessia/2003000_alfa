import asyncio
import json
import numpy as np
import requests
from flask import Flask, request, jsonify # Aggiunto jsonify
import threading
import os

app = Flask(__name__)

# Memoria temporanea per i dati dei sensori (Sliding Window) [cite: 85]
sensor_data = {} 
WINDOW_SIZE = 100 

def classify_event(frequency):
    # Soglie fittizie richieste dall'esame [cite: 90, 91, 92]
    if 0.5 <= frequency < 3.0:
        return "Earthquake"
    elif 3.0 <= frequency < 8.0:
        return "Conventional Explosion"
    elif frequency >= 8.0:
        return "Nuclear-like Event"
    return "Background Noise"

@app.route('/ingest', methods=['POST'])
def ingest():
    # RISOLUZIONE ERRORE 400: 'force=True' legge il JSON anche se l'header è mancante
    content = request.get_json(force=True, silent=True)
    
    if content is None:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        s_id = content['sensor_id']
        # Estraiamo il valore numerico dalla struttura del simulatore 
        val = content['data']['value']
        
        if s_id not in sensor_data:
            sensor_data[s_id] = []
        
        sensor_data[s_id].append(val)
        
        # Gestione Sliding Window [cite: 85]
        if len(sensor_data[s_id]) > WINDOW_SIZE:
            sensor_data[s_id].pop(0)

        # Se abbiamo abbastanza dati, calcoliamo la FFT [cite: 86, 87]
        if len(sensor_data[s_id]) == WINDOW_SIZE:
            window = np.array(sensor_data[s_id])
            # Calcolo FFT [cite: 86]
            fft_vals = np.abs(np.fft.rfft(window))
            # d=0.05 perché il campionamento di default è 20Hz (1/20 = 0.05s) 
            freqs = np.fft.rfftfreq(WINDOW_SIZE, d=0.05) 
            
            idx_max = np.argmax(fft_vals[1:]) + 1 
            dom_freq = freqs[idx_max]
            
            event = classify_event(dom_freq)
            if event != "Background Noise":
                # Questo log ti conferma che i dati stanno fluendo!
                print(f"!!! RILEVATO: {event} su {s_id} (Freq: {dom_freq:.2f} Hz) !!!")
                # TODO: Domani aggiungeremo il salvataggio su Postgres [cite: 96, 98]
                
        return jsonify({"status": "ok"}), 200

    except (KeyError, TypeError) as e:
        return jsonify({"error": f"Missing or malformed data: {str(e)}"}), 400

# Funzione per gestire lo SHUTDOWN forzato via SSE [cite: 53, 54, 61]
def listen_control():
    print("In ascolto sul canale di controllo SSE...")
    try:
        # La replica si collega al flusso di controllo del simulatore [cite: 56]
        response = requests.get("http://simulator:8080/api/control", stream=True)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    msg_content = decoded_line.replace('data: ', '')
                    msg = json.loads(msg_content)
                    if msg.get("command") == "SHUTDOWN":
                        print("!!! RICEVUTO COMANDO SHUTDOWN: Chiusura immediata !!!")
                        os._exit(0) # Spegnimento forzato richiesto [cite: 61]
    except Exception as e:
        print(f"Errore connessione controllo: {e}")

if __name__ == "__main__":
    # Avvia lo shutdown listener in un thread separato [cite: 53]
    threading.Thread(target=listen_control, daemon=True).start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
