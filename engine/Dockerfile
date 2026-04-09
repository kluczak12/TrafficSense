FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME ["/data/frames", "/data/db", "/data/model"]

ENV FRAMES_DIR=/data/frames
ENV DB_PATH=/data/db/pedestrians.db
ENV MODEL_PATH=/data/model

#CMD ["python", "costam.py"]
