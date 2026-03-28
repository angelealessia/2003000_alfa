FROM python:3.11-slim
WORKDIR /app
# Installiamo le dipendenze in modo che non manchi nulla [cite: 131]
RUN pip install --no-cache-dir flask numpy requests
RUN pip install psycopg2-binary
COPY processor.py .
# Esplicitiamo la porta per Docker [cite: 35]
EXPOSE 5000
CMD ["python", "processor.py"]

