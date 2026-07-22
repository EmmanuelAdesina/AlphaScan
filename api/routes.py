"""
FastAPI routes for APIS.
Defines all REST API endpoints for the system.
"""
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
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
    title="APIS - Autonomous Parallel Intelligence Scanner",
    description="AI-driven system that scans the internet for exposed API keys",
    version="0.1.0",
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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "detail": str(exc)},
    )


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
@limiter.limit("10/minute")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "APIS", "version": "0.1.0"}


# ── Status Endpoints ──────────────────────────────────────────────────────

@app.get("/status", response_model=StatusResponse, tags=["status"])
@limiter.limit(API_RATE_LIMIT)
async def get_status(engine=Depends(get_engine)):
    """Get current engine status."""
    status = engine.get_status()
    return StatusResponse(**status)


@app.get("/config", tags=["status"])
@limiter.limit("10/minute")
async def get_config():
    """Get current configuration (safe summary)."""
    return get_config_summary()


# ── Scan Endpoints ────────────────────────────────────────────────────────

@app.post("/scan/start", response_model=ScanResponse, tags=["scan"])
@limiter.limit("5/minute")
async def start_scan(request: ScanRequest, engine=Depends(get_engine)):
    """Start a scan (force immediate scan)."""
    if engine.state.running:
        return ScanResponse(
            status="already_running",
            message="Scan is already running in the background",
        )

    try:
        result = engine.force_scan()
        return ScanResponse(
            status="completed",
            message=f"Scan completed. Found {result['keys_found']} keys.",
            scan_id=f"scan_{result['cycle']}",
        )
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/scan/stop", response_model=ScanResponse, tags=["scan"])
@limiter.limit("10/minute")
async def stop_scan(engine=Depends(get_engine)):
    """Stop the running scan cycle."""
    if not engine.state.running:
        return ScanResponse(
            status="not_running",
            message="No scan is currently running",
        )

    engine.stop()
    return ScanResponse(
        status="stopped",
        message="Scan cycle stopped",
    )


@app.get("/scan/start", response_model=ScanResponse, tags=["scan"])
@limiter.limit("5/minute")
async def start_scan_get(engine=Depends(get_engine)):
    """Start a scan (GET method, same as POST)."""
    return await start_scan(ScanRequest(), engine)


# ── Results Endpoints ─────────────────────────────────────────────────────

@app.get("/results", response_model=ResultsResponse, tags=["results"])
@limiter.limit(API_RATE_LIMIT)
async def get_results(engine=Depends(get_engine)):
    """Get scan results."""
    results = engine.get_results()
    return ResultsResponse(
        total=len(results),
        results=[ScanResultInfo(**r) for r in results],
    )


# ── Keys Endpoints ────────────────────────────────────────────────────────

@app.get("/keys", response_model=KeyResponse, tags=["keys"])
@limiter.limit(API_RATE_LIMIT)
async def get_keys(engine=Depends(get_engine)):
    """Get all discovered keys (masked for security)."""
    keys = engine.get_keys()
    return KeyResponse(
        total=len(keys),
        keys=[KeyInfo(**k) for k in keys],
    )


@app.get("/keys/{key_type}", response_model=KeyResponse, tags=["keys"])
@limiter.limit(API_RATE_LIMIT)
async def get_keys_by_type(key_type: str, engine=Depends(get_engine)):
    """Get keys filtered by type."""
    keys = engine.get_keys()
    filtered = [k for k in keys if k.get("type") == key_type]
    return KeyResponse(
        total=len(filtered),
        keys=[KeyInfo(**k) for k in filtered],
    )


# ── Self-Improvement Endpoints ────────────────────────────────────────────

@app.post("/self-improve", response_model=ImprovementResponse, tags=["self-improvement"])
@limiter.limit("10/minute")
async def trigger_self_improvement(
    request: ImprovementRequest,
    engine=Depends(get_engine),
):
    """Trigger a self-improvement cycle."""
    try:
        success, message = engine.improver.trigger_improvement(request.description)
        return ImprovementResponse(
            success=success,
            message=message,
            code_generated=request.description,
            filename=message,
        )
    except Exception as e:
        logger.error(f"Self-improvement failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.get("/self-improve/metrics", response_model=MetricsResponse, tags=["self-improvement"])
@limiter.limit("10/minute")
async def get_improvement_metrics(engine=Depends(get_engine)):
    """Get self-improvement metrics."""
    metrics = engine.improver.get_metrics()
    return MetricsResponse(**metrics)


# ── Scanner Endpoints ─────────────────────────────────────────────────────

@app.get("/scanners", tags=["scanners"])
@limiter.limit("10/minute")
async def get_scanners(engine=Depends(get_engine)):
    """Get list of all scanners and their status."""
    return engine.scanner_manager.get_scanner_stats()


# ── Discord Command Endpoints ──────────────────────────────────────────────

@app.post("/discord/command", tags=["discord"])
@limiter.limit("10/minute")
async def discord_command(command: str, engine=Depends(get_engine)):
    """
    Process Discord commands.
    Commands: !status, !scan, !improve, !config
    """
    command = command.strip().lower()

    if command == "!status":
        return {"response": engine.get_status()}
    elif command == "!scan":
        result = engine.force_scan()
        return {"response": f"Scan completed: {result['keys_found']} keys found"}
    elif command.startswith("!improve"):
        desc = command.replace("!improve", "").strip()
        if desc:
            success, msg = engine.improver.trigger_improvement(desc)
            return {"response": f"Improvement: {msg}"}
        return {"response": "Usage: !improve <description>"}
    elif command == "!config":
        return {"response": get_config_summary()}
    else:
        return {"response": "Unknown command. Available: !status, !scan, !improve, !config"}
