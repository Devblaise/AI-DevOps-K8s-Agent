"""Minimal Loguru configuration.

Kept intentionally simple this phase. Never log secret values.
"""

import sys

from loguru import logger


def configure_logging() -> None:
    """Reset Loguru to a single, readable stderr sink."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        ),
    )
