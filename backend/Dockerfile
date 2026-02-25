# Backend de colorimetria para Cloud Run
FROM python:3.11-slim

WORKDIR /app

# opencv-python-headless não precisa de libGL/libglib no container headless

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render e Cloud Run injetam PORT
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
