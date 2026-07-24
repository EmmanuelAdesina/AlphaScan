"""
AlphaScan — Main Entry Point.
Simple scan loop: scan → parse → validate → report.
No self-improvement. No code generation. No push. Just scan.
"""
import argparse
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List

from alphascan.config import SCAN_INTERVAL, check_config, CENSYS_PAT
from alphascan.scanners import run_all_scanners
from alphascan.parser import extract_keys
from alphascan.validator import validate_keys
from alphascan.reporter import send_key_report, send_status, send_error, send_info
from alphascan.censys_client import CensysClient

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging. Quiet by default; verbose shows info."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def run_scan_cycle(cycle: int) -> Dict:
    """
    Execute one complete scan cycle.
    Returns summary dict.
    """
    start = time.time()

    # 1. Scan
    raw_data = run_all_scanners()
    scanners_used = []
    if raw_data:
        scanners_used = ["censys", "github", "pastebin"]

    logger.info(f"Cycle {cycle}: collected {len(raw_data)} raw text segments")

    # 2. Parse with LLM
    keys = extract_keys(raw_data)
    logger.info(f"Cycle {cycle}: extracted {len(keys)} potential keys")

    # 3. Validate
    validated = validate_keys(keys)
    valid_keys = [k for k in validated if k.get("valid", False)]
    invalid_keys = [k for k in validated if not k.get("valid", False)]
    logger.info(f"Cycle {cycle}: {len(valid_keys)} valid, {len(invalid_keys)} invalid")

    elapsed = time.time() - start

    summary = {
        "cycle": cycle,
        "duration": round(elapsed, 1),
        "raw_segments": len(raw_data),
        "extracted": len(keys),
        "valid": len(valid_keys),
        "invalid": len(invalid_keys),
        "validated_keys": validated,
        "scanners_used": scanners_used,
    }
    return summary


def main_loop(once: bool = False, verbose: bool = False, no_report: bool = False) -> None:
    """Main scan loop. Runs once or continuously."""
    setup_logging(verbose)

    logger.info("AlphaScan starting...")
    config_status = check_config()
    print("\n=== AlphaScan Configuration ===")
    for service, configured in config_status.items():
        status = "[OK]" if configured else "[!!]"
        print(f"  {status} {service}: {'configured' if configured else 'not configured'}")
    print()

    if not any(config_status.values()):
        print("[!!] No services configured. Create a .env file with your API keys.")
        print("   See .env.example for required keys.")
        sys.exit(1)

    # Validate Censys PAT at startup
    if config_status.get("censys"):
        print("  [*] Validating Censys PAT...")
        try:
            client = CensysClient(pat=CENSYS_PAT)
            if client.verify_auth():
                print("  [OK] Censys PAT is valid.")
            else:
                print("  [!!] Censys PAT is invalid or expired. Censys scanner will be disabled.")
                print("       Generate a new PAT at https://console.censys.io/api")
                config_status["censys"] = False
        except Exception as e:
            print(f"  [!!] Censys validation failed: {e}. Censys scanner will be disabled.")
            config_status["censys"] = False
    print()

    # Notify Discord we're online
    configured_services = [s for s, c in config_status.items() if c]
    send_info(
        f"AlphaScan initialized - {', '.join(configured_services)} configured"
        "\nSystem ready. Scanning cycle starts now."
    )

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n{'='*50}")
            print(f"  Cycle #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")

            summary = run_scan_cycle(cycle)

            # Print summary
            print(f"\n  [SUMMARY]")
            print(f"     Raw segments: {summary['raw_segments']}")
            print(f"     Keys extracted: {summary['extracted']}")
            print(f"     Valid: {summary['valid']}  Invalid: {summary['invalid']}")
            print(f"     Duration: {summary['duration']}s")

            # Report top findings
            if summary["validated_keys"]:
                valid = [k for k in summary["validated_keys"] if k.get("valid")]
                if valid:
                    print(f"\n  [TOP FINDINGS] (rank 0=critical, 10=lowest):")
                    for key in sorted(valid, key=lambda k: k.get("rank", 10))[:5]:
                        rank = key.get("rank", 10)
                        key_type = key.get("type", "unknown")
                        value_preview = key.get("value", "")[:12]
                        print(f"     [{rank}] {key_type}: {value_preview}...")

            # Send Discord report
            if not no_report:
                send_status(
                    cycle,
                    summary["duration"],
                    summary["valid"],
                    summary["scanners_used"],
                )
                if summary["validated_keys"]:
                    send_key_report(summary["validated_keys"])

            if once:
                print("\n[DONE] Single scan complete. Exiting.")
                break

            print(f"\n  Sleeping {SCAN_INTERVAL}s until next cycle...")
            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Scan stopped by user.")
        send_info("AlphaScan stopped by user.")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        send_error(str(e), "main loop")
        raise


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AlphaScan - Secret scanning and key intelligence system"
    )
    parser.add_argument(
        "--once", "-1",
        action="store_true",
        help="Run a single scan cycle and exit",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed debug output",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip Discord reporting (print to console only)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main_loop(once=args.once, verbose=args.verbose, no_report=args.no_report)