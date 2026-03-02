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

# Copy all refresher sources
COPY google_token_refresher/ ./google_token_refresher/
COPY google_watch_refresher/ ./google_watch_refresher/
COPY microsoft_token_refresher/ ./microsoft_token_refresher/
COPY microsoft_subscription_refresher/ ./microsoft_subscription_refresher/

# Add startup script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/start.sh"]
