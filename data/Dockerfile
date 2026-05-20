FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY frame_extractor.py .
COPY db.py .

ENV VIDEO_DIR=/data/videos
ENV ANNOTATIONS_DIR=/data/annotations
ENV FRAMES_DIR=/data/frames

CMD ["python3", "frame_extractor.py"]
