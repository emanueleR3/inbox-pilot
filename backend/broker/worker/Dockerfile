# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker sources
COPY worker/src ./src

ENV PYTHONUNBUFFERED=1

RUN sleep 15

# Run the async worker
CMD ["python", "-m", "src.main"]
