"""
AlphaScan Parser.
Extracts secrets from raw text using Mistral API or regex fallback.
Operates on Finding objects.
"""
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import MISTRAL_API_KEY
from models import Finding

logger = logging.getLogger(__name__)

# Regex patterns for direct extraction
SSH_RSA = re.compile(r"-----BEGIN RSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END RSA PRIVATE KEY-----")
SSH_OPENSSH = re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END OPENSSH PRIVATE KEY-----")
SSH_EC = re.compile(r"-----BEGIN EC PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END EC PRIVATE KEY-----")
SSH_DSA = re.compile(r"-----BEGIN DSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END DSA PRIVATE KEY-----")
SSH_PKCS8 = re.compile(r"-----BEGIN PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END PRIVATE KEY-----")
ETH_PRIVATE = re.compile(r"0x[a-fA-F0-9]{64}")
BTC_WIF = re.compile(r"5[HJK][1-9A-HJ-NP-Za-km-z]{50}")
OPENAI_KEY = re.compile(r"sk-[a-zA-Z0-9-]{20,}")
ANTHROPIC_KEY = re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}")
AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_-]{35}")
GITHUB_KEY = re.compile(r"gh[pousr]_[a-zA-Z0-9]{36}")
GITLAB_KEY = re.compile(r"glpat-[A-Za-z0-9-]{20}")
STRIPE_LIVE = re.compile(r"sk_live_[a-zA-Z0-9]{24,}")
STRIPE_TEST = re.compile(r"sk_test_[a-zA-Z0-9]{24,}")
SENDGRID_KEY = re.compile(r"SG\.[a-zA-Z0-9_-]{40}")
GENERIC_APIKEY = re.compile(r'(?i)(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{32,})')
GENERIC_BEARER = re.compile(r'(?i)bearer\s+([a-zA-Z0-9._-]{20,})')
MONGO_URI = re.compile(r"mongodb(?:\+srv)?://[^\s]+")
POSTGRES_URI = re.compile(r"postgresql://[^\s]+")
MYSQL_URI = re.compile(r"mysql://[^\s]+")

PATTERNS = [
    ("ssh_rsa", SSH_RSA, 0),
    ("ssh_openssh", SSH_OPENSSH, 0),
    ("ssh_ec", SSH_EC, 0),
    ("ssh_dsa", SSH_DSA, 0),
    ("ssh_pkcs8", SSH_PKCS8, 0),
    ("eth_private_key", ETH_PRIVATE, 2),
    ("btc_wif", BTC_WIF, 2),
    ("stripe_live", STRIPE_LIVE, 8),
    ("stripe_test", STRIPE_TEST, 8),
    ("anthropic", ANTHROPIC_KEY, 9),
    ("openai", OPENAI_KEY, 9),
    ("aws", AWS_KEY, 7),
    ("google", GOOGLE_KEY, 7),
    ("github", GITHUB_KEY, 10),
    ("gitlab", GITLAB_KEY, 10),
    ("sendgrid", SENDGRID_KEY, 10),
    ("mongodb", MONGO_URI, 10),
    ("postgresql", POSTGRES_URI, 10),
    ("mysql", MYSQL_URI, 10),
    ("generic_bearer", GENERIC_BEARER, 10),
]

GENERIC_PATTERN = ("generic_apikey", GENERIC_APIKEY, 10)


def extract_with_regex(text: str) -> List[Dict]:
    """Extract keys from text using regex."""
    found: List[Dict] = []
    for name, pattern, rank in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            found.append({"type": name, "value": value, "rank": rank, "source": "regex"})

    for match in GENERIC_PATTERN[1].finditer(text):
        value = match.group(1) if match.groups() else match.group(0)
        if not any(f["value"] == value for f in found):
            found.append({"type": GENERIC_PATTERN[0], "value": value, "rank": GENERIC_PATTERN[2], "source": "regex"})
    return found


def _mistral_extract_single(text: str) -> List[Dict] | None:
    """Call Mistral API to extract keys from a single text."""
    if len(text) < 20:
        return None
    text = text[:24000]

    prompt = f"""Extract all API keys, private keys, secrets, tokens, and credentials from the text below.
Return ONLY a JSON array of objects, each with: "type", "value", "line".
If nothing found, return [].

TEXT:
{text}

JSON:"""

    try:
        from mistralai import Mistral
        client = Mistral(api_key=MISTRAL_API_KEY)
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            keys = json.loads(json_match.group(0))
            for k in keys:
                k["source"] = "mistral"
            return keys
        return None
    except Exception as e:
        logger.debug(f"Mistral extraction failed: {e}")
        return None


def extract_keys(text: str) -> List[Dict]:
    """Extract keys from a single text. Tries Mistral first, falls back to regex."""
    if MISTRAL_API_KEY:
        keys = _mistral_extract_single(text)
        if keys is not None:
            return keys
    return extract_with_regex(text)


def parse_findings(findings: List[Finding]) -> List[Finding]:
    """
    Main parser entry: extract secrets from each Finding.

    Returns a new list of Findings with `extracted_secrets` populated.
    Deduplicates secrets by value across all findings.
    """
    if not findings:
        return []

    start = time.time()
    seen_values: set = set()
    parsed: List[Finding] = []

    for finding in findings:
        keys = extract_keys(finding.content)
        unique_keys = []
        for k in keys:
            val = k.get("value", "")
            if val and val not in seen_values:
                seen_values.add(val)
                unique_keys.append(k)

        if unique_keys:
            finding.extracted_secrets = unique_keys
        parsed.append(finding)

    elapsed = time.time() - start
    total_secrets = sum(len(f.extracted_secrets) for f in parsed)
    logger.info(f"Parser: {total_secrets} unique secrets extracted in {elapsed:.2f}s from {len(parsed)} findings")
    return parsed