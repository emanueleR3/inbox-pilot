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

# Copy all listeners sources
COPY gmail_listener/ ./gmail_listener/
COPY imap_poller/ ./imap_poller/
COPY microsoft_listener/ ./microsoft_listener/

# Add startup script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

ENV PYTHONUNBUFFERED=1

# Microsoft webhook server port
EXPOSE 8001

ENTRYPOINT ["/app/start.sh"]
