FROM python:3.12-slim

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

COPY annotation_loader.py .
COPY collision_detection.py .
COPY pedestrian_detection.py .
COPY video_processor.py .

ENV FRAMES_DIR=/data/frames
ENV DB_PATH=/data/db/pedestrians.db
ENV OUTPUT_DIR=/app/output_videos
ENV YOLO_CONFIG_DIR=/tmp

CMD ["python3", "video_processor.py"]
