"""
AlphaScan scanners.
Modular scanner functions returning Finding objects.
Pipeline: Scanners -> Finding -> Parser -> Validator -> Reporter
"""
import logging
import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

import requests

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    CENSYS_QUERIES,
    CENSYS_QUERY_INDEX,
    CENSYS_PAT,
    CENSYS_PAGES_PER_QUERY,
    DEDUPLICATE_BY_CONTENT_HASH,
    DEDUPLICATE_BY_IP,
    DEDUPLICATE_BY_URL,
    GITHUB_SEARCH_QUERY,
    GITHUB_TOKEN,
)
from censys_client import CensysClient
from models import Finding

logger = logging.getLogger(__name__)

_USER_AGENT = "AlphaScan/1.0"

# ── Deduplication state ─────────────────────────────────────────────
_seen_ips: Set[str] = set()
_seen_urls: Set[str] = set()
_seen_hashes: Set[str] = set()


def _reset_dedup() -> None:
    """Clear dedup state for a new scan cycle."""
    _seen_ips.clear()
    _seen_urls.clear()
    _seen_hashes.clear()


def _is_duplicate(finding: Finding) -> bool:
    """Return True if this finding should be skipped."""
    if DEDUPLICATE_BY_IP and finding.target in _seen_ips:
        return True
    if DEDUPLICATE_BY_URL and finding.target.startswith(("http://", "https://")) and finding.target in _seen_urls:
        return True
    if DEDUPLICATE_BY_CONTENT_HASH and finding.content_hash in _seen_hashes:
        return True
    return False


def _record(finding: Finding) -> None:
    if DEDUPLICATE_BY_IP:
        _seen_ips.add(finding.target)
    if DEDUPLICATE_BY_URL and finding.target.startswith(("http://", "https://")):
        _seen_urls.add(finding.target)
    if DEDUPLICATE_BY_CONTENT_HASH:
        _seen_hashes.add(finding.content_hash)


# ── Censys scanner ─────────────────────────────────────────────────

def scan_censys(per_query_pages: int = CENSYS_PAGES_PER_QUERY) -> List[Finding]:
    """
    Run Censys secret-discovery queries with pagination.

    Returns list of Finding objects.
    """
    findings: List[Finding] = []
    if not CENSYS_PAT:
        logger.warning("Censys not configured (CENSYS_PAT missing), skipping")
        return findings

    client = CensysClient(pat=CENSYS_PAT)

    # Use current query from rotation
    query_index = CENSYS_QUERY_INDEX % len(CENSYS_QUERIES)
    query = CENSYS_QUERIES[query_index]
    logger.info(f"Censys query [{query_index+1}/{len(CENSYS_QUERIES)}]: {query}")

    cursor = None
    pages = 0
    try:
        while pages < per_query_pages:
            pages += 1
            resp = client.search_hosts(query, per_page=50, cursor=cursor)
            hits = resp.get("hits", [])

            for hit in hits:
                ip = hit.get("ip", "unknown")
                services = hit.get("services", [])

                # Dedup by IP
                if DEDUPLICATE_BY_IP and ip in _seen_ips:
                    continue

                # Build a representative target string
                target = ip
                for svc in services:
                    port = svc.get("port")
                    if port:
                        target = f"{ip}:{port}"
                        break

                # Extract HTTP responses
                raw_bodies: List[str] = []
                for svc in services:
                    # HTTP response body
                    http_data = svc.get("http", {})
                    body = http_data.get("response", {}).get("body", "")
                    if body and len(body) > 20:
                        raw_bodies.append(body)

                    # Exposed service note on common API ports
                    port = svc.get("port", 0)
                    if port in (11434, 7860, 8000, 8080, 5000, 3000, 27017, 5432, 3306, 6379):
                        note = f"Exposed service on port {port}: {svc.get('service_name', 'unknown')}"
                        raw_bodies.append(note)

                if not raw_bodies:
                    continue

                # One finding per host (combine bodies)
                combined = "\n".join(raw_bodies)
                finding = Finding(
                    source="censys",
                    target=target,
                    content=combined,
                    metadata={
                        "query": query,
                        "query_index": query_index,
                        "services_count": len(services),
                        "ip": ip,
                    },
                )

                if not _is_duplicate(finding):
                    _record(finding)
                    findings.append(finding)

            cursor = resp.get("cursor")
            if not cursor or not hits:
                break

    except Exception as e:
        logger.error(f"Censys scan failed: {e}")

    logger.info(f"Censys scan collected {len(findings)} findings")
    return findings


# ── GitHub scanner ─────────────────────────────────────────────────

def scan_github(max_files: int = 15) -> List[Finding]:
    """
    Search GitHub public repos for files containing potential secrets.
    Returns list of Finding objects.
    """
    findings: List[Finding] = []
    if not GITHUB_TOKEN:
        logger.warning("GitHub not configured, skipping")
        return findings

    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": _USER_AGENT,
        }

        url = "https://api.github.com/search/code"
        params = {"q": GITHUB_SEARCH_QUERY, "per_page": 30}

        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"GitHub API returned {resp.status_code}: {resp.text[:200]}")
            return findings

        data = resp.json()
        items = data.get("items", [])
        logger.info(f"GitHub search found {len(items)} matching files")

        count = 0
        for item in items:
            if count >= max_files:
                break
            try:
                raw_url = item.get("html_url", "").replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                if not raw_url:
                    continue
                content_resp = requests.get(raw_url, headers={"User-Agent": _USER_AGENT}, timeout=10)
                if content_resp.status_code == 200 and len(content_resp.text) > 10:
                    repo = item.get("repository", {}).get("full_name", "unknown")
                    path = item.get("path", "unknown")
                    target = f"https://github.com/{repo}/blob/{path}"

                    finding = Finding(
                        source="github",
                        target=target,
                        content=content_resp.text,
                        metadata={
                            "repo": repo,
                            "path": path,
                            "html_url": item.get("html_url", ""),
                        },
                    )

                    if not _is_duplicate(finding):
                        _record(finding)
                        findings.append(finding)
                        count += 1
            except requests.RequestException:
                continue

    except requests.RequestException as e:
        logger.error(f"GitHub scan failed: {e}")
    except Exception as e:
        logger.error(f"GitHub scan error: {e}")

    logger.info(f"GitHub scan collected {len(findings)} findings")
    return findings


# ── Pastebin scanner ───────────────────────────────────────────────

def scan_pastebin(max_pastes: int = 15) -> List[Finding]:
    """
    Scrape Pastebin for new public pastes that may contain secrets.
    Returns list of Finding objects.
    """
    findings: List[Finding] = []
    try:
        resp = requests.get("https://pastebin.com/archive", headers={"User-Agent": _USER_AGENT}, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Pastebin archive returned {resp.status_code}")
            return findings

        # Extract paste IDs
        paste_ids = re.findall(r'/raw/([a-zA-Z0-9]{8})', resp.text)
        if not paste_ids:
            paste_ids = re.findall(r'pastebin\.com/([a-zA-Z0-9]{8})', resp.text)

        # Dedup IDs
        seen_ids: Set[str] = set()
        unique_ids: List[str] = []
        for pid in paste_ids:
            if pid not in seen_ids:
                seen_ids.add(pid)
                unique_ids.append(pid)

        logger.info(f"Pastebin found {len(unique_ids)} recent pastes")

        count = 0
        for pid in unique_ids[:max_pastes]:
            try:
                raw_url = f"https://pastebin.com/raw/{pid}"
                paste_resp = requests.get(raw_url, headers={"User-Agent": _USER_AGENT}, timeout=5)
                if paste_resp.status_code == 200 and len(paste_resp.text) > 20:
                    target = f"https://pastebin.com/raw/{pid}"
                    finding = Finding(
                        source="pastebin",
                        target=target,
                        content=paste_resp.text,
                        metadata={"paste_id": pid},
                    )
                    if not _is_duplicate(finding):
                        _record(finding)
                        findings.append(finding)
                        count += 1
            except requests.RequestException:
                continue

    except requests.RequestException as e:
        logger.warning(f"Pastebin scan failed: {e}")
    except Exception as e:
        logger.error(f"Pastebin scan error: {e}")

    logger.info(f"Pastebin scan collected {len(findings)} findings")
    return findings


# ── Orchestration ──────────────────────────────────────────────────

def run_all_scanners() -> Tuple[List[Finding], dict]:
    """
    Run all configured scanners and return combined findings + metrics.

    Returns:
        (findings, metrics)
    """
    _reset_dedup()
    all_findings: List[Finding] = []

    metrics = {
        "censys": {"scanned": 0, "findings": 0},
        "github": {"scanned": 0, "findings": 0},
        "pastebin": {"scanned": 0, "findings": 0},
        "total_assets_scanned": 0,
        "total_findings": 0,
        "total_secrets_extracted": 0,
        "validation_results": {"valid": 0, "invalid": 0, "skipped": 0},
    }

    # Censys
    try:
        censys_findings = scan_censys()
        all_findings.extend(censys_findings)
        metrics["censys"]["findings"] = len(censys_findings)
        metrics["censys"]["scanned"] = 1
    except Exception as e:
        logger.error(f"Censys scanner error: {e}")

    # GitHub
    try:
        github_findings = scan_github()
        all_findings.extend(github_findings)
        metrics["github"]["findings"] = len(github_findings)
        metrics["github"]["scanned"] = 1
    except Exception as e:
        logger.error(f"GitHub scanner error: {e}")

    # Pastebin
    try:
        pastebin_findings = scan_pastebin()
        all_findings.extend(pastebin_findings)
        metrics["pastebin"]["findings"] = len(pastebin_findings)
        metrics["pastebin"]["scanned"] = 1
    except Exception as e:
        logger.error(f"Pastebin scanner error: {e}")

    metrics["total_findings"] = len(all_findings)
    metrics["total_assets_scanned"] = (
        metrics["censys"]["scanned"] + metrics["github"]["scanned"] + metrics["pastebin"]["scanned"]
    )

    return all_findings, metrics