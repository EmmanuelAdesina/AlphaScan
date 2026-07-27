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
    # Respect the cloud platform's assigned port while keeping local Docker
    # deployments on port 8000 by default.
    PORT="${PORT:-8000}"

    # Determine number of workers (default: 2, max: 4 for memory safety)
    WORKERS="${UVICORN_WORKERS:-2}"

    # Uvicorn only accepts lowercase log levels. Deployment providers commonly
    # inject values such as LOG_LEVEL=INFO, so normalize before passing it on.
    LOG_LEVEL_RAW="${LOG_LEVEL:-info}"
    UVICORN_LOG_LEVEL="$(printf '%s' "${LOG_LEVEL_RAW}" | tr '[:upper:]' '[:lower:]')"
    case "${UVICORN_LOG_LEVEL}" in
        critical|error|warning|info|debug|trace) ;;
        warn) UVICORN_LOG_LEVEL="warning" ;;
        *)
            echo "  Warning: invalid LOG_LEVEL='${LOG_LEVEL_RAW}', falling back to 'info'"
            UVICORN_LOG_LEVEL="info"
            ;;
    esac

    echo "  Mode:     Production Server"
    echo "  Port:     ${PORT}"
    echo "  Workers:  ${WORKERS}"
    echo "  Log:      ${LOG_LEVEL_RAW} (uvicorn: ${UVICORN_LOG_LEVEL})"
    echo "═══════════════════════════════════════════════"

    exec uvicorn api.routes:app \
        --host 0.0.0.0 \
        --port "${PORT}" \
        --workers "${WORKERS}" \
        --log-level "${UVICORN_LOG_LEVEL}" \
        --access-log
else
    # Pass through any custom command (e.g., one-shot scan, tests)
    exec python "$@"
fi
