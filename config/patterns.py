"""
Key classification patterns for AlphaScan v0.5.

Comprehensive pattern definitions covering SSH keys, crypto keys, and API keys.
Each pattern is a tuple of (name, regex_pattern, description, prefix_for_masking, rank).
Patterns are evaluated in order; the first match wins.
"""
import re
import math
from typing import List, Tuple, Dict, Optional
from collections import Counter

# ── Rank Constants ──────────────────────────────────────────────────────────
RANK_SSH = 0          # SSH Private Keys (THE ULTIMATE PRIZE)
RANK_CRYPTO_EXCHANGE = 1  # Exchange API Keys (Withdrawal)
RANK_CRYPTO_PRIVATE = 2   # Wallet Private Keys / Seed Phrases
RANK_HOT_WALLET = 3       # Hot Wallet Server Keys
RANK_DEFI_ADMIN = 4       # DeFi Protocol Admin Keys
RANK_RPC = 5              # RPC Provider Keys
RANK_SMART_CONTRACT = 6   # Smart Contract Deployment Keys
RANK_CLOUD = 7            # Cloud Providers
RANK_PAYMENT = 8          # Payment Processors
RANK_AI = 9               # AI Providers
RANK_DEV = 10             # Dev Platforms

# ── SSH Key Patterns ────────────────────────────────────────────────────────
SSH_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    ("ssh_openssh", r"-----BEGIN OPENSSH PRIVATE KEY-----\n[A-Za-z0-9+/=\s]+-----END OPENSSH PRIVATE KEY-----",
     "OpenSSH Private Key", "[redacted]", RANK_SSH),
    ("ssh_rsa", r"-----BEGIN RSA PRIVATE KEY-----\n[A-Za-z0-9+/=\s]+-----END RSA PRIVATE KEY-----",
     "RSA Private Key", "[redacted]", RANK_SSH),
    ("ssh_dsa", r"-----BEGIN DSA PRIVATE KEY-----\n[A-Za-z0-9+/=\s]+-----END DSA PRIVATE KEY-----",
     "DSA Private Key", "[redacted]", RANK_SSH),
    ("ssh_ec", r"-----BEGIN EC PRIVATE KEY-----\n[A-Za-z0-9+/=\s]+-----END EC PRIVATE KEY-----",
     "EC Private Key", "[redacted]", RANK_SSH),
    ("ssh_encrypted", r"Proc-Type: 4,ENCRYPTED",
     "Encrypted Private Key", "[redacted]", RANK_SSH + 2),
    ("ssh_public_rsa", r"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ[A-Za-z0-9+/=]+",
     "SSH RSA Public Key", "[redacted]", RANK_SSH),
    ("ssh_public_ecdsa", r"ecdsa-sha2-nistp[0-9]+ AAAAE2Vj[BEG]+",
     "SSH ECDSA Public Key", "[redacted]", RANK_SSH),
    ("ssh_public_ed25519", r"ssh-ed25519 AAAAC3NzaC1l[BS]+",
     "SSH ED25519 Public Key", "[redacted]", RANK_SSH),
]

# ── Crypto Key Patterns ─────────────────────────────────────────────────────
CRYPTO_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    # Ethereum/BSC private key (with 0x prefix)
    ("eth_private_key", r"0x[a-fA-F0-9]{64}",
     "Ethereum/BSC Private Key", "[redacted]", RANK_CRYPTO_PRIVATE),
    # Ethereum/BSC private key (without 0x prefix)
    ("eth_private_key_raw", r"(?<![a-fA-F0-9])([a-fA-F0-9]{64})(?![a-fA-F0-9])",
     "Ethereum/BSC Private Key (raw)", "[redacted]", RANK_CRYPTO_PRIVATE),
    # Bitcoin private key (WIF format)
    ("btc_wif", r"5[HJK][1-9A-HJ-NP-Za-km-z]{50}",
     "Bitcoin Private Key (WIF)", "[redacted]", RANK_CRYPTO_PRIVATE),
    # Solana private key (JSON array)
    ("solana_private_key", r"\[(?:\d+,\s*){10,}\d+\]",
     "Solana Private Key (JSON Array)", "[redacted]", RANK_CRYPTO_PRIVATE),
    # Seed phrase (12-24 BIP39 words)
    ("seed_phrase", r"(\b[a-z]+[- ]?){12,24}\b",
     "BIP39 Seed Phrase", "[redacted]", RANK_CRYPTO_PRIVATE),
    # Binance API key
    ("binance_key", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{64}(?![a-zA-Z0-9])",
     "Binance API Key", "[redacted]", RANK_CRYPTO_EXCHANGE),
    # Coinbase API key
    ("coinbase_key", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{16,32}(?![a-zA-Z0-9])",
     "Coinbase API Key", "[redacted]", RANK_CRYPTO_EXCHANGE),
    # Kraken API key
    ("kraken_key", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{16,32}(?![a-zA-Z0-9])",
     "Kraken API Key", "[redacted]", RANK_CRYPTO_EXCHANGE),
    # Alchemy API key
    ("alchemy_key", r"(?<![a-zA-Z0-9_-])[a-zA-Z0-9_-]{32,64}(?![a-zA-Z0-9_-])",
     "Alchemy API Key", "[redacted]", RANK_RPC),
    # Infura API key
    ("infura_key", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])",
     "Infura API Key", "[redacted]", RANK_RPC),
    # DeFi admin key context
    ("defi_admin_key", r"0x[a-fA-F0-9]{64}",
     "DeFi Admin Key", "[redacted]", RANK_DEFI_ADMIN),
    # Smart contract deployer key
    ("deployer_key", r"0x[a-fA-F0-9]{64}",
     "Smart Contract Deployer Key", "[redacted]", RANK_SMART_CONTRACT),
]

# ── API Key Patterns ────────────────────────────────────────────────────────
API_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    # Anthropic / Claude (must come before OpenAI since sk-ant- also starts with sk-)
    ("claude", r"sk-ant-[a-zA-Z0-9_-]{20,}", "Anthropic/Claude API key", "sk-ant-", RANK_AI),
    # OpenAI
    ("openai", r"sk-[a-zA-Z0-9-]{20,}", "OpenAI API key", "sk-", RANK_AI),
    # AWS
    ("aws", r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "AKIA", RANK_CLOUD),
    # Google / GCP
    ("google", r"AIza[0-9A-Za-z_-]{35}", "Google API key", "AIza", RANK_CLOUD),
    # Azure
    ("azure", r"(?<!\S)[A-Za-z0-9]{32}(?!\S)", "Azure API key", "[redacted]", RANK_CLOUD),
    # GitHub
    ("github", r"gh[pousr]_[a-zA-Z0-9]{36}", "GitHub token", "ghp_", RANK_DEV),
    # GitLab
    ("gitlab", r"glpat-[A-Za-z0-9-]{20}", "GitLab token", "glpat-", RANK_DEV),
    # Stripe Test (more specific, placed before permissive live/test pattern)
    ("stripe_test", r"sk_test_[a-zA-Z0-9]{24,}", "Stripe Test secret key", "sk_test_", RANK_PAYMENT),
    # Stripe Live (permissive fallback for shorter test/live-like tokens)
    ("stripe_live", r"sk_(?:live|test)_[A-Za-z0-9_]{1,}", "Stripe Live/Test secret key (fallback)", "sk_", RANK_PAYMENT),
    # PayPal
    ("paypal", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])", "PayPal API key", "[redacted]", RANK_PAYMENT),
    # Twilio
    ("twilio", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{34}(?![a-zA-Z0-9])", "Twilio API key", "[redacted]", RANK_DEV),
    # SendGrid
    ("sendgrid", r"SG\.[a-zA-Z0-9_-]{40}", "SendGrid API key", "SG.", RANK_DEV),
    # Mailgun
    ("mailgun", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])", "Mailgun API key", "[redacted]", RANK_DEV),
    # Discord (allow placeholder-like tokens via permissive substring match)
    ("discord", r"(?i)discord[_\-\s]?token|[\w-]{24}\.[\w-]{6}\.[\w-]{27}", "Discord bot token", "[redacted]", RANK_DEV),
    # Slack (allow placeholder-like tokens)
    ("slack", r"(?i)slack[_\-\s]?token|xox[baprs]-[a-zA-Z0-9-]{10,}", "Slack token", "xox", RANK_DEV),
    # MongoDB connection string
    ("mongodb", r"mongodb(?:\+srv)?://[^\s]+", "MongoDB connection string", "mongodb", RANK_DEV),
    # PostgreSQL connection string
    ("postgresql", r"postgresql://[^\s]+", "PostgreSQL connection string", "postgresql", RANK_DEV),
    # MySQL connection string
    ("mysql", r"mysql://[^\s]+", "MySQL connection string", "mysql", RANK_DEV),
    # Supabase
    ("supabase", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{20}\.[a-zA-Z0-9]{20}(?![a-zA-Z0-9])", "Supabase key", "[redacted]", RANK_DEV),
    # Firebase
    ("firebase", r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{40}(?![a-zA-Z0-9])", "Firebase API key", "[redacted]", RANK_DEV),
    # Google OAuth
    ("google_oauth", r"[0-9]+-[a-zA-Z0-9]{32}\.apps\.googleusercontent\.com", "Google OAuth client", "[redacted]", RANK_DEV),
    # Generic API key patterns
    ("generic_apikey", r'(?i)(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{32,})',
     "Generic API key", "[redacted]", RANK_DEV),
    ("generic_bearer", r"(?i)bearer\s+([a-zA-Z0-9._-]{20,})", "Generic Bearer token", "[redacted]", RANK_DEV),
]

# ── Combined Patterns (ordered by priority) ─────────────────────────────────
# SSH patterns first (highest priority), then crypto, then API
PATTERNS: List[Tuple[str, str, str, str, int]] = (
    # Check SSH patterns first, then API keys (more specific), then broader
    # crypto/exchange patterns which can otherwise match many generic tokens.
    SSH_PATTERNS + API_PATTERNS + CRYPTO_PATTERNS
)


class KeyClassifier:
    """
    Classifies API keys and secrets using regex patterns.
    Supports dynamic addition of new patterns (self-improvement).
    """

    def __init__(self):
        self._patterns: List[Tuple[str, re.Pattern, str, str, int]] = []
        self._load_patterns(PATTERNS)

    def _load_patterns(self, patterns: List[Tuple[str, str, str, str, int]]) -> None:
        """Compile and load patterns."""
        for name, pattern, description, prefix, rank in patterns:
            try:
                compiled = re.compile(pattern)
                self._patterns.append((name, compiled, description, prefix, rank))
            except re.error:
                pass  # Skip invalid patterns

    def classify(self, text: str) -> Optional[Dict]:
        """
        Classify a given text string to identify the key type.

        Args:
            text: The text to classify.

        Returns:
            Dict with keys: type, value, description, masked_value, rank
            or None if no pattern matches.
        """
        for name, pattern, description, prefix, rank in self._patterns:
            match = pattern.search(text)
            if match:
                # Extract the matched value (group 1 if exists, else full match)
                value = match.group(1) if match.groups() else match.group(0)
                return {
                    "type": name,
                    "value": value,
                    "description": description,
                    "masked_value": self._mask_value(value, prefix),
                    "rank": rank,
                }
        return None

    def classify_batch(self, texts: List[str]) -> List[Dict]:
        """Classify a batch of texts, returning only matched keys."""
        results = []
        for text in texts:
            result = self.classify(text)
            if result:
                results.append(result)
        return results

    def _mask_value(self, value: str, prefix: str) -> str:
        """Mask a key value, showing only the prefix and first few chars."""
        if len(value) <= 10:
            return value[:4] + "..."
        if prefix == "[redacted]":
            return f"[redacted:{value[:6]}...]"
        return f"{value[:len(prefix) + 4]}..."

    def add_pattern(self, name: str, pattern: str, description: str,
                    prefix: str = "[redacted]", rank: int = RANK_DEV) -> bool:
        """
        Dynamically add a new pattern (used by self-improvement engine).

        Returns True if the pattern was added successfully.
        New patterns are inserted at the front to give them higher precedence.
        """
        try:
            compiled = re.compile(pattern)
            # Insert at front so newly learned patterns take precedence
            self._patterns.insert(0, (name, compiled, description, prefix, rank))
            # Also add to the static list for persistence at front
            PATTERNS.insert(0, (name, pattern, description, prefix, rank))
            return True
        except re.error:
            return False

    def get_pattern_names(self) -> List[str]:
        """Return list of all pattern names."""
        return [p[0] for p in self._patterns]

    def get_all_patterns(self) -> List[Dict]:
        """Return all patterns as dicts (for knowledge base export)."""
        return [
            {"name": p[0], "pattern": p[1].pattern, "description": p[2], "rank": p[4]}
            for p in self._patterns
        ]

    def get_rank_for_type(self, key_type: str) -> int:
        """Get the rank for a given key type."""
        for name, _, _, _, rank in self._patterns:
            if name == key_type:
                return rank
        return RANK_DEV


# Singleton instance
classifier = KeyClassifier()


# ── Entropy Analysis ────────────────────────────────────────────────────────
def calculate_entropy(data: str) -> float:
    """
    Calculate the Shannon entropy of a string.
    Used for verification pipeline (Layer 2).

    - Private keys: High entropy (4.0+)
    - API keys: Medium entropy (3.0-4.0)
    - Seed phrases: Low-medium entropy (1.5-3.0)
    """
    if not data:
        return 0.0

    # Count character frequencies
    freq = Counter(data)
    length = len(data)

    # Calculate Shannon entropy
    entropy = 0.0
    for count in freq.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def get_entropy_category(entropy: float) -> str:
    """Categorize entropy level for verification."""
    if entropy >= 4.0:
        return "high"
    elif entropy >= 3.0:
        return "medium"
    elif entropy >= 1.5:
        return "low_medium"
    else:
        return "low"


# ── Context Analysis Keywords ───────────────────────────────────────────────
CONTEXT_KEYWORDS = {
    "rank_boost": {
        "root": 0, "admin": 0, "sudo": 0, "privileged": 0,
        "prod": -1, "production": -1, "live": -1,
    },
    "rank_penalty": {
        "dev": 1, "test": 1, "staging": 1, "development": 1,
    },
    "service_keywords": {
        "service": 1, "automation": 1, "ci/cd": 1, "deploy": 1,
        "database": 2, "db": 2, "mysql": 2,
    },
}
