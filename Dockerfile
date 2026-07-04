FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend

EXPOSE 8080

# Render (and similar PaaS hosts) inject PORT and expect the container to listen on it;
# default to 8080 for hosts that don't set it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
