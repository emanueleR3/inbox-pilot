FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/v1

# Install Python deps first for better caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all API sources
COPY v1/ .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/v1

# Expose API port
EXPOSE 8000

ENTRYPOINT ["python", "-m", "src.main"]