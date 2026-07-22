"""
FastAPI routes for AlphaScan v0.5.
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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "detail": str(exc)},
    )


# ── Health Check ──────────────────────────────────────────────────────────

from fastapi import Request

@app.get("/health", tags=["health"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AlphaScan",
        "version": "0.5.0"
    }

# ── Status Endpoints ──────────────────────────────────────────────────────

@app.get("/status", response_model=StatusResponse, tags=["status"])
@limiter.limit(API_RATE_LIMIT)
async def get_status(request: Request, engine=Depends(get_engine)):
    """Get current engine status."""
    status = engine.get_status()
    return StatusResponse(**status)


@app.get("/config", tags=["status"])
@limiter.limit("10/minute")
async def get_config(request: Request):
    """Get current configuration (safe summary)."""
    return get_config_summary()


# ── Scan Endpoints ────────────────────────────────────────────────────────

@app.post("/scan/start", response_model=ScanResponse, tags=["scan"])
@limiter.limit("5/minute")
async def start_scan(request: Request, scan_request: ScanRequest, engine=Depends(get_engine)):
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
async def stop_scan(request: Request, engine=Depends(get_engine)):
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
async def start_scan_get(request: Request, engine=Depends(get_engine)):
    """Start a scan (GET method, same as POST)."""
    return await start_scan(request, ScanRequest(), engine)


# ── Results Endpoints ─────────────────────────────────────────────────────

@app.get("/results", response_model=ResultsResponse, tags=["results"])
@limiter.limit(API_RATE_LIMIT)
async def get_results(request: Request, engine=Depends(get_engine)):
    """Get scan results."""
    results = engine.get_results()
    return ResultsResponse(
        total=len(results),
        results=[ScanResultInfo(**r) for r in results],
    )


# ── Keys Endpoints ────────────────────────────────────────────────────────

@app.get("/keys", response_model=KeyResponse, tags=["keys"])
@limiter.limit(API_RATE_LIMIT)
async def get_keys(request: Request, engine=Depends(get_engine)):
    """Get all discovered keys (masked for security)."""
    keys = engine.get_keys()
    return KeyResponse(
        total=len(keys),
        keys=[KeyInfo(**k) for k in keys],
    )


@app.get("/keys/{key_type}", response_model=KeyResponse, tags=["keys"])
@limiter.limit(API_RATE_LIMIT)
async def get_keys_by_type(request: Request, key_type: str, engine=Depends(get_engine)):
    """Get keys filtered by type."""
    keys = engine.get_keys()
    filtered = [k for k in keys if k.get("type") == key_type]
    return KeyResponse(
        total=len(filtered),
        keys=[KeyInfo(**k) for k in filtered],
    )


@app.get("/keys/rank/{rank}", response_model=KeyResponse, tags=["keys"])
@limiter.limit(API_RATE_LIMIT)
async def get_keys_by_rank(request: Request, rank: int, engine=Depends(get_engine)):
    """Get keys filtered by rank (0-10)."""
    keys = engine.get_keys()
    filtered = [k for k in keys if k.get("rank") == rank]
    return KeyResponse(
        total=len(filtered),
        keys=[KeyInfo(**k) for k in filtered],
    )


# ── Verification Endpoints ──────────────────────────────────────────────────

@app.get("/verification/stats", tags=["verification"])
@limiter.limit("10/minute")
async def get_verification_stats(request: Request, engine=Depends(get_engine)):
    """Get verification statistics."""
    return engine.verifier.get_stats()


# ── Self-Improvement Endpoints ────────────────────────────────────────────

@app.post("/self-improve", response_model=ImprovementResponse, tags=["self-improvement"])
@limiter.limit("10/minute")
async def trigger_self_improvement(
    request: Request,
    improvement_request: ImprovementRequest,
    engine=Depends(get_engine),
):
    """Trigger a self-improvement cycle."""
    try:
        success, message = engine.improver.trigger_improvement(improvement_request.description)
        return ImprovementResponse(
            success=success,
            message=message,
            code_generated=improvement_request.description,
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
async def get_improvement_metrics(request: Request, engine=Depends(get_engine)):
    """Get self-improvement metrics."""
    metrics = engine.improver.get_metrics()
    return MetricsResponse(**metrics)


# ── Scanner Endpoints ─────────────────────────────────────────────────────

@app.get("/scanners", tags=["scanners"])
@limiter.limit("10/minute")
async def get_scanners(request: Request, engine=Depends(get_engine)):
    """Get list of all scanners and their status."""
    return engine.scanner_manager.get_scanner_stats()


# ── Autonomous Endpoints ──────────────────────────────────────────────────

@app.get("/autonomous/status", tags=["autonomous"])
@limiter.limit("10/minute")
async def get_autonomous_status(request: Request, engine=Depends(get_engine)):
    """Get autonomous system status."""
    return {
        "autonomous_mode": engine.state.running,
        "autonomous_decisions": engine.state.autonomous_decisions,
        "current_strategy": engine.strategy_analyzer.get_current_strategy(),
        "git_available": engine.git_manager.is_available(),
        "pending_approvals": len(engine.decision_logger.get_pending_approvals()),
        "missing_keys": engine.env_manager.detect_key_needs(),
    }


@app.get("/autonomous/decisions", tags=["autonomous"])
@limiter.limit("10/minute")
async def get_decisions(request: Request, engine=Depends(get_engine)):
    """Get autonomous decision log."""
    return engine.decision_logger.get_decisions()


# ── Discord Command Endpoints ─────────────────────────────────────────────

@app.post("/discord/command", tags=["discord"])
@limiter.limit("10/minute")
async def discord_command(request: Request, command: str, engine=Depends(get_engine)):
    """
    Process Discord commands.
    Commands: !status, !approve-pivot, !deny-pivot, !approve-feature,
    !deny-feature, !config, !restart, !push, !rollback, !logs, !help,
    !provide-key, !improve, !scan
    """
    result = engine.process_command(command)
    return {"success": result["success"], "message": result["message"]}
