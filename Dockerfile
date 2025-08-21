# =============================================================================
# VATSIM DATA COLLECTION SYSTEM - MULTI-STAGE DOCKERFILE
# =============================================================================

# =============================================================================
# STAGE 1: PYTHON APPLICATION BUILDER
# =============================================================================
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 2: PYTHON APPLICATION RUNTIME
# =============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/home/app/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application files
COPY app/ ./app/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY run.py .
COPY requirements.txt .

# Setup directories and user
RUN mkdir -p /app/logs /app/data /app/cache && \
    chmod 755 /app/logs /app/data /app/cache && \
    useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app

USER app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/api/status || exit 1

CMD ["python", "run.py"]

 