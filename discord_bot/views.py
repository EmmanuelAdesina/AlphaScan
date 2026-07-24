"""
Discord Views and Buttons for AlphaScan v0.5
Interactive components including dashboard buttons, endpoints verification, key validation, and system health.
"""
import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime
import discord
from discord.ui import View, Button, button, Modal, TextInput
from discord import Interaction

logger = logging.getLogger(__name__)


class MainDashboardView(View):
    """Main dashboard with action buttons."""

    def __init__(self, engine=None, timeout=600):
        super().__init__(timeout=timeout)
        self.engine = engine
        self.processing = set()

    @button(label="🟢 Start Scan", style=discord.ButtonStyle.green)
    async def start_scan_button(self, interaction: Interaction, button: Button):
        """Start a scan cycle."""
        if self._check_processing(interaction.user.id, button.label):
            await interaction.response.send_message(
                "⏳ This action is already running. Please wait...",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer()
            self._add_processing(interaction.user.id, button.label)

            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized"),
                    ephemeral=True,
                )
                return

            # Queue scan
            self.engine.state.force_scan = True

            embed = discord.Embed(
                title="✅ Scan Started",
                description="A new scan cycle has been queued and will execute shortly.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow(),
            )
            embed.set_footer(text="AlphaScan v0.5")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Scan started by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in start_scan_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to start scan: {str(e)}"),
                ephemeral=True,
            )
        finally:
            self._remove_processing(interaction.user.id, button.label)

    @button(label="📊 Scan Status", style=discord.ButtonStyle.blurple)
    async def scan_status_button(self, interaction: Interaction, button: Button):
        """Show current scan status."""
        try:
            await interaction.response.defer()

            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized"),
                    ephemeral=True,
                )
                return

            status = self.engine.get_status()
            embed = self._create_status_embed(status)

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Scan status requested by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in scan_status_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to get status: {str(e)}"),
                ephemeral=True,
            )

    @button(label="🔑 Review Keys", style=discord.ButtonStyle.blurple)
    async def review_keys_button(self, interaction: Interaction, button: Button):
        """Review discovered keys."""
        try:
            await interaction.response.defer()

            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized"),
                    ephemeral=True,
                )
                return

            keys = self.engine.get_keys()
            embed = self._create_keys_embed(keys)

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Keys reviewed by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in review_keys_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to get keys: {str(e)}"),
                ephemeral=True,
            )

    @button(label="🌐 Verify Endpoints", style=discord.ButtonStyle.primary)
    async def verify_endpoints_button(self, interaction: Interaction, button: Button):
        """Verify all endpoints."""
        if self._check_processing(interaction.user.id, button.label):
            await interaction.response.send_message(
                "⏳ Verification already running. Please wait...",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer()
            self._add_processing(interaction.user.id, button.label)

            # Show progress
            progress_embed = discord.Embed(
                title="🔍 Verifying Endpoints",
                description="Checking all configured endpoints...",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            progress_embed.set_footer(text="AlphaScan v0.5")
            msg = await interaction.followup.send(embed=progress_embed, ephemeral=True)

            # Perform verification
            from discord_bot.verifiers import EndpointVerifier

            verifier = EndpointVerifier()
            results = await verifier.verify_all()

            # Create result embed
            embed = self._create_endpoints_embed(results)

            # Update message with results
            await msg.edit(embed=embed)
            logger.info(f"Endpoint verification completed for {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in verify_endpoints_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to verify endpoints: {str(e)}"),
                ephemeral=True,
            )
        finally:
            self._remove_processing(interaction.user.id, button.label)

    @button(label="📈 Metrics", style=discord.ButtonStyle.primary)
    async def metrics_button(self, interaction: Interaction, button: Button):
        """Show system metrics."""
        try:
            await interaction.response.defer()

            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized"),
                    ephemeral=True,
                )
                return

            # Get metrics from improver
            if hasattr(self.engine, 'improver') and self.engine.improver:
                metrics = self.engine.improver.get_metrics()
                embed = self._create_metrics_embed(metrics)
            else:
                embed = self._warning_embed(
                    "Metrics Unavailable",
                    "The improvement engine is not initialized."
                )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Metrics requested by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in metrics_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to get metrics: {str(e)}"),
                ephemeral=True,
            )

    @button(label="🔑 Verify Keys", style=discord.ButtonStyle.primary)
    async def verify_keys_button(self, interaction: Interaction, button: Button):
        """Verify all API keys."""
        if self._check_processing(interaction.user.id, button.label):
            await interaction.response.send_message(
                "⏳ Verification already running. Please wait...",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer()
            self._add_processing(interaction.user.id, button.label)

            # Show progress
            progress_embed = discord.Embed(
                title="🔍 Verifying Keys",
                description="Checking all configured API keys...",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            progress_embed.set_footer(text="AlphaScan v0.5")
            msg = await interaction.followup.send(embed=progress_embed, ephemeral=True)

            # Perform verification
            from discord_bot.verifiers import KeyVerifier

            verifier = KeyVerifier()
            results = await verifier.verify_all()

            # Create result embed
            embed = self._create_keys_verification_embed(results)

            # Update message with results
            await msg.edit(embed=embed)
            logger.info(f"Key verification completed for {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in verify_keys_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to verify keys: {str(e)}"),
                ephemeral=True,
            )
        finally:
            self._remove_processing(interaction.user.id, button.label)

    @button(label="🩺 System Health", style=discord.ButtonStyle.primary)
    async def system_health_button(self, interaction: Interaction, button: Button):
        """Show system health information."""
        try:
            await interaction.response.defer()

            from discord_bot.health import HealthMonitor

            monitor = HealthMonitor(self.engine)
            health = await monitor.get_health()

            embed = self._create_health_embed(health)

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"System health requested by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in system_health_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to get system health: {str(e)}"),
                ephemeral=True,
            )

    @button(label="❌ Cancel Scan", style=discord.ButtonStyle.red)
    async def cancel_scan_button(self, interaction: Interaction, button: Button):
        """Cancel current scan."""
        try:
            await interaction.response.defer()

            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized"),
                    ephemeral=True,
                )
                return

            self.engine.stop()

            embed = discord.Embed(
                title="❌ Scan Cancelled",
                description="The current scan cycle has been stopped.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow(),
            )
            embed.set_footer(text="AlphaScan v0.5")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Scan cancelled by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in cancel_scan_button: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to cancel scan: {str(e)}"),
                ephemeral=True,
            )

    # ─── Helper Methods ───

    def _check_processing(self, user_id: int, action: str) -> bool:
        """Check if action is already processing."""
        key = (user_id, action)
        return key in self.processing

    def _add_processing(self, user_id: int, action: str):
        """Mark action as processing."""
        key = (user_id, action)
        self.processing.add(key)

    def _remove_processing(self, user_id: int, action: str):
        """Mark action as complete."""
        key = (user_id, action)
        self.processing.discard(key)

    def _create_status_embed(self, status: dict) -> discord.Embed:
        """Create status embed."""
        embed = discord.Embed(
            title="📊 Scan Status",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name="Running",
            value="✅ Yes" if status.get("running") else "❌ No",
            inline=True,
        )
        embed.add_field(
            name="Cycle",
            value=f"#{status.get('cycle', 0)}",
            inline=True,
        )
        embed.add_field(
            name="Total Keys",
            value=str(status.get("total_keys_found", 0)),
            inline=True,
        )
        embed.add_field(
            name="Total Scans",
            value=str(status.get("total_scans", 0)),
            inline=True,
        )
        embed.add_field(
            name="Last Scan",
            value=status.get("last_scan_time") or "Never",
            inline=True,
        )
        embed.add_field(
            name="Enabled Scanners",
            value=", ".join(status.get("enabled_scanners", [])) or "None",
            inline=False,
        )

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _create_keys_embed(self, keys: list) -> discord.Embed:
        """Create keys embed."""
        embed = discord.Embed(
            title=f"🔑 Discovered Keys ({len(keys)})",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        if not keys:
            embed.description = "No keys discovered yet."
        else:
            # Group by type
            by_type = {}
            for key in keys:
                key_type = key.get("type", "generic")
                by_type.setdefault(key_type, []).append(key)

            for key_type, type_keys in by_type.items():
                embed.add_field(
                    name=key_type.upper(),
                    value=f"{len(type_keys)} key(s)",
                    inline=True,
                )

            embed.add_field(
                name="Total",
                value=str(len(keys)),
                inline=False,
            )

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _create_endpoints_embed(self, results: dict) -> discord.Embed:
        """Create endpoints verification embed."""
        embed = discord.Embed(
            title="🌐 Endpoint Verification Results",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )

        online = results.get("online", [])
        offline = results.get("offline", [])
        slow = results.get("slow", [])

        for endpoint in online:
            embed.add_field(
                name=f"✅ {endpoint['name']}",
                value=f"Status: Online\nLatency: {endpoint.get('latency', 'N/A')}ms",
                inline=False,
            )

        for endpoint in offline:
            embed.add_field(
                name=f"❌ {endpoint['name']}",
                value=f"Status: {endpoint.get('error', 'Offline')}",
                inline=False,
            )

        for endpoint in slow:
            embed.add_field(
                name=f"⚠️ {endpoint['name']}",
                value=f"Status: Slow\nLatency: {endpoint.get('latency', 'N/A')}ms",
                inline=False,
            )

        # Summary
        summary = f"Online: {len(online)} | Offline: {len(offline)} | Slow: {len(slow)}"
        embed.add_field(name="Summary", value=summary, inline=False)

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _create_keys_verification_embed(self, results: dict) -> discord.Embed:
        """Create keys verification embed."""
        embed = discord.Embed(
            title="🔑 Key Verification Results",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        for provider, status in results.items():
            if status.get("valid"):
                emoji = "✅"
                color_name = "Valid"
            elif status.get("invalid"):
                emoji = "❌"
                color_name = "Invalid"
            elif status.get("rate_limited"):
                emoji = "⚠️"
                color_name = "Rate Limited"
            else:
                emoji = "❓"
                color_name = "Unknown"

            embed.add_field(
                name=f"{emoji} {provider}",
                value=f"Status: {color_name}\nLoaded: {'Yes' if status.get('loaded') else 'No'}",
                inline=False,
            )

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _create_metrics_embed(self, metrics: dict) -> discord.Embed:
        """Create metrics embed."""
        embed = discord.Embed(
            title="📈 System Metrics",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name="Success Rate",
            value=f"{metrics.get('success_rate', 0):.2%}",
            inline=True,
        )
        embed.add_field(
            name="Improvements",
            value=str(len(metrics.get("improvement_history", []))),
            inline=True,
        )
        embed.add_field(
            name="Deployments",
            value=str(len(metrics.get("deployment_history", []))),
            inline=True,
        )

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _create_health_embed(self, health: dict) -> discord.Embed:
        """Create health embed."""
        embed = discord.Embed(
            title="🩺 System Health",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="CPU Usage", value=health.get("cpu", "N/A"), inline=True)
        embed.add_field(name="RAM Usage", value=health.get("ram", "N/A"), inline=True)
        embed.add_field(
            name="Running Scanners",
            value=str(health.get("running_scanners", 0)),
            inline=True,
        )
        embed.add_field(
            name="Successful Scans",
            value=str(health.get("successful_scans", 0)),
            inline=True,
        )
        embed.add_field(
            name="Failed Scans",
            value=str(health.get("failed_scans", 0)),
            inline=True,
        )
        embed.add_field(
            name="Total Keys",
            value=str(health.get("total_keys", 0)),
            inline=True,
        )
        embed.add_field(
            name="Discord Status",
            value=health.get("discord_status", "Unknown"),
            inline=True,
        )

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _error_embed(self, message: str) -> discord.Embed:
        """Create error embed."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _warning_embed(self, title: str, message: str) -> discord.Embed:
        """Create warning embed."""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=message,
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="AlphaScan v0.5")
        return embed
