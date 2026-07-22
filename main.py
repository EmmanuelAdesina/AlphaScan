"""
Main entry point for APIS.
Starts the FastAPI server and optionally the autonomous engine.
"""
import logging
import sys
import os
from pathlib import Path

# Ensure the project root is in the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DEBUG, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("apis")


def main():
    """Main entry point."""
    import uvicorn

    # Start the FastAPI server
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
