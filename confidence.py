"""
AlphaScan Confidence Scoring Engine.

Produces a confidence score between 0 and 100 for each detected secret.
Considers multiple evidence factors and produces a detailed breakdown
explaining WHY each score was assigned.

Factors:
  - Regex pattern confidence (0-25)
  - Variable name relevance (0-15)
  - File/location relevance (0-10)
  - Provider-specific structure (0-20)
  - Entropy (0-15)
  - Length adequacy (0-5)
  - Known prefix match (0-10)
  - Repository context (0-5)
  - Duplicate sightings (0-5)
  - Historical occurrence (0-5)

Example output:
  Confidence 98
  Reason: Matched GitHub Fine-Grained PAT regex (25)
          Variable name GITHUB_TOKEN (15)
          Found inside .env (8)
          Repository metadata consistent (5)
          Known prefix github_pat_ (10)
          High entropy (4.5) (12)
          Adequate length (5)
          Total: 98
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConfidenceFactor:
    """A single factor contributing to the confidence score."""
    name: str
    score: float
    max_score: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "reason": self.reason,
        }


@dataclass
class ConfidenceResult:
    """Complete confidence assessment for a secret."""
    total_score: float           # 0-100
    category: str                # critical, high, medium, low, unlikely
    factors: List[ConfidenceFactor] = field(default_factory=list)
    reason: str = ""             # human-readable explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": round(self.total_score, 2),
            "category": self.category,
            "factors": [f.to_dict() for f in self.factors],
            "reason": self.reason,
        }


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


def _confidence_category(score: float) -> str:
    """Map numeric score to human-readable category."""
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "unlikely"


def _score_regex_confidence(secret_family: str, pattern_matched: bool) -> ConfidenceFactor:
    """Score based on regex pattern match quality."""
    max_score = 25.0
    if not pattern_matched:
        return ConfidenceFactor(
            name="regex_confidence",
            score=0,
            max_score=max_score,
            reason="No regex pattern matched. Classification based on context only.",
        )

    # Families with specific, distinctive patterns score higher
    specificity = {
        "github_classic_pat": 25,
        "github_fine_grained_pat": 25,
        "github_oauth_token": 25,
        "github_app_token": 25,
        "aws_access_key": 25,
        "openai_api": 20,
        "anthropic_api": 20,
        "google_ai_api": 20,
        "stripe_secret_key": 25,
        "stripe_publishable_key": 20,
        "sendgrid_api": 25,
        "discord_bot_token": 25,
        "slack_bot_token": 25,
        "slack_webhook": 25,
        "twilio_sid": 20,
        "rsa_private_key": 25,
        "ssh_private_key": 25,
        "ec_private_key": 25,
        "dsa_private_key": 25,
        "generic_private_key": 25,
        "pgp_private_key": 25,
        "ethereum_private_key": 20,
        "bitcoin_wif": 25,
        "gitlab_pat": 25,
        "jwt": 15,
        "mongodb_uri": 20,
        "postgresql_uri": 20,
        "mysql_uri": 20,
        "redis_uri": 20,
        "generic_base64_secret": 10,
        "unknown_secret": 5,
        "needs_review": 5,
    }

    score = specificity.get(secret_family, 10)
    family_display = secret_family.replace("_", " ").title()
    return ConfidenceFactor(
        name="regex_confidence",
        score=score,
        max_score=max_score,
        reason=f"Matched {family_display} regex pattern",
    )


def _score_variable_name(variable_name: str, secret_family: str) -> ConfidenceFactor:
    """Score based on variable name relevance."""
    max_score = 15.0
    if not variable_name:
        return ConfidenceFactor(
            name="variable_name",
            score=0,
            max_score=max_score,
            reason="No variable name context available.",
        )

    vn_lower = variable_name.lower()

    # Check if variable name contains provider/family keywords
    from secret_families import get_family
    defn = get_family(secret_family)
    if defn:
        keyword_matches = sum(1 for kw in defn.context_keywords if kw in vn_lower)
        if keyword_matches >= 3:
            score = max_score
            reason = f"Variable name '{variable_name}' strongly matches {defn.display_type}"
        elif keyword_matches >= 1:
            score = keyword_matches * 5.0
            reason = f"Variable name '{variable_name}' partially matches {defn.display_type}"
        else:
            # Check variable patterns
            pattern_matches = sum(1 for p in defn.variable_patterns if p.search(variable_name))
            if pattern_matches >= 1:
                score = max_score
                reason = f"Variable name '{variable_name}' matches expected pattern for {defn.display_type}"
            else:
                score = 0
                reason = f"Variable name '{variable_name}' does not match expected patterns"
    else:
        score = 0
        reason = f"Variable name '{variable_name}' — no family definition available"

    return ConfidenceFactor(name="variable_name", score=score, max_score=max_score, reason=reason)


def _score_file_relevance(filename: str, secret_family: str) -> ConfidenceFactor:
    """Score based on file location and name relevance."""
    max_score = 10.0
    if not filename:
        return ConfidenceFactor(
            name="file_relevance",
            score=0,
            max_score=max_score,
            reason="No file path context available.",
        )

    fn_lower = filename.lower()

    # Known secret-bearing filenames score higher
    high_relevance = [".env", "credentials", "secrets", "config", "settings", ".htpasswd"]
    medium_relevance = ["docker-compose", "dockerfile", "application", "deploy", "terraform", "ansible"]

    for pattern in high_relevance:
        if pattern in fn_lower:
            score = max_score
            return ConfidenceFactor(
                name="file_relevance",
                score=score,
                max_score=max_score,
                reason=f"Found in high-risk file: '{filename}'",
            )

    for pattern in medium_relevance:
        if pattern in fn_lower:
            score = 6.0
            return ConfidenceFactor(
                name="file_relevance",
                score=score,
                max_score=max_score,
                reason=f"Found in configuration file: '{filename}'",
            )

    # Check family-specific filename patterns
    from secret_families import get_family
    defn = get_family(secret_family)
    if defn:
        pattern_matches = sum(1 for p in defn.filename_patterns if p.search(filename))
        if pattern_matches:
            score = max_score
            return ConfidenceFactor(
                name="file_relevance",
                score=score,
                max_score=max_score,
                reason=f"Filename '{filename}' matches expected pattern for {defn.display_type}",
            )

    score = 2.0
    return ConfidenceFactor(
        name="file_relevance",
        score=score,
        max_score=max_score,
        reason=f"Found in file: '{filename}' (low relevance)",
    )


def _score_provider_structure(raw_value: str, secret_family: str) -> ConfidenceFactor:
    """Score based on provider-specific structural properties."""
    max_score = 20.0
    if not raw_value or not secret_family:
        return ConfidenceFactor(
            name="provider_structure",
            score=0,
            max_score=max_score,
            reason="No value or family classification available.",
        )

    from secret_families import get_family
    defn = get_family(secret_family)
    if not defn:
        return ConfidenceFactor(
            name="provider_structure",
            score=0,
            max_score=max_score,
            reason="No family definition available for structure check.",
        )

    score = 0
    reasons = []

    # Length check
    if len(raw_value) >= defn.min_length:
        score += 5.0
        reasons.append("adequate length")
    else:
        reasons.append(f"insufficient length ({len(raw_value)} < {defn.min_length})")

    # Prefix check
    if defn.prefixes and any(raw_value.startswith(p) for p in defn.prefixes):
        score += 10.0
        reasons.append(f"known prefix '{raw_value[:len(defn.prefixes[0])]}'")
    elif defn.prefixes:
        reasons.append("prefix mismatch")

    # Entropy check within expected range
    entropy = calculate_entropy(raw_value)
    low, high = defn.expected_entropy_range
    if low <= entropy <= high:
        score += 5.0
        reasons.append(f"entropy {entropy:.2f} within expected range [{low}-{high}]")
    elif entropy > high:
        score += 2.0
        reasons.append(f"entropy {entropy:.2f} above expected range")
    else:
        score += 1.0
        reasons.append(f"entropy {entropy:.2f} below expected range")

    return ConfidenceFactor(
        name="provider_structure",
        score=score,
        max_score=max_score,
        reason=f"Provider structure: {', '.join(reasons)}",
    )


def _score_entropy(raw_value: str) -> ConfidenceFactor:
    """Score based on Shannon entropy of the value."""
    max_score = 15.0
    entropy = calculate_entropy(raw_value)

    if entropy >= 5.0:
        score = max_score
        category = "very high"
    elif entropy >= 4.0:
        score = 12.0
        category = "high"
    elif entropy >= 3.0:
        score = 8.0
        category = "medium"
    elif entropy >= 2.0:
        score = 4.0
        category = "low"
    else:
        score = 1.0
        category = "very low"

    return ConfidenceFactor(
        name="entropy",
        score=score,
        max_score=max_score,
        reason=f"Entropy {entropy:.2f} ({category})",
    )


def _score_length(raw_value: str) -> ConfidenceFactor:
    """Score based on value length adequacy."""
    max_score = 5.0
    if not raw_value:
        return ConfidenceFactor(name="length", score=0, max_score=max_score, reason="Empty value")

    if len(raw_value) >= 32:
        score = max_score
        reason = f"Length {len(raw_value)} — sufficient for a real secret"
    elif len(raw_value) >= 20:
        score = 3.0
        reason = f"Length {len(raw_value)} — moderate"
    elif len(raw_value) >= 12:
        score = 1.0
        reason = f"Length {len(raw_value)} — short, could be test value"
    else:
        score = 0
        reason = f"Length {len(raw_value)} — too short to be a real secret"

    return ConfidenceFactor(name="length", score=score, max_score=max_score, reason=reason)


def _score_known_prefix(raw_value: str) -> ConfidenceFactor:
    """Score based on known provider prefix detection."""
    max_score = 10.0

    known_prefixes = {
        "ghp_": ("GitHub Classic PAT", 10),
        "github_pat_": ("GitHub Fine-Grained PAT", 10),
        "gho_": ("GitHub OAuth Token", 10),
        "ghs_": ("GitHub App Token", 10),
        "ghr_": ("GitHub Refresh Token", 10),
        "glpat-": ("GitLab PAT", 10),
        "AKIA": ("AWS Access Key", 10),
        "sk-": ("OpenAI API Key", 8),
        "sk-ant-": ("Anthropic API Key", 10),
        "AIza": ("Google AI API Key", 10),
        "sk_live_": ("Stripe Secret Key", 10),
        "sk_test_": ("Stripe Test Key", 8),
        "pk_live_": ("Stripe Publishable Key", 10),
        "SG.": ("SendGrid API Key", 10),
        "xoxb-": ("Slack Bot Token", 10),
        "0x": ("Ethereum Private Key", 6),
        "5H": ("Bitcoin WIF", 8),
        "5J": ("Bitcoin WIF", 8),
        "5K": ("Bitcoin WIF", 8),
        "AC": ("Twilio SID", 8),
        "key-": ("Mailgun API Key", 8),
        "eyJ": ("JWT", 6),
    }

    for prefix, (type_name, score) in known_prefixes.items():
        if raw_value.startswith(prefix):
            return ConfidenceFactor(
                name="known_prefix",
                score=score,
                max_score=max_score,
                reason=f"Known provider prefix: '{prefix}' ({type_name})",
            )

    return ConfidenceFactor(
        name="known_prefix",
        score=0,
        max_score=max_score,
        reason="No known provider prefix detected",
    )


def _score_repo_context(repository: str, organization: str) -> ConfidenceFactor:
    """Score based on repository and organization context."""
    max_score = 5.0
    if not repository and not organization:
        return ConfidenceFactor(
            name="repo_context",
            score=0,
            max_score=max_score,
            reason="No repository or organization context",
        )

    # Test/demo repos reduce confidence
    repo_lower = (repository or "").lower()
    org_lower = (organization or "").lower()

    test_indicators = ["test", "demo", "example", "sample", "tutorial", "playground", "sandbox", "fixture"]
    for indicator in test_indicators:
        if indicator in repo_lower or indicator in org_lower:
            return ConfidenceFactor(
                name="repo_context",
                score=1.0,
                max_score=max_score,
                reason=f"Repository/org appears to be a test/demo: '{repository}'",
            )

    score = 3.0
    return ConfidenceFactor(
        name="repo_context",
        score=score,
        max_score=max_score,
        reason=f"Repository: '{repository}', Organization: '{organization}'",
    )


def _score_duplicate_sightings(occurrences: int) -> ConfidenceFactor:
    """Score based on how many times this secret has been seen."""
    max_score = 5.0
    if occurrences <= 1:
        return ConfidenceFactor(
            name="duplicate_sightings",
            score=2.0,
            max_score=max_score,
            reason="First-time sighting",
        )
    if occurrences <= 3:
        return ConfidenceFactor(
            name="duplicate_sightings",
            score=4.0,
            max_score=max_score,
            reason=f"Seen {occurrences} times — repeated sighting increases confidence",
        )
    return ConfidenceFactor(
        name="duplicate_sightings",
        score=max_score,
        max_score=max_score,
        reason=f"Seen {occurrences} times — frequent sighting strongly increases confidence",
    )


def compute_confidence(
    raw_value: str,
    secret_family: str = "",
    pattern_matched: bool = False,
    variable_name: str = "",
    filename: str = "",
    repository: str = "",
    organization: str = "",
    occurrences: int = 1,
    ai_confidence: float = 0.0,
) -> ConfidenceResult:
    """
    Compute a comprehensive confidence score for a secret.

    Produces a score between 0 and 100 with a detailed breakdown
    explaining every factor that contributed.

    Args:
        raw_value: The secret value itself
        secret_family: Classified family name (e.g. "github_pat")
        pattern_matched: Whether a regex pattern matched
        variable_name: Variable/key name where the secret was found
        filename: File path where the secret was found
        repository: Repository name
        organization: Organization name
        occurrences: How many times this secret has been seen
        ai_confidence: AI classifier confidence (0-100), if available

    Returns:
        ConfidenceResult with total score, category, factors, and reason
    """
    factors = []

    # Factor 1: Regex confidence
    factors.append(_score_regex_confidence(secret_family, pattern_matched))

    # Factor 2: Variable name relevance
    factors.append(_score_variable_name(variable_name, secret_family))

    # Factor 3: File/location relevance
    factors.append(_score_file_relevance(filename, secret_family))

    # Factor 4: Provider-specific structure
    factors.append(_score_provider_structure(raw_value, secret_family))

    # Factor 5: Entropy
    factors.append(_score_entropy(raw_value))

    # Factor 6: Length
    factors.append(_score_length(raw_value))

    # Factor 7: Known prefix
    factors.append(_score_known_prefix(raw_value))

    # Factor 8: Repository context
    factors.append(_score_repo_context(repository, organization))

    # Factor 9: Duplicate sightings
    factors.append(_score_duplicate_sightings(occurrences))

    # Compute total score (capped at 100)
    total = sum(f.score for f in factors)
    total = min(total, 100.0)

    # Add AI confidence bonus (if provided)
    if ai_confidence > 0:
        # AI confidence is weighted as additional evidence
        ai_bonus = ai_confidence * 0.15  # max 15 additional points
        total = min(total + ai_bonus, 100.0)

    # Build reason string
    reason_lines = [f"Confidence {round(total, 1)}"]
    for f in factors:
        if f.score > 0:
            reason_lines.append(f"  {f.reason} ({round(f.score, 1)} pts)")
    if ai_confidence > 0:
        reason_lines.append(f"  AI classifier confidence {ai_confidence}% ({round(ai_confidence * 0.15, 1)} pts)")

    category = _confidence_category(total)

    return ConfidenceResult(
        total_score=total,
        category=category,
        factors=factors,
        reason="\n".join(reason_lines),
    )
