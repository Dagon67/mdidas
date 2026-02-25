# Backend de colorimetria para Cloud Run
FROM python:3.11-slim

WORKDIR /app

# Dependências de sistema para OpenCV (libgl1 é o pacote atual no Debian novo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render e Cloud Run injetam PORT
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
