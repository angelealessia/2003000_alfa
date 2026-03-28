# Usa un'immagine leggera di Python
FROM python:3.11-slim

# Imposta la cartella di lavoro dentro il container
WORKDIR /app

# Copia i file dei requisiti e installa le librerie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice del broker
COPY broker.py .

# Comando per avviare il broker
CMD ["python", "broker.py"]
