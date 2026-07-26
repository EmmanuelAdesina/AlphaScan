"""
AlphaScan Secret Families.

Never classify everything as "api_key". Each secret family provides
specific provider-aware classification with distinct regex patterns,
known prefixes, entropy expectations, and context clues.

A secret family is a broad grouping (e.g. "github_pat") while
secret_type is the specific variant (e.g. "GitHub Fine-Grained PAT").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Tuple


@dataclass
class SecretFamilyDefinition:
    """Complete definition of a secret family.

    Includes detection patterns, known prefixes, expected entropy,
    context clues, and provider mapping.
    """
    family: str                           # e.g. "github_pat"
    display_type: str                     # e.g. "GitHub Fine-Grained PAT"
    provider: str                         # e.g. "github"
    patterns: List[Pattern] = field(default_factory=list)
    prefixes: List[str] = field(default_factory=list)
    min_length: int = 20
    expected_entropy_range: Tuple[float, float] = (3.0, 6.0)
    context_keywords: List[str] = field(default_factory=list)
    filename_patterns: List[Pattern] = field(default_factory=list)
    variable_patterns: List[Pattern] = field(default_factory=list)
    json_key_patterns: List[Pattern] = field(default_factory=list)
    description: str = ""
    risk_level: str = "medium"            # critical, high, medium, low
    supports_provider_verification: bool = False
    verification_endpoint: Optional[str] = None


# ── Family Definitions ─────────────────────────────────────────────

FAMILIES: Dict[str, SecretFamilyDefinition] = {}

def _register(defn: SecretFamilyDefinition) -> None:
    FAMILIES[defn.family] = defn


# ── GitHub ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="github_classic_pat",
    display_type="GitHub Classic PAT",
    provider="github",
    patterns=[re.compile(r"ghp_[a-zA-Z0-9]{36}")],
    prefixes=["ghp_"],
    min_length=40,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["github", "git", "token", "pat", "personal access"],
    filename_patterns=[re.compile(r"\.env", re.I), re.compile(r"config", re.I)],
    variable_patterns=[re.compile(r"GITHUB_TOKEN", re.I), re.compile(r"GITHUB_PAT", re.I)],
    json_key_patterns=[re.compile(r"github_token", re.I), re.compile(r"github_pat", re.I)],
    description="GitHub Personal Access Token (classic). Grants repository access.",
    risk_level="high",
    supports_provider_verification=True,
    verification_endpoint="https://api.github.com/user",
))

_register(SecretFamilyDefinition(
    family="github_fine_grained_pat",
    display_type="GitHub Fine-Grained PAT",
    provider="github",
    patterns=[re.compile(r"github_pat_[a-zA-Z0-9_]{82}")],
    prefixes=["github_pat_"],
    min_length=90,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["github", "fine", "granular", "pat"],
    variable_patterns=[re.compile(r"GITHUB_FINE_GRAINED", re.I)],
    json_key_patterns=[re.compile(r"github_pat", re.I)],
    description="GitHub Fine-Grained Personal Access Token. Scoped repository access.",
    risk_level="high",
    supports_provider_verification=True,
    verification_endpoint="https://api.github.com/user",
))

_register(SecretFamilyDefinition(
    family="github_oauth_token",
    display_type="GitHub OAuth Token",
    provider="github",
    patterns=[re.compile(r"gho_[a-zA-Z0-9]{36}")],
    prefixes=["gho_"],
    min_length=40,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["github", "oauth"],
    description="GitHub OAuth Access Token.",
    risk_level="high",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="github_app_token",
    display_type="GitHub App Token",
    provider="github",
    patterns=[re.compile(r"ghs_[a-zA-Z0-9]{36}")],
    prefixes=["ghs_"],
    min_length=40,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["github", "app", "installation"],
    description="GitHub App Installation Token.",
    risk_level="high",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="github_refresh_token",
    display_type="GitHub Refresh Token",
    provider="github",
    patterns=[re.compile(r"ghr_[a-zA-Z0-9]{36}")],
    prefixes=["ghr_"],
    min_length=40,
    context_keywords=["github", "refresh"],
    description="GitHub Refresh Token.",
    risk_level="medium",
    supports_provider_verification=True,
))

# ── AWS ──────────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="aws_access_key",
    display_type="AWS Access Key",
    provider="aws",
    patterns=[re.compile(r"AKIA[0-9A-Z]{16}")],
    prefixes=["AKIA"],
    min_length=20,
    expected_entropy_range=(3.5, 5.0),
    context_keywords=["aws", "amazon", "access", "key", "iam"],
    filename_patterns=[re.compile(r"\.env", re.I), re.compile(r"aws.*config", re.I)],
    variable_patterns=[re.compile(r"AWS_ACCESS_KEY_ID", re.I), re.compile(r"AWS_KEY", re.I)],
    json_key_patterns=[re.compile(r"aws_access_key", re.I)],
    description="AWS IAM Access Key ID. Identifies an IAM user.",
    risk_level="critical",
    supports_provider_verification=True,
    verification_endpoint="https://sts.amazonaws.com/",
))

_register(SecretFamilyDefinition(
    family="aws_secret_access_key",
    display_type="AWS Secret Access Key",
    provider="aws",
    patterns=[re.compile(r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})")],
    min_length=40,
    expected_entropy_range=(4.5, 6.0),
    context_keywords=["aws", "secret", "access"],
    variable_patterns=[re.compile(r"AWS_SECRET_ACCESS_KEY", re.I)],
    json_key_patterns=[re.compile(r"aws_secret_access_key", re.I)],
    description="AWS Secret Access Key. Used with Access Key ID for authentication.",
    risk_level="critical",
    supports_provider_verification=True,
))

# ── GitLab ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="gitlab_pat",
    display_type="GitLab PAT",
    provider="gitlab",
    patterns=[re.compile(r"glpat-[A-Za-z0-9\-]{20}")],
    prefixes=["glpat-"],
    min_length=26,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["gitlab", "token", "pat"],
    variable_patterns=[re.compile(r"GITLAB_TOKEN", re.I)],
    description="GitLab Personal Access Token.",
    risk_level="high",
    supports_provider_verification=True,
    verification_endpoint="https://gitlab.com/api/v4/user",
))

# ── Anthropic (registered before OpenAI — "sk-ant-" is more specific than "sk-") ────

_register(SecretFamilyDefinition(
    family="anthropic_api",
    display_type="Anthropic API Key",
    provider="anthropic",
    patterns=[re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}")],
    prefixes=["sk-ant-"],
    min_length=27,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["anthropic", "claude", "ai"],
    variable_patterns=[re.compile(r"ANTHROPIC_API_KEY", re.I)],
    json_key_patterns=[re.compile(r"anthropic_api_key", re.I)],
    description="Anthropic API Key. Grants access to Claude models.",
    risk_level="medium",
    supports_provider_verification=True,
    verification_endpoint="https://api.anthropic.com/v1/models",
))

# ── OpenAI ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="openai_api",
    display_type="OpenAI API Key",
    provider="openai",
    patterns=[re.compile(r"sk-[a-zA-Z0-9\-]{20,}")],
    prefixes=["sk-"],
    min_length=24,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["openai", "gpt", "chatgpt", "ai", "dalle", "api"],
    filename_patterns=[re.compile(r"\.env", re.I)],
    variable_patterns=[re.compile(r"OPENAI_API_KEY", re.I), re.compile(r"OPENAI_KEY", re.I)],
    json_key_patterns=[re.compile(r"openai_api_key", re.I)],
    description="OpenAI API Key. Grants access to GPT, DALL-E, and other models.",
    risk_level="medium",
    supports_provider_verification=True,
    verification_endpoint="https://api.openai.com/v1/models",
))

# ── Mistral ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="mistral_api",
    display_type="Mistral API Key",
    provider="mistral",
    patterns=[re.compile(r"(?i)mistral[_\-]?api[_\-]?key[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9]{20,})")],
    min_length=20,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["mistral", "ai", "mistralai"],
    variable_patterns=[re.compile(r"MISTRAL_API_KEY", re.I)],
    description="Mistral AI API Key.",
    risk_level="medium",
    supports_provider_verification=True,
))

# ── Google AI ────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="google_ai_api",
    display_type="Google AI API Key",
    provider="google",
    patterns=[re.compile(r"AIza[0-9A-Za-z_\-]{35}")],
    prefixes=["AIza"],
    min_length=39,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["google", "ai", "gemini", "bard", "cloud", "firebase"],
    variable_patterns=[re.compile(r"GOOGLE_API_KEY", re.I), re.compile(r"GOOGLE_AI_KEY", re.I)],
    description="Google AI / Cloud API Key.",
    risk_level="high",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="google_service_account",
    display_type="Google Service Account JSON",
    provider="google",
    patterns=[re.compile(r"\"type\":\s*\"service_account\"")],
    context_keywords=["google", "service_account", "gcloud", "project_id"],
    description="Google Cloud Service Account credentials JSON.",
    risk_level="critical",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="firebase_config",
    display_type="Firebase Configuration",
    provider="google",
    patterns=[re.compile(r"\"apiKey\":\s*\"AIza")],
    context_keywords=["firebase", "apiKey", "projectId", "appId"],
    description="Firebase web/app configuration containing API key.",
    risk_level="medium",
))

# ── Stripe ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="stripe_secret_key",
    display_type="Stripe Secret Key",
    provider="stripe",
    patterns=[re.compile(r"sk_live_[a-zA-Z0-9]{24,}")],
    prefixes=["sk_live_"],
    min_length=32,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["stripe", "payment", "live", "secret"],
    variable_patterns=[re.compile(r"STRIPE_SECRET_KEY", re.I), re.compile(r"STRIPE_API_KEY", re.I)],
    description="Stripe Secret Key (live mode). Full payment access.",
    risk_level="critical",
    supports_provider_verification=True,
    verification_endpoint="https://api.stripe.com/v1/balance",
))

_register(SecretFamilyDefinition(
    family="stripe_publishable_key",
    display_type="Stripe Publishable Key",
    provider="stripe",
    patterns=[re.compile(r"pk_live_[a-zA-Z0-9]{24,}")],
    prefixes=["pk_live_"],
    min_length=32,
    context_keywords=["stripe", "publishable", "public"],
    variable_patterns=[re.compile(r"STRIPE_PUBLIC_KEY", re.I)],
    description="Stripe Publishable Key (live mode). Limited scope, public-safe.",
    risk_level="low",
    supports_provider_verification=True,
))

# ── Coinbase ─────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="coinbase_api_key",
    display_type="Coinbase API Key",
    provider="coinbase",
    patterns=[re.compile(r"(?i)coinbase[_\-]?api[_\-]?key[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9]{20,})")],
    context_keywords=["coinbase", "crypto", "exchange"],
    variable_patterns=[re.compile(r"COINBASE_API_KEY", re.I)],
    description="Coinbase API Key.",
    risk_level="high",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="coinbase_secret",
    display_type="Coinbase Secret",
    provider="coinbase",
    patterns=[re.compile(r"(?i)coinbase[_\-]?secret[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9+/]{20,})")],
    context_keywords=["coinbase", "secret"],
    variable_patterns=[re.compile(r"COINBASE_SECRET", re.I)],
    description="Coinbase API Secret for request signing.",
    risk_level="critical",
))

# ── Discord ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="discord_bot_token",
    display_type="Discord Bot Token",
    provider="discord",
    patterns=[re.compile(r"[MN][a-zA-Z0-9\-]{23,}\.[a-zA-Z0-9\-]{6}\.[a-zA-Z0-9\-]{27}")],
    min_length=60,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["discord", "bot", "token"],
    variable_patterns=[re.compile(r"DISCORD_TOKEN", re.I), re.compile(r"DISCORD_BOT_TOKEN", re.I)],
    description="Discord Bot Token. Grants full bot access.",
    risk_level="high",
    supports_provider_verification=True,
))

# ── Slack ────────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="slack_bot_token",
    display_type="Slack Bot Token",
    provider="slack",
    patterns=[re.compile(r"xoxb-[a-zA-Z0-9\-]{10,}")],
    prefixes=["xoxb-"],
    min_length=34,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["slack", "bot", "token", "workspace"],
    variable_patterns=[re.compile(r"SLACK_BOT_TOKEN", re.I), re.compile(r"SLACK_TOKEN", re.I)],
    description="Slack Bot Token.",
    risk_level="high",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="slack_webhook",
    display_type="Slack Webhook",
    provider="slack",
    patterns=[re.compile(r"https://hooks\.slack\.com/services/T[a-zA-Z0-9]{8,}/B[a-zA-Z0-9]{8,}/[a-zA-Z0-9]{24,}")],
    context_keywords=["slack", "webhook", "hooks"],
    description="Slack Incoming Webhook URL.",
    risk_level="medium",
    supports_provider_verification=True,
))

# ── Twilio ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="twilio_sid",
    display_type="Twilio SID",
    provider="twilio",
    patterns=[re.compile(r"AC[a-zA-Z0-9]{32}")],
    prefixes=["AC"],
    min_length=34,
    context_keywords=["twilio", "sid", "account"],
    variable_patterns=[re.compile(r"TWILIO_ACCOUNT_SID", re.I)],
    description="Twilio Account SID.",
    risk_level="medium",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="twilio_auth_token",
    display_type="Twilio Auth Token",
    provider="twilio",
    patterns=[re.compile(r"(?i)twilio[_\-]?auth[_\-]?token[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9]{32})")],
    min_length=32,
    context_keywords=["twilio", "auth", "token"],
    variable_patterns=[re.compile(r"TWILIO_AUTH_TOKEN", re.I)],
    description="Twilio Auth Token.",
    risk_level="high",
    supports_provider_verification=True,
))

# ── SendGrid ─────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="sendgrid_api",
    display_type="SendGrid API Key",
    provider="sendgrid",
    patterns=[re.compile(r"SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}")],
    prefixes=["SG."],
    min_length=69,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["sendgrid", "mail", "email", "smtp"],
    variable_patterns=[re.compile(r"SENDGRID_API_KEY", re.I)],
    description="SendGrid API Key. Grants email sending access.",
    risk_level="high",
    supports_provider_verification=True,
))

# ── Mailgun ──────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="mailgun_api",
    display_type="Mailgun API Key",
    provider="mailgun",
    patterns=[re.compile(r"key-[a-zA-Z0-9]{32}")],
    prefixes=["key-"],
    min_length=36,
    context_keywords=["mailgun", "mail", "email"],
    variable_patterns=[re.compile(r"MAILGUN_API_KEY", re.I)],
    description="Mailgun API Key.",
    risk_level="medium",
))

# ── Cloudflare ───────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="cloudflare_api_token",
    display_type="Cloudflare API Token",
    provider="cloudflare",
    patterns=[re.compile(r"(?i)cloudflare[_\-]?api[_\-]?token[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_]{20,})")],
    context_keywords=["cloudflare", "cf", "dns", "cdn"],
    variable_patterns=[re.compile(r"CLOUDFLARE_API_TOKEN", re.I)],
    description="Cloudflare API Token.",
    risk_level="high",
    supports_provider_verification=True,
))

# ── Azure ────────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="azure_storage_key",
    display_type="Azure Storage Key",
    provider="azure",
    patterns=[re.compile(r"(?i)azure[_\-]?storage[_\-]?key[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9+/=]{40,})")],
    context_keywords=["azure", "storage", "blob", "account"],
    variable_patterns=[re.compile(r"AZURE_STORAGE_KEY", re.I)],
    description="Azure Storage Account Key.",
    risk_level="high",
))

# ── Database URIs ───────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="mongodb_uri",
    display_type="MongoDB URI",
    provider="mongodb",
    patterns=[re.compile(r"mongodb(?:\+srv)?://[^\s\"']+")],
    prefixes=["mongodb://", "mongodb+srv://"],
    context_keywords=["mongodb", "mongo", "db", "database"],
    variable_patterns=[re.compile(r"MONGO_URI", re.I), re.compile(r"MONGODB_URI", re.I)],
    description="MongoDB connection URI containing credentials.",
    risk_level="high",
))

_register(SecretFamilyDefinition(
    family="redis_uri",
    display_type="Redis URI",
    provider="redis",
    patterns=[re.compile(r"redis://[^\s\"']+")],
    prefixes=["redis://"],
    context_keywords=["redis", "cache"],
    variable_patterns=[re.compile(r"REDIS_URI", re.I)],
    description="Redis connection URI.",
    risk_level="medium",
))

_register(SecretFamilyDefinition(
    family="postgresql_uri",
    display_type="PostgreSQL URI",
    provider="postgresql",
    patterns=[re.compile(r"postgresql://[^\s\"']+")],
    prefixes=["postgresql://"],
    context_keywords=["postgres", "postgresql", "db", "database", "psql"],
    variable_patterns=[re.compile(r"DATABASE_URL", re.I), re.compile(r"POSTGRES_URI", re.I)],
    description="PostgreSQL connection URI containing credentials.",
    risk_level="high",
))

_register(SecretFamilyDefinition(
    family="mysql_uri",
    display_type="MySQL URI",
    provider="mysql",
    patterns=[re.compile(r"mysql://[^\s\"']+")],
    prefixes=["mysql://"],
    context_keywords=["mysql", "db", "database"],
    variable_patterns=[re.compile(r"MYSQL_URI", re.I)],
    description="MySQL connection URI containing credentials.",
    risk_level="high",
))

# ── Private Keys ────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="rsa_private_key",
    display_type="RSA Private Key",
    provider="ssh",
    patterns=[re.compile(r"-----BEGIN RSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END RSA PRIVATE KEY-----")],
    context_keywords=["rsa", "private", "key", "ssh"],
    description="RSA Private Key. Used for SSH, TLS, signing.",
    risk_level="critical",
))

_register(SecretFamilyDefinition(
    family="ssh_private_key",
    display_type="SSH Private Key",
    provider="ssh",
    patterns=[re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END OPENSSH PRIVATE KEY-----")],
    context_keywords=["ssh", "openssh", "private"],
    description="OpenSSH Private Key.",
    risk_level="critical",
))

_register(SecretFamilyDefinition(
    family="dsa_private_key",
    display_type="DSA Private Key",
    provider="ssh",
    patterns=[re.compile(r"-----BEGIN DSA PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END DSA PRIVATE KEY-----")],
    context_keywords=["dsa", "private", "ssh"],
    description="DSA Private Key.",
    risk_level="critical",
))

_register(SecretFamilyDefinition(
    family="ec_private_key",
    display_type="EC Private Key",
    provider="ssh",
    patterns=[re.compile(r"-----BEGIN EC PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END EC PRIVATE KEY-----")],
    context_keywords=["ec", "elliptic", "private"],
    description="Elliptic Curve Private Key.",
    risk_level="critical",
))

_register(SecretFamilyDefinition(
    family="generic_private_key",
    display_type="Generic Private Key (PKCS#8)",
    provider="ssh",
    patterns=[re.compile(r"-----BEGIN PRIVATE KEY-----[A-Za-z0-9+/=\s]+-----END PRIVATE KEY-----")],
    description="Generic PKCS#8 Private Key.",
    risk_level="critical",
))

_register(SecretFamilyDefinition(
    family="pgp_private_key",
    display_type="PGP Private Key",
    provider="pgp",
    patterns=[re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----")],
    context_keywords=["pgp", "gpg", "private", "encrypt"],
    description="PGP Private Key Block.",
    risk_level="critical",
))

# ── JWT ──────────────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="jwt",
    display_type="JWT",
    provider="jwt",
    patterns=[re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}")],
    prefixes=["eyJ"],
    min_length=30,
    expected_entropy_range=(3.5, 6.0),
    context_keywords=["jwt", "token", "json", "web", "signature"],
    description="JSON Web Token. May contain claims and secrets.",
    risk_level="medium",
))

# ── Crypto Keys ──────────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="ethereum_private_key",
    display_type="Ethereum Private Key",
    provider="ethereum",
    patterns=[re.compile(r"0x[a-fA-F0-9]{64}")],
    prefixes=["0x"],
    min_length=66,
    expected_entropy_range=(3.8, 4.2),
    context_keywords=["eth", "ethereum", "wallet", "private", "key", "0x"],
    variable_patterns=[re.compile(r"PRIVATE_KEY", re.I), re.compile(r"ETH_KEY", re.I)],
    description="Ethereum Private Key. Controls wallet funds.",
    risk_level="critical",
    supports_provider_verification=True,
))

_register(SecretFamilyDefinition(
    family="solana_private_key",
    display_type="Solana Private Key",
    provider="solana",
    patterns=[re.compile(r"(?i)solana[_\-]?private[_\-]?key[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9+/]{44,})")],
    context_keywords=["solana", "sol", "wallet", "keypair"],
    description="Solana Private Key / Keypair.",
    risk_level="critical",
))

_register(SecretFamilyDefinition(
    family="bitcoin_wif",
    display_type="Bitcoin WIF",
    provider="bitcoin",
    patterns=[re.compile(r"5[HJK][1-9A-HJ-NP-Za-km-z]{50}")],
    prefixes=["5H", "5J", "5K"],
    min_length=51,
    expected_entropy_range=(4.0, 6.0),
    context_keywords=["bitcoin", "btc", "wif", "wallet", "private"],
    description="Bitcoin Wallet Import Format private key.",
    risk_level="critical",
))

# ── Generic / Unknown ────────────────────────────────────────────────

_register(SecretFamilyDefinition(
    family="generic_base64_secret",
    display_type="Generic Base64 Secret",
    provider="",
    patterns=[re.compile(r"(?i)(?:secret|password|key|token|credential)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9+/=]{32,})")],
    min_length=32,
    expected_entropy_range=(3.0, 6.0),
    context_keywords=["secret", "password", "key", "token", "credential"],
    description="Generic base64-encoded secret. Needs review to determine actual type.",
    risk_level="low",
))

_register(SecretFamilyDefinition(
    family="unknown_secret",
    display_type="Unknown Secret",
    provider="",
    patterns=[],
    min_length=10,
    description="Unidentified high-entropy string. Requires manual review.",
    risk_level="low",
))

_register(SecretFamilyDefinition(
    family="needs_review",
    display_type="Needs Review",
    provider="",
    patterns=[],
    min_length=8,
    description="Potential secret requiring manual investigation.",
    risk_level="low",
))


# ── Classification Engine ───────────────────────────────────────────

def classify_secret(
    raw_value: str,
    context: Dict[str, Any] = None,
) -> Tuple[str, str, str]:
    """
    Classify a raw secret value into (family, display_type, provider).

    Uses pattern matching, prefix detection, and context clues.
    Never defaults to "api_key" — always provides a specific
    classification or marks as "unknown_secret"/"needs_review".

    Returns:
        (family, display_type, provider)
    """
    context = context or {}

    # ── Step 1: Pattern matching ────────────────────────────────────
    for family_name, defn in FAMILIES.items():
        for pattern in defn.patterns:
            if pattern.search(raw_value):
                # Check prefix match for additional confirmation
                if defn.prefixes:
                    prefix_match = any(raw_value.startswith(p) for p in defn.prefixes)
                    if prefix_match:
                        return defn.family, defn.display_type, defn.provider
                    # Pattern matched but prefix didn't — still classify
                    # (some patterns capture the value inside groups)
                    return defn.family, defn.display_type, defn.provider
                return defn.family, defn.display_type, defn.provider

    # ── Step 2: Prefix detection ────────────────────────────────────
    for family_name, defn in FAMILIES.items():
        if defn.prefixes and any(raw_value.startswith(p) for p in defn.prefixes):
            return defn.family, defn.display_type, defn.provider

    # ── Step 3: Context-based classification ────────────────────────
    context_text = " ".join([
        context.get("variable_name", ""),
        context.get("json_key", ""),
        context.get("filename", ""),
        context.get("repository", ""),
    ]).lower()

    if context_text:
        best_match = None
        best_score = 0
        for family_name, defn in FAMILIES.items():
            score = sum(1 for kw in defn.context_keywords if kw in context_text)
            if score > best_score:
                best_score = score
                best_match = defn
        if best_match and best_score >= 2:
            return best_match.family, best_match.display_type, best_match.provider

    # ── Step 4: Entropy-based fallback ──────────────────────────────
    from confidence import calculate_entropy
    entropy = calculate_entropy(raw_value)
    if entropy >= 4.0 and len(raw_value) >= 32:
        # High-entropy string but no specific classification
        # This is NOT an "api_key" — it's a generic base64 secret
        return "generic_base64_secret", "Generic Base64 Secret", ""

    if entropy >= 3.0 and len(raw_value) >= 20:
        return "unknown_secret", "Unknown Secret", ""

    # ── Step 5: Needs review ────────────────────────────────────────
    return "needs_review", "Needs Review", ""


def get_family(family_name: str) -> Optional[SecretFamilyDefinition]:
    """Get a family definition by name."""
    return FAMILIES.get(family_name)


def all_family_names() -> List[str]:
    """Return all registered family names."""
    return sorted(FAMILIES.keys())
