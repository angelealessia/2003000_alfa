import json
import numpy as np
import requests
from flask import Flask, request, jsonify
import threading
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)

# Configurazione DB
def get_db_connection():
    return psycopg2.connect(
        host="db",
        database="seismic_hq",
        user="admin",
        password="password"
    )

# Inizializzazione Tabella con vincolo di unicità (Idempotenza) [cite: 98, 118]
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        sensor_id TEXT,
        timestamp TIMESTAMP,
        frequency FLOAT,
        event_type TEXT,
        value FLOAT,
        UNIQUE(sensor_id, timestamp) -- Impedisce doppioni per lo stesso evento [cite: 98]
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

sensor_data = {} 
WINDOW_SIZE = 100 

def classify_event(frequency):
    if 0.5 <= frequency < 3.0: return "Earthquake" [cite: 90]
    elif 3.0 <= frequency < 8.0: return "Conventional Explosion" [cite: 91]
    elif frequency >= 8.0: return "Nuclear-like Event" [cite: 92]
    return "Background Noise"

@app.route('/ingest', methods=['POST'])
def ingest():
    content = request.get_json(force=True, silent=True)
    if not content: return jsonify({"error": "Invalid JSON"}), 400

    try:
        s_id = content['sensor_id']
        val = content['data']['value']
        ts = content['data'].get('timestamp', datetime.utcnow().isoformat())
        
        if s_id not in sensor_data: sensor_data[s_id] = []
        sensor_data[s_id].append(val)
        
        if len(sensor_data[s_id]) > WINDOW_SIZE: sensor_data[s_id].pop(0)

        if len(sensor_data[s_id]) == WINDOW_SIZE:
            window = np.array(sensor_data[s_id])
            fft_vals = np.abs(np.fft.rfft(window))
            freqs = np.fft.rfftfreq(WINDOW_SIZE, d=0.05) 
            dom_freq = freqs[np.argmax(fft_vals[1:]) + 1]
            
            event = classify_event(dom_freq)
            if event != "Background Noise":
                # Inserimento con gestione conflitti (Idempotenza) [cite: 141]
                conn = get_db_connection()
                cur = conn.cursor()
                try:
                    cur.execute("""
                        INSERT INTO events (sensor_id, timestamp, frequency, event_type, value)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (sensor_id, timestamp) DO NOTHING
                    """, (s_id, ts, float(dom_freq), event, float(val)))
                    conn.commit()
                except Exception as e:
                    print(f"Errore DB: {e}")
                finally:
                    cur.close()
                    conn.close()
                
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/events', methods=['GET'])
def list_events():
    """Endpoint per il Gateway"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT sensor_id, timestamp, frequency, event_type, value FROM events ORDER BY timestamp DESC LIMIT 50")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"sensor_id": r[0], "timestamp": r[1].isoformat(), "frequency": r[2], "type": r[3], "value": r[4]} for r in rows])

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online"}), 200

def listen_control():
    try:
        response = requests.get("http://simulator:8080/api/control", stream=True) [cite: 56]
        for line in response.iter_lines():
            if line:
                msg = json.loads(line.decode('utf-8').replace('data: ', ''))
                if msg.get("command") == "SHUTDOWN": [cite: 60]
                    os._exit(0) [cite: 61]
    except: pass

if __name__ == "__main__":
    threading.Thread(target=listen_control, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
