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

# wersja na mocniejszy laptop
# RUN pip install torch torchvision
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
RUN pip install -r requirements.txt

COPY annotation_loader.py .
COPY event_logger.py .
COPY collision_detection.py .
COPY pedestrian_detection.py .
COPY server.py .

# ustawić dla testu video_processor.py
# ENV FRAMES_DIR=/data/frames
# ENV OUTPUT_DIR=/app/output_videos
ENV YOLO_CONFIG_DIR=/tmp

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]