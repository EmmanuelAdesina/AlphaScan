"""
API dependencies for AlphaScan v0.5.
Provides shared dependencies like the engine instance.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from core.engine import AlphaScanEngine

# Global engine instance (singleton)
_engine: Optional[AlphaScanEngine] = None


def get_engine() -> AlphaScanEngine:
    """
    Get the global AlphaScan engine instance.
    Creates one if it doesn't exist.
    """
    global _engine
    if _engine is None:
        _engine = AlphaScanEngine()
    return _engine


def set_engine(engine: AlphaScanEngine) -> None:
    """Set the global engine instance (for testing or external control)."""
    global _engine
    _engine = engine


def get_engine_or_404() -> AlphaScanEngine:
    """Get the engine or raise 404 if not initialized."""
    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Engine not initialized",
        )
    return engine
