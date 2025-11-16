# RVC2MQTT Docker Container
# Phase 2.5: Production Deployment
# Base: Python 3.11 slim for smaller image size

FROM python:3.11-slim

# Set metadata
LABEL maintainer="rvc2mqtt"
LABEL description="RV-C to MQTT bridge with Home Assistant Discovery"
LABEL version="2.5.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (if needed for python-can or serial)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY rvc2mqtt.py .
COPY ha_discovery.py .
COPY rvc_commands.py .
COPY can_tx.py .
COPY command_handler.py .
COPY command_validator.py .
COPY audit_logger.py .
COPY mqttlog.py .
COPY rvc-spec.yml .

# Copy default configuration (will be overridden by volume mount)
COPY rvc2mqtt.ini .

# Copy mappings directory
COPY mappings/ ./mappings/

# Set timezone (can be overridden by environment variable)
ENV TZ=America/New_York

# Run as non-root user for security
# Use UID 99 and GID 100 (nobody:users) to match Unraid's standard appdata ownership
# Creating directories and setting permissions for when running without volume mounts
RUN mkdir -p /app/logs /app/audit && \
    chmod -R 777 /app/logs /app/audit
# Run as nobody:users (99:100) - Unraid standard
USER 99:100

# Health check (optional - check if process is running)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f rvc2mqtt.py || exit 1

# Entry point
CMD ["python", "-u", "rvc2mqtt.py"]
