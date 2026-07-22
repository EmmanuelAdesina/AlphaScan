"""
API dependencies for APIS.
Provides shared dependencies like the engine instance.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from core.engine import ApisEngine

# Global engine instance (singleton)
_engine: Optional[ApisEngine] = None


def get_engine() -> ApisEngine:
    """
    Get the global APIS engine instance.
    Creates one if it doesn't exist.
    """
    global _engine
    if _engine is None:
        _engine = ApisEngine()
    return _engine


def set_engine(engine: ApisEngine) -> None:
    """Set the global engine instance (for testing or external control)."""
    global _engine
    _engine = engine


def get_engine_or_404() -> ApisEngine:
    """Get the engine or raise 404 if not initialized."""
    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Engine not initialized",
        )
    return engine
