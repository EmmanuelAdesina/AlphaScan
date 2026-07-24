"""
AlphaScan v0.5 - Discord Bot
Comprehensive Discord integration with interactive dashboard, buttons, and real-time monitoring.
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction

# Configure logging
logger = logging.getLogger(__name__)


class AlphaScanBot(commands.Cog):
    """Main Discord bot for AlphaScan v0.5."""

    def __init__(self, bot: commands.Bot, engine=None):
        self.bot = bot
        self.engine = engine
        self.processing = set()  # Track ongoing operations
        logger.info("AlphaScan Discord Bot initialized")

    async def cog_load(self):
        """Called when cog is loaded."""
        logger.info("AlphaScan cog loaded successfully")

    async def cog_unload(self):
        """Called when cog is unloaded."""
        logger.info("AlphaScan cog unloaded")

    @app_commands.command(name="scan", description="Trigger an immediate scan cycle")
    async def slash_scan(self, interaction: Interaction):
        """Slash command to trigger a scan."""
        try:
            await interaction.response.defer(thinking=True)
            
            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized")
                )
                return

            # Trigger scan
            self.engine.state.force_scan = True
            await interaction.followup.send(
                embed=self._success_embed(
                    "Scan Queued",
                    "An immediate scan cycle has been queued and will start shortly."
                )
            )
            logger.info("Scan triggered via Discord slash command")
        except Exception as e:
            logger.error(f"Error in slash_scan: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to trigger scan: {str(e)}")
            )

    @app_commands.command(name="status", description="Get current engine status")
    async def slash_status(self, interaction: Interaction):
        """Slash command to get system status."""
        try:
            await interaction.response.defer()
            
            if self.engine is None:
                await interaction.followup.send(
                    embed=self._error_embed("Engine not initialized")
                )
                return

            status = self.engine.get_status()
            embed = self._create_status_embed(status)
            await interaction.followup.send(embed=embed)
            logger.info("Status requested via Discord slash command")
        except Exception as e:
            logger.error(f"Error in slash_status: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to get status: {str(e)}")
            )

    @app_commands.command(name="dashboard", description="Open the interactive dashboard")
    async def slash_dashboard(self, interaction: Interaction):
        """Slash command to open the main dashboard."""
        try:
            await interaction.response.defer()
            
            # Import views here to avoid circular imports
            from discord_bot.views import MainDashboardView
            
            view = MainDashboardView(self.engine)
            embed = self._create_dashboard_embed()
            
            await interaction.followup.send(embed=embed, view=view)
            logger.info("Dashboard opened via Discord slash command")
        except Exception as e:
            logger.error(f"Error in slash_dashboard: {e}", exc_info=True)
            await interaction.followup.send(
                embed=self._error_embed(f"Failed to open dashboard: {str(e)}")
            )

    # ─── Embed Creation Methods ───

    def _create_status_embed(self, status: dict) -> discord.Embed:
        """Create a status embed."""
        embed = discord.Embed(
            title="🔍 AlphaScan Status",
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
            name="Total Keys Found",
            value=str(status.get("total_keys_found", 0)),
            inline=True,
        )
        embed.add_field(
            name="Total Scans",
            value=str(status.get("total_scans", 0)),
            inline=True,
        )
        embed.add_field(
            name="Enabled Scanners",
            value=", ".join(status.get("enabled_scanners", [])) or "None",
            inline=False,
        )
        embed.add_field(
            name="Autonomous Mode",
            value="✅ Enabled" if status.get("autonomous_mode") else "❌ Disabled",
            inline=True,
        )

        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _create_dashboard_embed(self) -> discord.Embed:
        """Create the main dashboard embed."""
        embed = discord.Embed(
            title="📊 AlphaScan Dashboard",
            description="Interactive dashboard for system control and monitoring",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name="🟢 Start Scan",
            value="Trigger an immediate scan cycle",
            inline=False,
        )
        embed.add_field(
            name="📊 Scan Status",
            value="View current engine status and metrics",
            inline=False,
        )
        embed.add_field(
            name="🔑 Review Keys",
            value="View and manage discovered keys",
            inline=False,
        )
        embed.add_field(
            name="🌐 Verify Endpoints",
            value="Check health of all configured endpoints",
            inline=False,
        )
        embed.add_field(
            name="📈 Metrics",
            value="View system metrics and improvements",
            inline=False,
        )
        embed.add_field(
            name="⚙️ Settings",
            value="Configure system settings",
            inline=False,
        )
        embed.add_field(
            name="📄 Logs",
            value="View recent system logs",
            inline=False,
        )

        embed.set_footer(text="AlphaScan v0.5 | Select an option below")
        return embed

    def _success_embed(self, title: str, description: str) -> discord.Embed:
        """Create a success embed."""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _error_embed(self, message: str) -> discord.Embed:
        """Create an error embed."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _warning_embed(self, title: str, message: str) -> discord.Embed:
        """Create a warning embed."""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=message,
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="AlphaScan v0.5")
        return embed

    def _info_embed(self, title: str, message: str) -> discord.Embed:
        """Create an info embed."""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=message,
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="AlphaScan v0.5")
        return embed


async def setup(bot: commands.Bot, engine=None):
    """Setup the bot cog."""
    await bot.add_cog(AlphaScanBot(bot, engine))
    logger.info("AlphaScan bot cog setup complete")
