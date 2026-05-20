FROM python:3.12-slim

WORKDIR /app

# prawdopodobnie już się nie przyda
# COPY requirements.txt .
# RUN pip install -r requirements.txt

COPY main.py .
COPY db.py .

ENV ANNOTATIONS_DIR=/data/annotations
ENV ANNOTATIONS_VEHICLE_DIR=/data/annotations_vehicle
ENV ANNOTATIONS_TRAFFIC_DIR=/data/annotations_traffic
ENV DB_DIR=/data/db

# ustawić do testu frame_extractor.py
# ENV VIDEO_DIR=/data/videos
# ENV FRAMES_DIR=/data/frames

CMD ["python3", "main.py"]
