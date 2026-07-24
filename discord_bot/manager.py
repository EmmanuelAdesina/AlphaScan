"""
AlphaScan Discord Bot Manager
Handles bot setup, intents, event handlers, and lifecycle management.
"""
import logging
import asyncio
from typing import Optional
from datetime import datetime

import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)


class AlphaScanBotManager:
    """Manager for the AlphaScan Discord bot."""

    def __init__(self, token: str, engine=None):
        self.token = token
        self.engine = engine
        self.bot = None
        self._setup_bot()

    def _setup_bot(self):
        """Set up the Discord bot with proper intents and settings."""
        try:
            # Set up intents
            intents = discord.Intents.default()
            intents.message_content = True  # For reading message content
            intents.guilds = True
            intents.guild_messages = True
            intents.direct_messages = True

            # Create bot instance
            self.bot = commands.Bot(
                command_prefix="!",
                intents=intents,
                description="AlphaScan v0.5 - Secret Intelligence System",
            )

            # Register event handlers
            self._register_events()

            logger.info("Discord bot configured successfully")
        except Exception as e:
            logger.error(f"Error setting up bot: {e}", exc_info=True)
            raise

    def _register_events(self):
        """Register bot event handlers."""
        if not self.bot:
            return

        @self.bot.event
        async def on_ready():
            """Called when the bot is ready."""
            try:
                logger.info(f"Bot logged in as {self.bot.user}")
                logger.info(f"Bot is in {len(self.bot.guilds)} guild(s)")

                # Sync slash commands
                try:
                    synced = await self.bot.tree.sync()
                    logger.info(f"Synced {len(synced)} slash command(s)")
                except Exception as e:
                    logger.error(f"Error syncing slash commands: {e}", exc_info=True)

                # Set status
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name="for API keys | /dashboard for controls"
                )
                await self.bot.change_presence(activity=activity)
                logger.info("Bot presence updated")
            except Exception as e:
                logger.error(f"Error in on_ready: {e}", exc_info=True)

        @self.bot.event
        async def on_message(message):
            """Handle incoming messages."""
            try:
                if message.author == self.bot.user:
                    return

                logger.debug(
                    f"Message from {message.author}: {message.content[:50]}..."
                )

                # Process commands
                await self.bot.process_commands(message)
            except Exception as e:
                logger.error(f"Error in on_message: {e}", exc_info=True)

        @self.bot.event
        async def on_command_error(ctx, error):
            """Handle command errors."""
            logger.error(f"Command error: {error}", exc_info=True)

            try:
                embed = discord.Embed(
                    title="❌ Command Error",
                    description=f"An error occurred: {str(error)}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow(),
                )
                embed.set_footer(text="AlphaScan v0.5")

                await ctx.send(embed=embed, ephemeral=True)
            except Exception as e:
                logger.error(f"Error sending error message: {e}", exc_info=True)

        @self.bot.event
        async def on_interaction_check(interaction):
            """Validate all interactions."""
            try:
                # Add any permission checks here
                return True
            except Exception as e:
                logger.error(f"Error in interaction check: {e}", exc_info=True)
                return False

        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """Handle uncaught errors."""
            logger.error(f"Uncaught error in {event}", exc_info=True)

    async def load_cogs(self):
        """Load bot cogs (extensions)."""
        try:
            from discord_bot.bot import setup

            await setup(self.bot, self.engine)
            logger.info("Cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cogs: {e}", exc_info=True)
            raise

    async def start(self):
        """Start the bot."""
        try:
            if not self.bot:
                logger.error("Bot not initialized")
                return

            logger.info("Starting Discord bot...")

            # Load cogs before starting
            await self.load_cogs()

            # Start the bot
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the bot gracefully."""
        try:
            if self.bot:
                logger.info("Stopping Discord bot...")
                await self.bot.close()
                logger.info("Discord bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)

    def run(self):
        """Run the bot synchronously."""
        try:
            if not self.bot:
                logger.error("Bot not initialized")
                return

            self.bot.run(self.token)
        except Exception as e:
            logger.error(f"Error running bot: {e}", exc_info=True)
            raise

    async def send_message(
        self,
        guild_id: int,
        channel_id: int,
        embed: discord.Embed = None,
        content: str = None,
        view=None,
    ) -> Optional[discord.Message]:
        """Send a message to a specific channel."""
        try:
            if not self.bot or not self.bot.user:
                logger.error("Bot not ready")
                return None

            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return None

            channel = guild.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return None

            message = await channel.send(
                content=content,
                embed=embed,
                view=view,
            )
            logger.info(f"Message sent to {guild.name}#{channel.name}")
            return message
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            return None

    async def send_webhook_message(
        self,
        webhook_url: str,
        content: str = None,
        embed: discord.Embed = None,
    ) -> bool:
        """Send a message via webhook."""
        try:
            import aiohttp

            payload = {}
            if content:
                payload["content"] = content
            if embed:
                payload["embeds"] = [embed.to_dict()]

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status >= 400:
                        logger.error(f"Webhook error: HTTP {resp.status}")
                        return False
                    logger.info("Webhook message sent successfully")
                    return True
        except Exception as e:
            logger.error(f"Error sending webhook message: {e}", exc_info=True)
            return False


def create_bot_manager(token: str, engine=None) -> AlphaScanBotManager:
    """Factory function to create a bot manager."""
    try:
        manager = AlphaScanBotManager(token, engine)
        logger.info("Bot manager created successfully")
        return manager
    except Exception as e:
        logger.error(f"Error creating bot manager: {e}", exc_info=True)
        raise
