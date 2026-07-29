# =========================================
#  Infrastructure Knowledge Intelligence
#  Backend Dockerfile (Multi-Stage)
# =========================================

# --- Stage 1: Base ---
FROM python:3.11-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by some Python packages
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends --fix-missing \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Stage 2: Dependencies ---
FROM base AS dependencies

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 3: Application ---
FROM dependencies AS application

# Copy the application source code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose the FastAPI default port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
