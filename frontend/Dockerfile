FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN apt update && apt install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

COPY server.py .
COPY index.html .

EXPOSE 3000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]