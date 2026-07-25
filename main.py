"""
AlphaScan v0.5.1 - Main Application Entry Point
Starts the FastAPI server and initializes all components.

v0.5.1 changes:
  - Mandatory pre-scan API key verification (utils.api_verifier)
  - Signal-only output mode (QUIET_MODE) suppresses INFO logs
  - --quiet CLI flag mirrors QUIET_MODE=true
  - Aborts startup if any critical API key is invalid
  - --once runs a single scan cycle and exits
  - --no-report skips Discord reporting
"""
import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DEBUG, LOG_LEVEL, QUIET_MODE
from utils.config_validator import ConfigValidator
from utils.api_verifier import verify_all_api_keys, should_abort_scan


def setup_logging(quiet: bool = QUIET_MODE) -> None:
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
    effective_level = "WARNING" if quiet else LOG_LEVEL
    root_logger.setLevel(getattr(logging, effective_level, logging.INFO))
    root_logger.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("github").setLevel(logging.WARNING)
    logging.getLogger("censys").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING if quiet else logging.INFO
    )


def parse_args() -> argparse.Namespace:
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


def _print_metrics(metrics: dict) -> None:
    """Print scan metrics to stdout."""
    print("\n" + "=" * 60)
    print("  SCAN METRICS")
    print("=" * 60)
    print(f"  Assets scanned : {metrics.get('total_assets_scanned', 0)}")
    print(f"  Findings found : {metrics.get('total_findings', 0)}")
    print(f"  Secrets extracted: {metrics.get('total_secrets_extracted', 0)}")
    vr = metrics.get("validation_results", {})
    print(f"  Validated valid : {vr.get('valid', 0)}")
    print(f"  Validated invalid: {vr.get('invalid', 0)}")
    print("=" * 60 + "\n")


def _report_findings(findings) -> bool:
    """Send validated keys to Discord."""
    try:
        from reporter import send_key_report
        flat_keys = []
        for f in findings:
            for k in f.validation_results:
                flat_keys.append(k)
        if flat_keys:
            return send_key_report(flat_keys)
        return send_discord("🔑 **AlphaScan** — No validated secrets found in this scan.")
    except Exception as e:
        logging.getLogger(__name__).error(f"Reporting failed: {e}")
        return False


def run_scan_cycle(no_report: bool = False) -> dict:
    """
    Execute one full scan cycle:
      Scanners -> Parser -> Validator -> (Reporter)
    Returns metrics dict.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting scan cycle...")

    # Stage 1: Scanners
    from scanners import run_all_scanners
    findings, metrics = run_all_scanners()

    if not findings:
        logger.info("No findings collected from scanners.")
        if not no_report:
            try:
                from reporter import send_discord
                send_discord("📡 **AlphaScan** — Scan complete. No exposed assets found.")
            except Exception:
                pass
        return metrics

    # Stage 2: Parser
    from parser import parse_findings
    parsed = parse_findings(findings)

    # Stage 3: Validator
    from validator import validate_findings, get_metrics as get_validator_metrics
    validated = validate_findings(parsed)
    val_metrics = get_validator_metrics(validated)
    metrics.update(val_metrics)

    # Stage 4: Reporter
    if not no_report:
        _report_findings(validated)

    # Print metrics
    _print_metrics(metrics)
    return metrics


def main() -> None:
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
            print(f"\n❌ {verification.abort_reason}", file=sys.stderr)
            sys.exit(1)
    else:
        if not quiet:
            logger.warning("Skipping API key verification (--no-verify).")

    # ── Single scan mode ──────────────────────────────────────────────────
    if args.once:
        run_scan_cycle(no_report=args.no_report)
        sys.exit(0)

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