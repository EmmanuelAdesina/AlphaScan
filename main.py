"""
AlphaScan v0.5 - Main Application Entry Point
Starts the FastAPI server and initializes all components.
"""
import asyncio
import logging
import sys
from pathlib import Path

from config.settings import DEBUG, LOG_LEVEL
from utils.config_validator import ConfigValidator
from core.engine import AlphaScanEngine

# Configure structured logging
def setup_logging():
    """Configure structured logging with color formatting."""
    import colorlog

    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "critical": "red,bg_white",
        },
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("github").setLevel(logging.WARNING)
    logging.getLogger("censys").setLevel(logging.WARNING)


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting AlphaScan v0.5...")

    # Validate configuration on startup
    validator = ConfigValidator()
    report = validator.validate_all()

    if report["errors"]:
        logger.error("Configuration errors detected. Please fix before continuing:")
        for error in report["errors"]:
            logger.error(f"  {error}")

    if report["warnings"]:
        logger.warning("Configuration warnings:")
        for warning in report["warnings"]:
            logger.warning(f"  {warning}")

    logger.info("Configuration validated.")
    validator.log_report()

    # Start FastAPI server
    import uvicorn

    logger.info("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down AlphaScan...")
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)