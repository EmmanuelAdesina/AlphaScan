# =============================================================================
# AlphaScan — Production Dockerfile
# =============================================================================
# Multi-stage build:
#   Stage 1 (frontend-builder): Builds the Next.js frontend
#   Stage 2 (production): Python runtime with backend + static frontend
#
# Build:  docker build -t alphascan .
# Run:    docker run --env-file .env -p 8000:8000 alphascan
# Or use: docker compose up
# =============================================================================

# ── Stage 1: Frontend builder ───────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy dependency manifests first for layer caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy the rest of the frontend source
COPY frontend/ ./

# Build the Next.js static export (output: 'export' writes to out/)
RUN npm run build

# ── Stage 2: Production Python image ─────────────────────────────────────────
FROM python:3.11-slim AS production

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for security (non-root user)
RUN groupadd -r alphascan && \
    useradd -r -g alphascan -s /sbin/nologin alphascan

WORKDIR /app

# Install production Python dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy backend application code
COPY main.py config.py models.py storage.py metrics.py ./
COPY scanners.py parser.py validator.py reporter.py ./
COPY pipeline.py confidence.py deduplication.py ./
COPY context_extraction.py secret_families.py provider_verifiers.py ./
COPY censys_client.py daily_export.py ./
COPY api/ ./api/
COPY utils/ ./utils/

# Copy the pre-built frontend from the frontend-builder stage
COPY --from=frontend-builder /app/frontend/out/ ./static/

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create data directories with correct permissions
RUN mkdir -p /app/data /app/exports && \
    chown -R alphascan:alphascan /app

# Switch to non-root user
USER alphascan

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
ENTRYPOINT ["./entrypoint.sh"]
