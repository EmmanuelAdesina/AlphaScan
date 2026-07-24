# AlphaScan — Production Docker Image
# Multi-stage: install deps, then run as non-root user
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system deps for crypto libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY alphascan/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: eth-account for Ethereum wallet derivation from private keys
RUN pip install --no-cache-dir eth-account 2>/dev/null || true

# ── Runtime stage ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (as a Python package: alphascan/)
COPY alphascan/ alphascan/

# Default: run a single scan cycle, then exit
# Override CMD to run continuously: python -m alphascan.main
CMD ["python", "-m", "alphascan.main", "--once", "--no-report"]