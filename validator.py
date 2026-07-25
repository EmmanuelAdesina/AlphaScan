"""
AlphaScan Key Validator.
Three-layer validation: format check, entropy analysis, and (for crypto) Etherscan balance check.
No classes. Simple functions.
"""
import logging
import math
import re
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

import requests

from config import ETHERSCAN_API_KEY

logger = logging.getLogger(__name__)


# ── Layer 1: Format Validation ────────────────────────────────────

# Minimum length requirements per key type
MIN_LENGTHS = {
    "ssh_rsa": 100,
    "ssh_openssh": 100,
    "ssh_ec": 100,
    "ssh_dsa": 100,
    "eth_private_key": 64,
    "btc_wif": 51,
    "openai": 20,
    "anthropic": 20,
    "aws": 20,
    "google": 35,
    "github": 36,
    "gitlab": 20,
    "stripe_live": 24,
    "stripe_test": 24,
    "sendgrid": 40,
    "mongodb": 10,
    "postgresql": 10,
    "mysql": 10,
    "generic_apikey": 32,
    "generic_bearer": 20,
}

# Prefix validation per key type
PREFIXES = {
    "openai": "sk-",
    "anthropic": "sk-ant-",
    "aws": "AKIA",
    "google": "AIza",
    "github": "ghp_",
    "gitlab": "glpat-",
    "stripe_live": "sk_live_",
    "stripe_test": "sk_test_",
    "sendgrid": "SG.",
    "eth_private_key": "0x",
    "btc_wif": ("5H", "5J", "5K"),
}


def check_format(key: Dict) -> Tuple[bool, str]:
    """
    Validate key format based on type.
    Returns (is_valid, reason).
    """
    key_type = key.get("type", "")
    value = key.get("value", "")

    if not value:
        return False, "empty value"

    # Check minimum length
    min_len = MIN_LENGTHS.get(key_type, 10)
    if len(value) < min_len:
        return False, f"too short ({len(value)} < {min_len})"

    # Check prefix
    prefix = PREFIXES.get(key_type)
    if prefix:
        if isinstance(prefix, tuple):
            if not value.startswith(prefix):
                return False, f"prefix mismatch (expected one of {prefix})"
        else:
            if not value.startswith(prefix):
                return False, f"prefix mismatch (expected '{prefix}')"

    # SSH key format check
    if key_type.startswith("ssh_"):
        if not value.startswith("-----BEGIN"):
            return False, "missing BEGIN marker"
        if not value.strip().endswith("-----"):
            return False, "missing END marker"

    # Ethereum private key: exactly 64 hex chars after 0x
    if key_type == "eth_private_key":
        hex_part = value[2:] if value.startswith("0x") else value
        if len(hex_part) != 64:
            return False, f"wrong length ({len(hex_part)} != 64)"
        if not re.match(r'^[a-fA-F0-9]{64}$', hex_part):
            return False, "invalid hex characters"

    return True, "format OK"


# ── Layer 2: Entropy Analysis ─────────────────────────────────────

def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0
    freq = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def check_entropy(key: Dict) -> Tuple[bool, float, str]:
    """
    Check if key has sufficient entropy.
    Returns (is_suspicious, entropy_value, category).
    Entropy is advisory only — format-valid keys are not rejected for low entropy.
    """
    value = key.get("value", "")
    entropy = calculate_entropy(value)

    if entropy >= 4.0:
        category = "high"
    elif entropy >= 3.0:
        category = "medium"
    elif entropy >= 1.5:
        category = "low_medium"
    else:
        category = "low"

    # Only flag as suspicious if entropy is extremely low (< 1.5)
    # This catches obvious fake/test data without rejecting valid keys
    is_suspicious = entropy < 1.5
    return is_suspicious, entropy, category


# ── Layer 3: Etherscan Balance Check (for crypto keys) ────────────

def derive_address_from_private_key(private_key_hex: str) -> Optional[str]:
    """
    Derive Ethereum address from a private key hex string.
    Uses eth_account library if available.
    """
    try:
        from eth_account import Account
        # Remove 0x prefix if present
        key_hex = private_key_hex[2:] if private_key_hex.startswith("0x") else private_key_hex
        account = Account.from_key(key_hex)
        return account.address
    except ImportError:
        logger.debug("eth_account not installed, cannot derive address")
        return None
    except Exception as e:
        logger.debug(f"Failed to derive address: {e}")
        return None


def check_etherscan_balance(address: str) -> Optional[Dict]:
    """
    Check wallet balance via Etherscan API.
    Returns dict with balance info or None on failure.
    """
    if not ETHERSCAN_API_KEY:
        logger.debug("Etherscan API key not configured")
        return None

    try:
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": 1,
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": ETHERSCAN_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Etherscan returned {resp.status_code}")
            return None

        data = resp.json()
        if data.get("status") != "1":
            logger.debug(f"Etherscan error: {data.get('message', 'unknown')}")
            return None

        balance_wei = int(data.get("result", "0"))
        balance_eth = balance_wei / 1e18

        return {
            "address": address,
            "balance_wei": balance_wei,
            "balance_eth": balance_eth,
            "has_funds": balance_eth > 0,
        }

    except requests.RequestException as e:
        logger.debug(f"Etherscan request failed: {e}")
        return None
    except Exception as e:
        logger.debug(f"Etherscan check error: {e}")
        return None


def check_crypto_balance(key: Dict) -> Optional[Dict]:
    """
    Check if a crypto private key has a non-zero wallet balance.
    Only works for Ethereum-compatible keys.
    """
    key_type = key.get("type", "")
    value = key.get("value", "")

    if key_type not in ("eth_private_key",):
        return None

    address = derive_address_from_private_key(value)
    if not address:
        return None

    balance = check_etherscan_balance(address)
    return balance


# ── Main Validation Pipeline ──────────────────────────────────────

def validate_key(key: Dict) -> Dict:
    """
    Run all validation layers on a single key.
    Returns enriched key dict with validation results.
    """
    result = dict(key)

    # Layer 1: Format
    format_ok, format_reason = check_format(key)
    result["format_valid"] = format_ok
    result["format_reason"] = format_reason

    if not format_ok:
        result["valid"] = False
        result["validation_summary"] = f"FAILED format: {format_reason}"
        return result

    # Layer 2: Entropy (advisory — format-valid keys pass regardless)
    entropy_suspicious, entropy_val, entropy_cat = check_entropy(key)
    result["entropy"] = round(entropy_val, 2)
    result["entropy_category"] = entropy_cat
    result["entropy_suspicious"] = entropy_suspicious
    result["entropy_valid"] = not entropy_suspicious

    # Layer 3: Etherscan (crypto only)
    if key.get("type") == "eth_private_key":
        balance = check_crypto_balance(key)
        if balance:
            result["wallet_address"] = balance["address"]
            result["wallet_balance_eth"] = balance["balance_eth"]
            result["wallet_has_funds"] = balance["has_funds"]
            if balance["has_funds"]:
                result["valid"] = True
                result["validation_summary"] = f"PASSED (wallet: {balance['balance_eth']:.4f} ETH)"
            else:
                result["valid"] = True  # Still valid, just empty wallet
                result["validation_summary"] = f"PASSED (empty wallet)"
        else:
            result["valid"] = True
            result["validation_summary"] = "PASSED (Etherscan unavailable)"
    else:
        result["valid"] = True
        result["validation_summary"] = "PASSED"

    return result


def validate_keys(keys: List[Dict]) -> List[Dict]:
    """Validate a batch of keys and return enriched results."""
    return [validate_key(k) for k in keys]