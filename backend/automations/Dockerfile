FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /automations

# Install Python deps first for better caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all sources
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/automations

# Expose API port
EXPOSE 8010

# CMD ["uvicorn", "api.main:automations", "--host", "0.0.0.0", "--port", "8010"]
CMD ["python", "api/main.py"]
