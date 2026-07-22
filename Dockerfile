# ── Multi-stage build for AlphaScan v0.5 ─────────────────────────────────────
# Stage 1: Builder - install dependencies
FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime - minimal image
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r apis && useradd -r -g apis apis

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# v0.5: Autonomous mode environment variables
ENV AUTONOMOUS_MODE=true
ENV AUTO_PUSH_GITHUB=true

# Create data directory
RUN mkdir -p /app/data/verified_keys && chown -R apis:apis /app

# Switch to non-root user
USER apis

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
     CMD curl -f http://localhost:8000/health || exit 1 

# Run the application
CMD ["python", "main.py"]
