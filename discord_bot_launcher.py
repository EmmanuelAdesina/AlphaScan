#!/usr/bin/env python3
"""
AlphaScan v0.5 - Discord Bot Launcher
Starts the Discord bot as a standalone service.
"""
import asyncio
import logging
import sys
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DEBUG, LOG_LEVEL, DISCORD_BOT_TOKEN
from discord_bot import create_bot_manager


def setup_logging():
    """Configure structured logging."""
    try:
        import colorlog

        handler = colorlog.StreamHandler()
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        root_logger.addHandler(handler)

        # Suppress noisy loggers
        logging.getLogger("discord").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
    except ImportError:
        # Fallback if colorlog not available
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL, logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


async def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting AlphaScan Discord Bot v0.5...")

    # Validate token
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not set in environment variables")
        sys.exit(1)

    try:
        # Try to import and initialize the engine (optional)
        engine = None
        try:
            from core.engine import AlphaScanEngine

            logger.info("Initializing AlphaScan engine...")
            engine = AlphaScanEngine()
            logger.info("Engine initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize engine: {e}")
            logger.info("Bot will run in limited mode without engine integration")

        # Create bot manager
        logger.info("Creating Discord bot manager...")
        bot_manager = create_bot_manager(DISCORD_BOT_TOKEN, engine)

        # Start the bot
        logger.info("Starting Discord bot...")
        await bot_manager.start()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
