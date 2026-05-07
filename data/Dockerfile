FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY costam.py .
COPY db.py .

ENV VIDEO_DIR=/data/videos
ENV ANNOTATIONS_DIR=/data/videos/annotations
ENV FRAMES_DIR=/data/frames

CMD ["python3", "costam.py"]
