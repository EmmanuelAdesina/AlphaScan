"""
AlphaScan Key Validator.
Operates on Finding objects. Enriches Findings with validation results.
"""
import logging
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ETHERSCAN_API_KEY
from models import Finding

logger = logging.getLogger(__name__)

# Minimum length requirements per key type
MIN_LENGTHS = {
    "ssh_rsa": 100,
    "ssh_openssh": 100,
    "ssh_ec": 100,
    "ssh_dsa": 100,
    "ssh_pkcs8": 100,
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
    """Validate key format based on type. Returns (is_valid, reason)."""
    key_type = key.get("type", "")
    value = key.get("value", "")
    if not value:
        return False, "empty value"
    min_len = MIN_LENGTHS.get(key_type, 10)
    if len(value) < min_len:
        return False, f"too short ({len(value)} < {min_len})"
    prefix = PREFIXES.get(key_type)
    if prefix:
        if isinstance(prefix, tuple):
            if not value.startswith(prefix):
                return False, f"prefix mismatch (expected one of {prefix})"
        else:
            if not value.startswith(prefix):
                return False, f"prefix mismatch (expected '{prefix}')"
    if key_type.startswith("ssh_"):
        if not value.startswith("-----BEGIN"):
            return False, "missing BEGIN marker"
        if not value.strip().endswith("-----"):
            return False, "missing END marker"
    if key_type == "eth_private_key":
        hex_part = value[2:] if value.startswith("0x") else value
        if len(hex_part) != 64:
            return False, f"wrong length ({len(hex_part)} != 64)"
        if not re.match(r'^[a-fA-F0-9]{64}$', hex_part):
            return False, "invalid hex characters"
    return True, "format OK"


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
    """Check if key has sufficient entropy."""
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
    is_suspicious = entropy < 1.5
    return is_suspicious, entropy, category


def derive_address_from_private_key(private_key_hex: str) -> Optional[str]:
    """Derive Ethereum address from a private key hex string."""
    try:
        from eth_account import Account
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
    """Check wallet balance via Etherscan API."""
    if not ETHERSCAN_API_KEY:
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
        resp = __import__('requests').get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != "1":
            return None
        balance_wei = int(data.get("result", "0"))
        balance_eth = balance_wei / 1e18
        return {"address": address, "balance_wei": balance_wei, "balance_eth": balance_eth, "has_funds": balance_eth > 0}
    except Exception:
        return None


def check_crypto_balance(key: Dict) -> Optional[Dict]:
    """Check if a crypto private key has a non-zero wallet balance."""
    key_type = key.get("type", "")
    value = key.get("value", "")
    if key_type not in ("eth_private_key",):
        return None
    address = derive_address_from_private_key(value)
    if not address:
        return None
    return check_etherscan_balance(address)


def validate_key(key: Dict) -> Dict:
    """Run all validation layers on a single key."""
    result = dict(key)
    format_ok, format_reason = check_format(key)
    result["format_valid"] = format_ok
    result["format_reason"] = format_reason
    if not format_ok:
        result["valid"] = False
        result["validation_summary"] = f"FAILED format: {format_reason}"
        return result
    entropy_suspicious, entropy_val, entropy_cat = check_entropy(key)
    result["entropy"] = round(entropy_val, 2)
    result["entropy_category"] = entropy_cat
    result["entropy_suspicious"] = entropy_suspicious
    result["entropy_valid"] = not entropy_suspicious
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
                result["valid"] = True
                result["validation_summary"] = "PASSED (empty wallet)"
        else:
            result["valid"] = True
            result["validation_summary"] = "PASSED (Etherscan unavailable)"
    else:
        result["valid"] = True
        result["validation_summary"] = "PASSED"
    return result


def validate_finding(finding: Finding) -> Finding:
    """Validate all extracted secrets in a Finding."""
    if not finding.extracted_secrets:
        finding.validation_results = []
        return finding
    validated = [validate_key(k) for k in finding.extracted_secrets]
    finding.validation_results = validated
    return finding


def validate_findings(findings: List[Finding]) -> List[Finding]:
    """Validate a batch of Findings and return enriched results."""
    return [validate_finding(f) for f in findings]


def get_metrics(findings: List[Finding]) -> Dict[str, Any]:
    """Compute scan metrics from validated findings."""
    total_secrets = 0
    valid = 0
    invalid = 0
    for f in findings:
        for vr in f.validation_results:
            total_secrets += 1
            if vr.get("valid"):
                valid += 1
            else:
                invalid += 1
    return {
        "total_findings": len(findings),
        "total_secrets_extracted": total_secrets,
        "validation_results": {"valid": valid, "invalid": invalid, "skipped": 0},
    }