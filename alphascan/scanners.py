"""
AlphaScan scanners.
Three simple scan functions: censys, github, pastebin.
No classes. No base classes. No abstractions.
"""
import logging
import re
from typing import List

import requests

from alphascan.config import (
    CENSYS_API_ID, CENSYS_API_SECRET, CENSYS_QUERY,
    GITHUB_TOKEN, GITHUB_SEARCH_QUERY,
)

logger = logging.getLogger(__name__)

_USER_AGENT = "AlphaScan/1.0"


def scan_censys() -> List[str]:
    """
    Scan Censys free tier for exposed API keys/secrets.
    Returns list of raw text snippets found.
    """
    if not CENSYS_API_ID or not CENSYS_API_SECRET:
        logger.warning("Censys not configured, skipping")
        return []

    results: List[str] = []
    try:
        auth = (CENSYS_API_ID, CENSYS_API_SECRET)
        url = "https://search.censys.io/api/v2/hosts/search"
        params = {"q": CENSYS_QUERY, "per_page": 25}

        resp = requests.get(url, auth=auth, params=params, timeout=15, headers={"User-Agent": _USER_AGENT})
        if resp.status_code != 200:
            logger.warning(f"Censys API returned {resp.status_code}: {resp.text[:200]}")
            return results

        data = resp.json()
        for hit in data.get("result", {}).get("hits", []):
            # Collect HTTP response bodies
            services = hit.get("services", [])
            for svc in services:
                http_data = svc.get("http", {})
                body = http_data.get("response", {}).get("body", "")
                if body and len(body) > 20:
                    results.append(body)
                # Also note exposed services on common API ports
                port = svc.get("port", 0)
                if port in (11434, 7860, 8000, 8080, 5000, 3000):
                    results.append(f"Exposed service on port {port}: {svc.get('service_name', 'unknown')}")

    except requests.RequestException as e:
        logger.error(f"Censys scan failed: {e}")
    except Exception as e:
        logger.error(f"Censys scan error: {e}")

    logger.info(f"Censys scan found {len(results)} raw snippets")
    return results


def scan_github() -> List[str]:
    """
    Search GitHub public repos for files containing potential secrets.
    Returns list of raw file contents found.
    """
    if not GITHUB_TOKEN:
        logger.warning("GitHub not configured, skipping")
        return []

    results: List[str] = []
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": _USER_AGENT,
        }

        # Search code via GitHub API
        url = "https://api.github.com/search/code"
        params = {"q": GITHUB_SEARCH_QUERY, "per_page": 30}

        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"GitHub API returned {resp.status_code}: {resp.text[:200]}")
            return results

        data = resp.json()
        items = data.get("items", [])
        logger.info(f"GitHub search found {len(items)} matching files")

        for item in items:
            try:
                # Fetch raw content
                raw_url = item.get("html_url", "").replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                if not raw_url:
                    continue
                content_resp = requests.get(raw_url, headers={"User-Agent": _USER_AGENT}, timeout=10)
                if content_resp.status_code == 200 and len(content_resp.text) > 10:
                    results.append(content_resp.text)
            except requests.RequestException:
                continue

    except requests.RequestException as e:
        logger.error(f"GitHub scan failed: {e}")
    except Exception as e:
        logger.error(f"GitHub scan error: {e}")

    logger.info(f"GitHub scan fetched {len(results)} file contents")
    return results


def scan_pastebin() -> List[str]:
    """
    Scrape Pastebin for new public pastes that may contain secrets.
    Returns list of raw paste content.
    """
    results: List[str] = []
    try:
        # Get recent public pastes page
        resp = requests.get("https://pastebin.com/archive", headers={"User-Agent": _USER_AGENT}, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Pastebin archive returned {resp.status_code}")
            return results

        # Extract paste IDs from the page
        paste_ids = re.findall(r'/raw/([a-zA-Z0-9]{8})', resp.text)
        if not paste_ids:
            # Try alternative pattern
            paste_ids = re.findall(r'pastebin\.com/([a-zA-Z0-9]{8})', resp.text)

        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for pid in paste_ids:
            if pid not in seen:
                seen.add(pid)
                unique_ids.append(pid)

        logger.info(f"Pastebin found {len(unique_ids)} recent pastes")

        # Fetch first 15 paste contents
        for pid in unique_ids[:15]:
            try:
                raw_url = f"https://pastebin.com/raw/{pid}"
                paste_resp = requests.get(raw_url, headers={"User-Agent": _USER_AGENT}, timeout=5)
                if paste_resp.status_code == 200 and len(paste_resp.text) > 20:
                    results.append(paste_resp.text)
            except requests.RequestException:
                continue

    except requests.RequestException as e:
        logger.warning(f"Pastebin scan failed: {e}")
    except Exception as e:
        logger.error(f"Pastebin scan error: {e}")

    logger.info(f"Pastebin scan fetched {len(results)} paste contents")
    return results


def run_all_scanners() -> List[str]:
    """Run all configured scanners and return combined raw data."""
    raw_data: List[str] = []
    raw_data.extend(scan_censys())
    raw_data.extend(scan_github())
    raw_data.extend(scan_pastebin())
    return raw_data