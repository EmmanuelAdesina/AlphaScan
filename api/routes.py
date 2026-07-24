"""
FastAPI routes for AlphaScan v0.5.
Defines all REST API endpoints for the system.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from api.dependencies import get_engine
from api.models import (
    ScanRequest, ScanResponse, StatusResponse, KeyInfo, KeyResponse,
    ScanResultInfo, ResultsResponse, ImprovementRequest, ImprovementResponse,
    MetricsResponse, ErrorResponse,
)
from config.settings import API_RATE_LIMIT, get_config_summary

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AlphaScan v0.5 - Secret Intelligence System",
    description="AI-driven system that scans the internet for exposed API keys, SSH keys, and crypto keys",
    version="0.5.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=[API_RATE_LIMIT])
app.state.limiter = limiter


async def _engine_runner(engine):
    logger.info("Starting scan engine...")
    try:
        await asyncio.to_thread(engine.run)
    except asyncio.CancelledError:
        logger.info("Engine background task cancelled")
        raise
    except Exception:
        logger.exception("Unhandled exception in engine background task")


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup initiated.")
    engine = get_engine()
    logger.info("Engine initialized.")
    task = asyncio.create_task(_engine_runner(engine))
    app.state.engine_task = task
    logger.info("Background scan task created.")
    logger.info("Application startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated.")
    engine = get_engine()
    engine.stop()
    task = getattr(app.state, "engine_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Engine background task cancelled during shutdown")
    logger.info("Engine stopped.")
    logger.info("Application shutdown complete.")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "detail": str(exc)},
    )


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Health check endpoint with detailed system status."""
    try:
        engine = get_engine()
        scanner_stats = engine.scanner_manager.get_scanner_stats()
        enabled_scanners = [s for s in scanner_stats if s.get("enabled", False)]
        disabled_scanners = [s for s in scanner_stats if not s.get("enabled", False)]

        return {
            "status": "healthy",
            "service": "AlphaScan",
            "version": "0.5.0",
            "running": engine.state.running,
            "scan_cycle": engine.state.cycle,
            "enabled_scanners": [s.get("name") for s in enabled_scanners],
            "disabled_scanners": [s.get("name") for s in disabled_scanners],
            "active_scanners": engine.scanner_manager.get_enabled_scanners(),
            "llm_provider": engine.parser.llm_manager.get_active_provider(),
            "internet_connectivity": "unknown",  # Could add a connectivity check here
            "git_status": engine.git_manager.get_status() if engine.git_manager.is_available() else {"available": False},
            "database_status": "connected" if engine.verifier else "disconnected",
            "config": get_config_summary(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "AlphaScan",
            "version": "0.5.0",
            "error": str(e),
        }


@app.get("/", tags=["health"])
@limiter.limit("10/minute")
async def root(request: Request):
    """Root endpoint with basic service info."""
    return {
        "service": "AlphaScan",
        "version": "0.5.0",
        "health": "ok",
        "endpoints": ["/health", "/config", "/status", "/scan", "/results", "/keys", "/improvement", "/metrics"],
    }


@app.get("/config", tags=["health"])
@limiter.limit("10/minute")
async def config_summary(request: Request):
    """Return a safe configuration summary."""
    try:
        return get_config_summary()
    except Exception as e:
        logger.error(f"Config summary failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/status", response_model=StatusResponse, tags=["engine"])
@limiter.limit("10/minute")
async def get_status(request: Request):
    """Return current engine status."""
    engine = get_engine()
    return engine.get_status()


@app.post("/scan", response_model=ScanResponse, tags=["engine"])
@limiter.limit("5/minute")
async def trigger_scan(request: Request, scan_request: ScanRequest):
    """Trigger an immediate scan cycle."""
    engine = get_engine()
    scan_id = f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    try:
        result = await asyncio.to_thread(engine.force_scan)
        return {
            "status": "success",
            "message": f"Scan triggered successfully. Cycle {result['cycle']} completed.",
            "scan_id": scan_id,
        }
    except Exception as e:
        logger.error(f"Scan trigger failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/results", response_model=ResultsResponse, tags=["engine"])
@limiter.limit("10/minute")
async def get_results(request: Request):
    """Get recent scan results."""
    engine = get_engine()
    results = engine.get_results()
    return {"total": len(results), "results": results}


@app.get("/keys", response_model=KeyResponse, tags=["engine"])
@limiter.limit("10/minute")
async def get_keys(request: Request):
    """Get all discovered keys."""
    engine = get_engine()
    keys = engine.get_keys()
    return {"total": len(keys), "keys": keys}


@app.post("/improvement", response_model=ImprovementResponse, tags=["self-improvement"])
@limiter.limit("5/minute")
async def request_improvement(request: Request, improvement_request: ImprovementRequest):
    """Trigger a self-improvement cycle."""
    engine = get_engine()
    try:
        success, message = await asyncio.to_thread(engine.improver.trigger_improvement, improvement_request.description)
        return {
            "success": success,
            "message": message,
            "code_generated": None,
            "filename": None,
        }
    except Exception as e:
        logger.error(f"Improvement request failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/metrics", response_model=MetricsResponse, tags=["self-improvement"])
@limiter.limit("10/minute")
async def get_metrics(request: Request):
    """Get self-improvement metrics."""
    engine = get_engine()
    try:
        metrics = engine.improver.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Metrics request failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))