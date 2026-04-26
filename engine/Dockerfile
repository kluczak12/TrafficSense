FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN apt update && apt install -y \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    libxau6 \
    libxdmcp6 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt

COPY identificationOfPedestrians.py .
COPY prediction.py .

ENV FRAMES_DIR=/data/frames
ENV DB_PATH=/data/db/pedestrians.db
ENV OUTPUT_DIR=/app/output_videos

CMD ["python3", "prediction.py"]