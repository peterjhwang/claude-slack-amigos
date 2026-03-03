FROM python:3.12-slim

WORKDIR /app

# System deps (gcc needed for some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data directory for SQLite databases (mapped to a volume in docker-compose)
RUN mkdir -p /app/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "info"]
