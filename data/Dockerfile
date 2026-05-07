FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY costam.py .
COPY db.py .

ENV VIDEO_DIR=/data/videos
ENV ANNOTATIONS_DIR=/data/videos/annotations
ENV FRAMES_DIR=/data/frames
ENV EXPECTED_MODEL_HASH=f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36

CMD ["python3", "costam.py"]
