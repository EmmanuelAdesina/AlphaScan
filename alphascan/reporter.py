"""
AlphaScan Discord Reporter.
Sends clean, ranked reports (0-10) to Discord via webhook.
No classes. Simple functions.
"""
import logging
from typing import Dict, List, Optional

import requests

from alphascan.config import DISCORD_WEBHOOK_URL, MAX_KEYS_PER_REPORT

logger = logging.getLogger(__name__)


# ── Rank Names and Colors ─────────────────────────────────────────

RANK_INFO = {
    0:  {"name": "🔴 SSH Private Keys", "color": 0xFF0000},
    1:  {"name": "🟠 Crypto Exchange Keys (Withdrawal)", "color": 0xFF4500},
    2:  {"name": "🟠 Wallet Private Keys / Seed Phrases", "color": 0xFF8C00},
    3:  {"name": "🟡 Hot Wallet Server Keys", "color": 0xFFA500},
    4:  {"name": "🟡 DeFi Protocol Admin Keys", "color": 0xFFD700},
    5:  {"name": "🟣 RPC Provider Keys", "color": 0x9932CC},
    6:  {"name": "🟣 Smart Contract Deployment Keys", "color": 0xBA55D3},
    7:  {"name": "🔵 Cloud Provider Keys", "color": 0x1E90FF},
    8:  {"name": "🟢 Payment Processor Keys", "color": 0x32CD32},
    9:  {"name": "🟢 AI Provider Keys", "color": 0x00CED1},
    10: {"name": "🔵 Dev Platform Keys", "color": 0x5865F2},
}


def get_rank_name(rank: int) -> str:
    """Get human-readable name for a rank."""
    return RANK_INFO.get(rank, {}).get("name", f"Unknown ({rank})")


def get_rank_color(rank: int) -> int:
    """Get Discord embed color for a rank."""
    return RANK_INFO.get(rank, {}).get("color", 0x5865F2)


def mask_value(value: str, key_type: str = "") -> str:
    """Mask a key value for safe display, showing first 6 chars."""
    if not value:
        return "[empty]"
    if len(value) <= 10:
        return value[:4] + "..."
    # For SSH keys, just show type indicator
    if key_type.startswith("ssh_"):
        return f"[ssh_key:{len(value)}_chars]"
    # For private keys, show first 6 chars
    if key_type in ("eth_private_key", "btc_wif"):
        return value[:6] + "..." + value[-4:]
    # For API keys, show prefix + first few chars
    return value[:8] + "..." + value[-4:] if len(value) > 16 else value[:6] + "..."


def send_discord(content: str, embeds: Optional[List[Dict]] = None) -> bool:
    """
    Send a message to Discord via webhook.
    Returns True if sent successfully.
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook not configured")
        return False

    payload: Dict = {"content": content}
    if embeds:
        payload["embeds"] = embeds

    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10,
            headers={"User-Agent": "AlphaScan/1.0"},
        )
        if resp.status_code >= 400:
            logger.error(f"Discord webhook returned {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except requests.RequestException as e:
        logger.error(f"Discord webhook failed: {e}")
        return False


def send_status(cycle: int, duration: float, keys_found: int, scanners_used: List[str]) -> bool:
    """Send a scan status update to Discord."""
    lines = [
        "📡 **AlphaScan Status**",
        f"• Cycle #{cycle} completed in {duration:.1f}s",
        f"• Found {keys_found} potential key(s)",
        f"• Scanners: {', '.join(s for s in scanners_used if s)}",
        f"• Next scan in ~5m",
    ]
    return send_discord("\n".join(lines))


def send_key_report(keys: List[Dict]) -> bool:
    """
    Send a clean, ranked key report to Discord.
    Keys are grouped by rank (0-10).
    """
    if not keys:
        return send_discord("🔑 **AlphaScan** — No validated keys found in this cycle.")

    # Limit keys
    keys = keys[:MAX_KEYS_PER_REPORT]

    # Group by rank
    by_rank: Dict[int, List[Dict]] = {}
    for key in keys:
        rank = key.get("rank", 10)
        by_rank.setdefault(rank, []).append(key)

    # Sort ranks (lowest = most critical first)
    sorted_ranks = sorted(by_rank.keys())

    embeds = []
    total_valid = sum(1 for k in keys if k.get("valid", False))
    total_invalid = sum(1 for k in keys if not k.get("valid", False))

    for rank in sorted_ranks:
        rank_keys = by_rank[rank]
        rank_name = get_rank_name(rank)
        color = get_rank_color(rank)

        # Build fields for this rank group
        fields = []
        for key in rank_keys:
            val = mask_value(key.get("value", ""), key.get("type", ""))
            valid_status = "✅" if key.get("valid") else "❌"
            summary = key.get("validation_summary", "")
            entropy = key.get("entropy", "")
            wallet = key.get("wallet_balance_eth", "")

            field_value = f"`{val}`"
            if entropy:
                field_value += f"\nEntropy: {entropy}"
            if wallet:
                field_value += f"\nBalance: {wallet} ETH"
            if summary:
                field_value += f"\n{valid_status} {summary}"

            fields.append({
                "name": f"{key.get('type', 'unknown')}",
                "value": field_value,
                "inline": False,
            })

            # Discord has 25 field limit per embed
            if len(fields) >= 20:
                break

        embeds.append({
            "title": f"{rank_name} ({len(rank_keys)} found)",
            "color": color,
            "fields": fields,
        })

        # Discord has 10 embed limit per webhook
        if len(embeds) >= 10:
            break

    # Summary line
    summary = (
        f"🔑 **AlphaScan — Key Report**\n"
        f"📊 {len(keys)} total | ✅ {total_valid} valid | ❌ {total_invalid} failed "
        f"| Ranks 0-10 (0=critical, 10=lowest)"
    )

    return send_discord(summary, embeds)


def send_error(error: str, context: str = "") -> bool:
    """Send an error notification to Discord."""
    msg = f"❌ **AlphaScan Error**\n• {error}"
    if context:
        msg += f"\n• Context: {context}"
    return send_discord(msg)


def send_info(message: str) -> bool:
    """Send an informational message to Discord."""
    return send_discord(f"ℹ️ {message}")