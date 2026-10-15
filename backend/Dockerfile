# =========================================
#  Infrastructure Knowledge Intelligence
#  Backend Dockerfile (Multi-Stage CPU-Optimized)
# =========================================

# --- Stage 1: Base ---
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends --fix-missing \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Stage 2: Dependencies ---
FROM base AS dependencies

RUN pip install --no-cache-dir --upgrade pip

# Install CPU-only PyTorch first (avoids downloading 3GB+ of CUDA libraries)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 3: Application ---
FROM dependencies AS application

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/system || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
