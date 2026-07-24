# AlphaScan — Development / Single-file Docker Image
# Copies all .py files into a flat directory.
# For production use the root Dockerfile (multi-stage build).
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install optional eth-account for wallet derivation
RUN pip install --no-cache-dir eth-account 2>/dev/null || true

# Copy all application files
COPY *.py ./

# Run scan loop by default (single cycle, no discord report)
# For continuous mode: python -m alphascan.main
CMD ["python", "main.py", "--once", "--no-report"]