"""
AlphaScan v0.5.1 - Main Application Entry Point
Starts the FastAPI server and initializes all components.

v0.5.1 changes:
  - Mandatory pre-scan API key verification (utils.api_verifier)
  - Signal-only output mode (QUIET_MODE) suppresses INFO logs
  - --quiet CLI flag mirrors QUIET_MODE=true
  - Aborts startup if any critical API key is invalid
"""
import argparse
import logging
import sys

from config import DEBUG, LOG_LEVEL, QUIET_MODE
from utils.config_validator import ConfigValidator
from utils.api_verifier import verify_all_api_keys, should_abort_scan


def setup_logging(quiet: bool = QUIET_MODE) -> None:
    """Configure structured logging with color formatting.

    When *quiet* is True (the default for production), INFO-level logs are
    suppressed entirely so that only warnings, errors, and the final
    intelligence report are emitted.
    """
    import colorlog

    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # In quiet mode, raise the floor to WARNING so INFO logs are hidden.
    effective_level = "WARNING" if quiet else LOG_LEVEL
    root_logger.setLevel(getattr(logging, effective_level, logging.INFO))
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers regardless of mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("github").setLevel(logging.WARNING)
    logging.getLogger("censys").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING if quiet else logging.INFO
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="AlphaScan v0.5.1 Secret Intelligence System")
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Run completely silent except for the final report and fatal errors.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        default=False,
        help="Skip pre-scan API key verification (not recommended).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run a single scan cycle and exit (no continuous loop).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Skip Discord reporting for this run.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    quiet = args.quiet or QUIET_MODE

    setup_logging(quiet=quiet)
    logger = logging.getLogger(__name__)

    if not quiet:
        logger.info("Starting AlphaScan v0.5.1...")

    # Validate configuration on startup (non-network checks)
    validator = ConfigValidator()
    report = validator.validate_all()

    if report["errors"] and not quiet:
        logger.error("Configuration errors detected. Please fix before continuing:")
        for error in report["errors"]:
            logger.error(f"  {error}")

    if report["warnings"] and not quiet:
        logger.warning("Configuration warnings:")
        for warning in report["warnings"]:
            logger.warning(f"  {warning}")

    if not quiet:
        logger.info("Configuration validated.")
    validator.log_report()

    # ── Mandatory pre-scan API key verification ────────────────────────────
    if not args.no_verify:
        verification = verify_all_api_keys()
        if should_abort_scan(verification):
            # Critical key invalid – abort with descriptive error.
            print(f"\n❌ {verification.abort_reason}", file=sys.stderr)
            sys.exit(1)
    else:
        if not quiet:
            logger.warning("Skipping API key verification (--no-verify).")

    # Start FastAPI server
    import uvicorn

    if not quiet:
        logger.info("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(
        "api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level="warning" if quiet else LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down AlphaScan...")
    except SystemExit:
        raise
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)