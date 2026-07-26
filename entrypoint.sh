#!/bin/sh
# =============================================================================
# AlphaScan — Production Entrypoint
# =============================================================================
# Starts the FastAPI server with production-grade settings.
# Override with: docker run alphascan python main.py --once --no-report
# =============================================================================
set -e

echo "═══════════════════════════════════════════════"
echo "  AlphaScan v0.5.1 — Starting"
echo "═══════════════════════════════════════════════"

# Default to server mode if no arguments provided
if [ "$#" -eq 0 ]; then
    # Determine number of workers (default: 2, max: 4 for memory safety)
    WORKERS="${UVICORN_WORKERS:-2}"

    echo "  Mode:     Production Server"
    echo "  Port:     8000"
    echo "  Workers:  ${WORKERS}"
    echo "  Log:      ${LOG_LEVEL:-INFO}"
    echo "═══════════════════════════════════════════════"

    exec uvicorn api.routes:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers "${WORKERS}" \
        --log-level "${LOG_LEVEL:-info}" \
        --access-log
else
    # Pass through any custom command (e.g., one-shot scan, tests)
    exec python "$@"
fi
