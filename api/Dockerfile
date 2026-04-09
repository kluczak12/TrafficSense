FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME ["/data/videos", "/data/db"]

ENV DB_PATH=/data/db/pedestrians.db
ENV VIDEO_DIR=/data/videos

# EXPOSE 8000

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
