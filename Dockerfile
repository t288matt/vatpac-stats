# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in user space
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/home/app/.local/bin:$PATH

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/cache && \
    chmod 755 /app/logs /app/data /app/cache

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8001

# Health check with proper timeout and error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/api/status || exit 1

# Default command with centralized error handling
CMD ["python", "run.py"] 