"""
SSH Private Key Intelligence for AlphaScan v0.5.

Detects, analyzes, and verifies SSH private keys without using them.
Passive detection only - NEVER attempts to use the key.
"""
import re
import base64
import hashlib
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# SSH key header patterns
# Character class includes base64 chars, whitespace, and PEM header chars (:, ,, -)
SSH_KEY_PATTERNS = {
    "openssh": r"-----BEGIN OPENSSH PRIVATE KEY-----\n([\s\S]+?)-----END OPENSSH PRIVATE KEY-----",
    "rsa": r"-----BEGIN RSA PRIVATE KEY-----\n([\s\S]+?)-----END RSA PRIVATE KEY-----",
    "dsa": r"-----BEGIN DSA PRIVATE KEY-----\n([\s\S]+?)-----END DSA PRIVATE KEY-----",
    "ec": r"-----BEGIN EC PRIVATE KEY-----\n([\s\S]+?)-----END EC PRIVATE KEY-----",
}

# Public key patterns
SSH_PUBLIC_PATTERNS = {
    "rsa_pub": r"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ([A-Za-z0-9+/=]+)",
    "ecdsa_pub": r"ecdsa-sha2-nistp[0-9]+ AAAAE2Vj([A-Za-z0-9+/=]+)",
    "ed25519_pub": r"ssh-ed25519 AAAAC3NzaC1l([A-Za-z0-9+/=]+)",
}

# Encrypted key indicator
ENCRYPTED_PATTERN = r"Proc-Type: 4,ENCRYPTED"

# Context keywords for permission analysis
PERMISSION_KEYWORDS = {
    "root": "ROOT ACCESS",
    "admin": "ADMIN ACCESS",
    "sudo": "SUDO ACCESS",
    "service": "SERVICE ACCOUNT",
    "automation": "AUTOMATION ACCOUNT",
    "ci/cd": "CI/CD ACCOUNT",
    "deploy": "DEPLOY ACCOUNT",
    "database": "DATABASE ACCOUNT",
    "db": "DATABASE ACCOUNT",
}


class SSHIntelligence:
    """
    Detects and analyzes SSH private keys from text data.
    All operations are passive - keys are never used, only analyzed.
    """

    def __init__(self):
        self._compiled_private = {
            name: re.compile(pattern) for name, pattern in SSH_KEY_PATTERNS.items()
        }
        self._compiled_public = {
            name: re.compile(pattern) for name, pattern in SSH_PUBLIC_PATTERNS.items()
        }
        self._encrypted_re = re.compile(ENCRYPTED_PATTERN)

    def detect(self, text: str) -> List[Dict]:
        """
        Detect SSH keys in text.

        Args:
            text: Text to scan for SSH keys.

        Returns:
            List of detected SSH key dicts with analysis.
        """
        results = []

        # Check for private keys
        for key_type, pattern in self._compiled_private.items():
            for match in pattern.finditer(text):
                key_data = match.group(0)
                key_body = match.group(1) if match.groups() else ""

                analysis = self._analyze_private_key(key_type, key_data, key_body, text)
                results.append(analysis)

        # Check for public keys
        for key_type, pattern in self._compiled_public.items():
            for match in pattern.finditer(text):
                key_data = match.group(0)
                analysis = self._analyze_public_key(key_type, key_data, text)
                results.append(analysis)

        # Check for encrypted key indicator
        if self._encrypted_re.search(text):
            # Mark any detected keys as encrypted
            for result in results:
                result["encrypted"] = True

        return results

    def _analyze_private_key(self, key_type: str, key_data: str,
                             key_body: str, context: str) -> Dict:
        """Analyze a detected SSH private key."""
        # Validate PEM format
        is_valid_pem = self._validate_pem(key_data)

        # Generate fingerprint
        fingerprint = self._generate_fingerprint(key_data)

        # Detect encryption
        encrypted = bool(self._encrypted_re.search(context))

        # Determine key size
        key_size = self._estimate_key_size(key_type, key_body)

        # Analyze context for permissions
        permissions = self._analyze_context(context)

        # Determine format
        format_name = self._get_format_name(key_type)

        return {
            "type": f"ssh_{key_type}",
            "key_format": format_name,
            "value": key_data,
            "fingerprint": fingerprint,
            "encrypted": encrypted,
            "key_size": key_size,
            "valid_pem": is_valid_pem,
            "permissions": permissions,
            "context": context[:200] if context else "",
            "detected_at": datetime.utcnow().isoformat(),
            "description": f"{format_name} ({'Encrypted' if encrypted else 'Unencrypted'})",
        }

    def _analyze_public_key(self, key_type: str, key_data: str,
                            context: str) -> Dict:
        """Analyze a detected SSH public key."""
        return {
            "type": f"ssh_{key_type}",
            "key_format": "SSH Public Key",
            "value": key_data,
            "fingerprint": self._generate_fingerprint(key_data),
            "encrypted": False,
            "key_size": self._estimate_key_size(key_type, key_data),
            "valid_pem": True,
            "permissions": self._analyze_context(context),
            "context": context[:200] if context else "",
            "detected_at": datetime.utcnow().isoformat(),
            "description": "SSH Public Key (correlation with private key)",
        }

    def _validate_pem(self, key_data: str) -> bool:
        """Validate PEM format and base64 encoding."""
        try:
            # Extract base64 content between headers
            lines = key_data.strip().split("\n")
            if len(lines) < 2:
                return False

            # Check for proper BEGIN/END markers
            if "BEGIN" not in lines[0] or "END" not in lines[-1]:
                return False

            # Extract and validate base64 content (skip header lines like Proc-Type)
            b64_lines = []
            for line in lines[1:-1]:
                # Skip non-base64 header lines
                if line.startswith("Proc-Type") or line.startswith("DEK-Info"):
                    continue
                b64_lines.append(line)

            b64_content = "\n".join(b64_lines)
            if b64_content.strip():
                base64.b64decode(b64_content, validate=True)
            return True
        except Exception:
            return False

    def _generate_fingerprint(self, key_data: str) -> str:
        """
        Generate MD5 fingerprint of the key.
        Format: MD5:12:34:56:78:90:ab:cd:ef:12:34:56:78:90:ab:cd:ef
        """
        try:
            # Use the raw key data for fingerprinting
            key_bytes = key_data.encode("utf-8")
            md5_hash = hashlib.md5(key_bytes).hexdigest()

            # Format as colon-separated pairs
            formatted = ":".join(
                md5_hash[i:i+2] for i in range(0, len(md5_hash), 2)
            )
            return f"MD5:{formatted}"
        except Exception:
            return "MD5:00:00:00:00:00:00:00:00:00:00:00:00"

    def _estimate_key_size(self, key_type: str, key_body: str) -> int:
        """Estimate the key size in bits."""
        try:
            # Decode base64 and estimate size
            b64_content = key_body.replace("\n", "").strip()
            decoded = base64.b64decode(b64_content)
            byte_length = len(decoded)

            if key_type == "openssh":
                return byte_length * 8
            elif key_type == "rsa":
                return byte_length * 8
            elif key_type == "ec":
                return 256
            elif key_type == "dsa":
                return 1024
            else:
                return byte_length * 8
        except Exception:
            return 0

    def _analyze_context(self, context: str) -> str:
        """Analyze context text for permission level keywords."""
        context_lower = context.lower() if context else ""

        for keyword, permission in PERMISSION_KEYWORDS.items():
            if keyword in context_lower:
                return permission

        return "UNKNOWN"

    def _get_format_name(self, key_type: str) -> str:
        """Get human-readable format name."""
        names = {
            "openssh": "OpenSSH Private Key",
            "rsa": "RSA Private Key",
            "dsa": "DSA Private Key",
            "ec": "EC Private Key",
        }
        return names.get(key_type, "Unknown Format")

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify an SSH key entry (passive verification only).

        Args:
            key_data: Dict with SSH key information.

        Returns:
            Dict with verification results.
        """
        value = key_data.get("value", "")

        return {
            "verified": True,
            "method": "format_validation",
            "checks": {
                "pem_format": self._validate_pem(value),
                "fingerprint": self._generate_fingerprint(value),
                "encrypted": key_data.get("encrypted", False),
                "key_size": key_data.get("key_size", 0),
            },
            "risk_level": "critical" if not key_data.get("encrypted", False) else "high",
            "note": "Passive verification only - key was not used",
        }
