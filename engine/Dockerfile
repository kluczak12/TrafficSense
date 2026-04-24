FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN apt update && apt install -y \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

COPY identificationOfPedestrians.py . 
COPY yolov8n.pt .

VOLUME ["/data/frames", "/data/db", "/data/model", "/lib"]

ENV FRAMES_DIR=/data/frames
ENV DB_PATH=/data/db/pedestrians.db
ENV MODEL_PATH=/data/model

CMD ["python", "identificationOfPedestrians.py"]
