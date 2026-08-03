# syntax=docker/dockerfile:1
# Image chung cho 3 edge agent — giới hạn 2 vCPU / 4GB đặt ở docker-compose.
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MQTT_HOST=mqtt-broker \
    MQTT_PORT=1883

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY agents ./agents
COPY configs ./configs
COPY scripts ./scripts
COPY dashboard ./dashboard

EXPOSE 5000

# Train ONNX trong image để analysis_agent chạy được ngay (CPU-only).
RUN python scripts/train_anomaly_model.py

CMD ["python", "-m", "agents.sensor_agent.main"]
