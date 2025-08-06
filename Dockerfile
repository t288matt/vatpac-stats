# Ultra-optimized multi-stage build for minimal footprint
FROM python:3.11-alpine as builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install only essential build dependencies including linux-headers for psutil
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    linux-headers \
    && rm -rf /var/cache/apk/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in user space with minimal packages
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Production stage - Alpine for minimal footprint
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/home/app/.local/bin:$PATH

# Install only runtime dependencies
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    && rm -rf /var/cache/apk/*

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/app/.local

# Copy only essential application files
COPY app/ ./app/
COPY run.py .
COPY requirements.txt .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/cache && \
    chmod 755 /app/logs /app/data /app/cache

# Create non-root user for security
RUN adduser -D -s /bin/sh -u 1000 app && \
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