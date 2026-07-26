"""
AlphaScan Intelligence Pipeline.

Replaces the simple Scanner -> Parser -> Validator pipeline with
a layered intelligence pipeline:

  Collectors -> Normalization -> Context Extraction -> Secret Detection
  -> Secret Classification -> Confidence Scoring -> Deduplication
  -> Provider Verification -> Risk Classification -> Storage -> Dashboard

Each stage enriches the secret with progressively more evidence,
producing a canonical Secret model with full metadata,
confidence scoring, verification trail, and deduplication history.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from models import Finding, Secret, ValidationLevel, VerificationStatus, HistoryEntry
from secret_families import classify_secret
from confidence import compute_confidence, ConfidenceResult
from context_extraction import extract_context, ContextResult
from deduplication import deduplicate_secrets, DeduplicationResult
from provider_verifiers import verify_secret_provider, ProviderVerificationResult
from storage import Storage, get_storage
from metrics import compute_metrics, ScanMetrics

logger = logging.getLogger(__name__)


class IntelligencePipeline:
    """
    Layered intelligence pipeline that transforms raw scan findings
    into high-confidence, verified secrets with full evidence trails.
    """

    def __init__(self, storage: Storage = None) -> None:
        self.storage = storage or get_storage()
        self._pipeline_stats: Dict[str, Any] = {
            "collectors": 0,
            "normalization": 0,
            "context_extraction": 0,
            "secret_detection": 0,
            "confidence_scoring": 0,
            "deduplication": 0,
            "provider_verification": 0,
            "risk_classification": 0,
            "storage": 0,
        }

    def process_findings(self, findings: List[Finding]) -> Tuple[List[Secret], ScanMetrics]:
        """
        Run the full intelligence pipeline on a batch of findings.

        Returns (enriched_secrets, scan_metrics).
        """
        if not findings:
            return [], ScanMetrics()

        pipeline_start = datetime.now(timezone.utc)
        logger.info(f"Starting intelligence pipeline with {len(findings)} findings")

        # ── Stage 1: Collectors ──────────────────────────────────
        raw_secrets = []
        for finding in findings:
            for secret_data in finding.extracted_secrets:
                secret = Secret(
                    source=finding.source,
                    finding_target=finding.target,
                    repository=finding.metadata.get("repo", ""),
                    organization=finding.metadata.get("organization", ""),
                    file=finding.metadata.get("path", ""),
                    scanner=finding.source,
                    discovered_at=finding.timestamp,
                    raw_value=secret_data.get("value", ""),
                )
                raw_secrets.append(secret)
        self._pipeline_stats["collectors"] = len(raw_secrets)
        logger.info(f"Collectors: {len(raw_secrets)} raw secrets from {len(findings)} findings")

        if not raw_secrets:
            logger.warning("No secrets extracted from findings")
            return [], ScanMetrics()

        # ── Stage 2: Normalization ────────────────────────────────
        for secret in raw_secrets:
            if not secret.discovered_at:
                secret.discovered_at = datetime.now(timezone.utc).isoformat()
            if secret.raw_value and not secret.masked_value:
                secret.masked_value = Secret._mask(secret.raw_value, secret.secret_type)
            secret.history.append(HistoryEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event="discovered",
                details={
                    "source": secret.source,
                    "finding_target": secret.finding_target,
                    "repository": secret.repository,
                },
            ))
        self._pipeline_stats["normalization"] = len(raw_secrets)
        logger.info(f"Normalization: {len(raw_secrets)} secrets normalized")

        # ── Stage 3: Context Extraction ────────────────────────────
        for secret in raw_secrets:
            context = extract_context(
                raw_value=secret.raw_value,
                source=secret.source,
                repository=secret.repository,
                organization=secret.organization,
                filename=secret.file,
                file_path=secret.metadata.get("path", ""),
                content=secret.metadata.get("content", ""),
                metadata=secret.metadata,
            )
            secret.metadata.update(context.to_dict())
        self._pipeline_stats["context_extraction"] = len(raw_secrets)
        logger.info(f"Context extraction: {len(raw_secrets)} secrets enriched")

        # ── Stage 4: Secret Classification ─────────────────────────
        for secret in raw_secrets:
            if not secret.secret_family or not secret.secret_type:
                family, display_type, provider = classify_secret(
                    secret.raw_value,
                    context={
                        "variable_name": secret.metadata.get("variable_name", ""),
                        "json_key": secret.metadata.get("json_key", ""),
                        "filename": secret.file,
                        "repository": secret.repository,
                    },
                )
                secret.secret_family = family
                secret.secret_type = display_type
                secret.provider = provider
                secret.history.append(HistoryEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event="classified",
                    details={
                        "secret_family": family,
                        "secret_type": display_type,
                        "provider": provider,
                    },
                ))
        self._pipeline_stats["secret_detection"] = len(raw_secrets)
        logger.info(f"Classification: {len(raw_secrets)} secrets classified")

        # ── Stage 5: Confidence Scoring ──────────────────────────────
        for secret in raw_secrets:
            confidence_result = compute_confidence(
                raw_value=secret.raw_value,
                secret_family=secret.secret_family,
                pattern_matched=secret.secret_family not in ("unknown_secret", "needs_review"),
                variable_name=secret.metadata.get("variable_name", ""),
                filename=secret.file,
                repository=secret.repository,
                organization=secret.organization or "",
                occurrences=secret.metadata.get("occurrences", 1),
                ai_confidence=secret.metadata.get("ai_confidence", 0.0),
            )
            secret.confidence_score = confidence_result.total_score
            secret.metadata["confidence_breakdown"] = confidence_result.to_dict()

            if confidence_result.total_score >= 70:
                secret.validation_level = ValidationLevel.HEURISTIC
            elif confidence_result.total_score >= 40:
                secret.validation_level = ValidationLevel.FORMAT
            else:
                secret.validation_level = ValidationLevel.NONE
        self._pipeline_stats["confidence_scoring"] = len(raw_secrets)
        logger.info(f"Confidence scoring: {len(raw_secrets)} secrets scored")

        # ── Stage 6: Deduplication ──────────────────────────────────
        dedup_result = deduplicate_secrets(raw_secrets)
        unique_secrets = dedup_result.unique_secrets
        self._pipeline_stats["deduplication"] = {
            "total_input": dedup_result.total_input,
            "unique_count": len(unique_secrets),
            "duplicates_found": dedup_result.duplicates_found,
            "merged_count": dedup_result.merged_count,
        }
        logger.info(
            f"Deduplication: {dedup_result.total_input} -> "
            f"{len(unique_secrets)} unique, "
            f"{dedup_result.duplicates_found} duplicates"
        )

        # ── Stage 7: Provider Verification ──────────────────────────
        for secret in unique_secrets:
            if secret.provider and secret.raw_value:
                verification_result = verify_secret_provider(
                    secret.provider,
                    secret.raw_value,
                    context={
                        "repository": secret.repository,
                        "variable_name": secret.metadata.get("variable_name", ""),
                    },
                )
                secret.verification_status = verification_result.status
                secret.verification_reason = verification_result.reason
                secret.verified_at = verification_result.verified_at
                if verification_result.provider_response:
                    secret.provider_status = str(verification_result.provider_response)
                    secret.metadata["provider_response"] = verification_result.provider_response

                # Update validation level based on verification
                if verification_result.status == VerificationStatus.ACTIVE:
                    secret.validation_level = ValidationLevel.ACTIVE
                elif verification_result.status in (
                    VerificationStatus.VALID_FORMAT,
                    VerificationStatus.INSUFFICIENT_SCOPE,
                ):
                    if secret.validation_level.rank < ValidationLevel.PROVIDER.rank:
                        secret.validation_level = ValidationLevel.PROVIDER

                secret.history.append(HistoryEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event="provider_verified",
                    details={
                        "verification_status": verification_result.status.value,
                        "verification_reason": verification_result.reason,
                    },
                ))
            else:
                secret.verification_status = VerificationStatus.UNKNOWN
                secret.verification_reason = "No provider or raw value available"
        self._pipeline_stats["provider_verification"] = len(unique_secrets)
        logger.info(f"Provider verification: {len(unique_secrets)} secrets verified")

        # ── Stage 8: Risk Classification ──────────────────────────────
        for secret in unique_secrets:
            risk = "low"
            if secret.confidence_score >= 70 and secret.verification_status == VerificationStatus.ACTIVE:
                risk = "critical"
            elif secret.confidence_score >= 70 and secret.verification_status in (
                VerificationStatus.VALID_FORMAT, VerificationStatus.EXPIRED,
                VerificationStatus.REVOKED, VerificationStatus.DISABLED,
                VerificationStatus.INSUFFICIENT_SCOPE,
            ):
                risk = "high"
            elif secret.confidence_score >= 40:
                risk = "medium"
            elif secret.confidence_score < 20:
                risk = "low"

            if secret.metadata.get("is_test_file"):
                risk = "low"

            secret.metadata["risk_classification"] = risk
        self._pipeline_stats["risk_classification"] = len(unique_secrets)
        logger.info(f"Risk classification: {len(unique_secrets)} secrets classified")

        # ── Stage 9: Storage ──────────────────────────────────────────
        self.storage.insert_secrets_batch(unique_secrets)
        self._pipeline_stats["storage"] = len(unique_secrets)
        logger.info(f"Storage: {len(unique_secrets)} secrets persisted")

        # ── Stage 10: Metrics ─────────────────────────────────────────
        metrics = compute_metrics(unique_secrets)
        metrics.assets_crawled = len(findings)
        self._pipeline_stats["metrics"] = metrics.to_dict()

        pipeline_duration = (datetime.now(timezone.utc) - pipeline_start).total_seconds()
        logger.info(
            f"Pipeline completed in {pipeline_duration:.2f}s: "
            f"{len(unique_secrets)} secrets processed"
        )

        return unique_secrets, metrics

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get current pipeline execution statistics."""
        return self._pipeline_stats

    def reset_stats(self) -> None:
        """Reset pipeline statistics."""
        self._pipeline_stats = {
            "collectors": 0,
            "normalization": 0,
            "context_extraction": 0,
            "secret_detection": 0,
            "confidence_scoring": 0,
            "deduplication": 0,
            "provider_verification": 0,
            "risk_classification": 0,
            "storage": 0,
        }
