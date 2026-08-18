# Image for the Flask viewer (wsgi:app) + the parser/campaign scripts.
# scripts/parser.py and scripts/send_campaign.py shell out to `psql`, so the
# Postgres client is installed alongside the Python deps.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Production run (same command as deploy/README.md), bound to all interfaces
# so it's reachable from outside the container.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "wsgi:app"]
