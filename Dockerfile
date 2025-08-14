# Multi-stage build using Debian for better library support
FROM python:3.11-slim as builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install build dependencies - simplified to essential only
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in user space with minimal packages
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Production stage - Debian slim for better library support
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/home/app/.local/bin:$PATH

# Install runtime dependencies - simplified to essential only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/app/.local

# Copy only essential application files
COPY app/ ./app/
COPY tests/ ./tests/
COPY config/ ./config/
COPY run.py .
COPY run_tests.py .
COPY requirements.txt .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/cache && \
    chmod 755 /app/logs /app/data /app/cache

# Create non-root user for security (Debian syntax)
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8001

# Health check with proper timeout and error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/api/status || exit 1

# Default command
CMD ["python", "run.py"] 