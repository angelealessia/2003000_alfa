FROM python:3.11-slim
WORKDIR /app
RUN pip install flask numpy requests
COPY processor.py .
CMD ["python", "processor.py"]
