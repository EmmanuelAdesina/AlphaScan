FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install optional eth-account for wallet derivation
RUN pip install --no-cache-dir eth-account 2>/dev/null || true

# Copy app code
COPY config.py scanners.py parser.py validator.py reporter.py main.py ./

# Run scan loop by default
CMD ["python", "main.py"]