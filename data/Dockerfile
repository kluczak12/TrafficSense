FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME ["/data/videos", "/data/frames", "/data/db"]

ENV VIDEO_DIR=/data/videos
ENV FRAMES_DIR=/data/frames

# CMD ["python", "costam.py"]
