"""
AlphaScan Groq LLM Parser.
Uses Groq API to extract API keys, secrets, and credentials from raw text.
No classes. No fallback chains. Just Groq + regex fallback.
"""
import json
import logging
import re
import time
from typing import Dict, List, Optional

from alphascan.config import GROQ_API_KEY

logger = logging.getLogger(__name__)


# ── Regex patterns for direct extraction (fallback + supplement) ──

# SSH keys
SSH_RSA = re.compile(r"-----BEGIN RSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END RSA PRIVATE KEY-----")
SSH_OPENSSH = re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END OPENSSH PRIVATE KEY-----")
SSH_EC = re.compile(r"-----BEGIN EC PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END EC PRIVATE KEY-----")
SSH_DSA = re.compile(r"-----BEGIN DSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END DSA PRIVATE KEY-----")

# Crypto
ETH_PRIVATE = re.compile(r"0x[a-fA-F0-9]{64}")
BTC_WIF = re.compile(r"5[HJK][1-9A-HJ-NP-Za-km-z]{50}")

# API keys
OPENAI_KEY = re.compile(r"sk-[a-zA-Z0-9-]{20,}")
ANTHROPIC_KEY = re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}")
AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_-]{35}")
GITHUB_KEY = re.compile(r"gh[pousr]_[a-zA-Z0-9]{36}")
GITLAB_KEY = re.compile(r"glpat-[A-Za-z0-9-]{20}")
STRIPE_LIVE = re.compile(r"sk_live_[a-zA-Z0-9]{24,}")
STRIPE_TEST = re.compile(r"sk_test_[a-zA-Z0-9]{24,}")
SENDGRID_KEY = re.compile(r"SG\.[a-zA-Z0-9_-]{40}")

# Generic
GENERIC_APIKEY = re.compile(r'(?i)(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{32,})')
GENERIC_BEARER = re.compile(r'(?i)bearer\s+([a-zA-Z0-9._-]{20,})')

# Connection strings
MONGO_URI = re.compile(r"mongodb(?:\+srv)?://[^\s]+")
POSTGRES_URI = re.compile(r"postgresql://[^\s]+")
MYSQL_URI = re.compile(r"mysql://[^\s]+")

# ── Pattern list with type name and rank (0=critical, 10=lowest) ──

PATTERNS = [
    ("ssh_rsa", SSH_RSA, 0),
    ("ssh_openssh", SSH_OPENSSH, 0),
    ("ssh_ec", SSH_EC, 0),
    ("ssh_dsa", SSH_DSA, 0),
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

# Dynamic pattern catch-all for generic apikey patterns
GENERIC_PATTERN = ("generic_apikey", GENERIC_APIKEY, 10)


def extract_with_regex(text: str) -> List[Dict]:
    """Extract any matching keys from a single text using regex patterns."""
    found: List[Dict] = []
    for name, pattern, rank in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            found.append({
                "type": name,
                "value": value,
                "rank": rank,
                "source": "regex",
            })

    # Also check generic API key pattern
    for match in GENERIC_PATTERN[1].finditer(text):
        value = match.group(1) if match.groups() else match.group(0)
        # Avoid duplicates with more specific patterns
        if not any(f["value"] == value for f in found):
            found.append({
                "type": GENERIC_PATTERN[0],
                "value": value,
                "rank": GENERIC_PATTERN[2],
                "source": "regex",
            })

    return found


def extract_with_groq(texts: List[str]) -> List[Dict]:
    """
    Use Groq API (mixtral-8x7b) to extract keys from raw text.
    Returns list of extracted key dicts.
    Falls back to regex on failure.
    """
    if not GROQ_API_KEY:
        logger.info("No Groq API key configured, using regex fallback")
        return _extract_regex_batch(texts)

    if not texts:
        return []

    start = time.time()
    all_keys: List[Dict] = []

    for text in texts:
        try:
            keys = _groq_extract_single(text)
            if keys:
                all_keys.extend(keys)
        except Exception as e:
            logger.debug(f"Groq extraction failed for segment: {e}")
            # Fallback to regex for this segment
            all_keys.extend(extract_with_regex(text))

    elapsed = time.time() - start
    logger.info(f"Groq extraction: {len(all_keys)} keys in {elapsed:.2f}s")
    return all_keys


def _groq_extract_single(text: str) -> Optional[List[Dict]]:
    """
    Call Groq API to extract keys from a single text.
    Uses mixtral-8x7b-32768 for its large context window.
    """
    if len(text) < 20:
        return None

    # Truncate if necessary (Groq has 32k limit, but we keep it reasonable)
    if len(text) > 24000:
        text = text[:24000]

    prompt = f"""Extract all API keys, private keys, secrets, tokens, and credentials from the text below.
Return ONLY a JSON array of objects, each with: "type", "value", "line" (the line or context snippet).
If nothing found, return empty array [].

Examples of what to extract:
- API keys (sk-..., AKIA..., AIza..., gh[pousr]_..., etc.)
- Private keys (-----BEGIN ... PRIVATE KEY-----)
- Cryptocurrency private keys (0x... 64 hex chars)
- Connection strings (mongodb://, postgresql://, mysql://)
- Bearer tokens, access tokens, secret keys
- Any key=value pairs that look like credentials

TEXT TO ANALYZE:
{text}

JSON OUTPUT:"""

    try:
        import groq
        client = groq.Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        # Try to extract JSON array from response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            keys = json.loads(json_match.group(0))
            # Add source field
            for k in keys:
                k["source"] = "groq"
            return keys

        return None

    except Exception as e:
        logger.debug(f"Groq API call failed: {e}")
        return None


def _extract_regex_batch(texts: List[str]) -> List[Dict]:
    """Extract keys from multiple texts using regex only."""
    all_keys: List[Dict] = []
    seen_values: set = set()

    for text in texts:
        keys = extract_with_regex(text)
        for k in keys:
            if k["value"] not in seen_values:
                seen_values.add(k["value"])
                if "source" not in k:
                    k["source"] = "regex"
                all_keys.append(k)

    return all_keys


def extract_keys(texts: List[str]) -> List[Dict]:
    """
    Main entry point: extract keys from raw texts.
    Tries Groq first, falls back to regex.
    Deduplicates results.
    """
    keys = extract_with_groq(texts)
    if not keys:
        keys = _extract_regex_batch(texts)

    # Deduplicate by value
    seen: set = set()
    unique: List[Dict] = []
    for k in keys:
        if k["value"] not in seen:
            seen.add(k["value"])
            unique.append(k)

    return unique