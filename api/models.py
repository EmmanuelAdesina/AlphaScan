"""
Pydantic models for APIS REST API.
Defines request and response schemas for all endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class ScanRequest(BaseModel):
    """Request to start a scan."""
    scanners: Optional[List[str]] = Field(
        default=None,
        description="List of scanner names to use. If empty, uses all enabled scanners."
    )
    parallel: bool = Field(
        default=True,
        description="Run scanners in parallel"
    )


class ScanResponse(BaseModel):
    """Response from starting a scan."""
    status: str
    message: str
    scan_id: Optional[str] = None


class StatusResponse(BaseModel):
    """Engine status response."""
    running: bool
    cycle: int
    total_keys_found: int
    total_scans: int
    last_scan_time: Optional[str] = None
    last_scan_duration: float
    last_error: Optional[str] = None
    discovered_key_types: List[str]
    scan_interval: int
    enabled_scanners: List[str]


class KeyInfo(BaseModel):
    """Information about a discovered key."""
    type: str
    value: str
    description: str
    masked_value: str
    source: Optional[str] = None
    timestamp: Optional[str] = None


class KeyResponse(BaseModel):
    """Response containing discovered keys."""
    total: int
    keys: List[KeyInfo]


class ScanResultInfo(BaseModel):
    """Information about a scan result."""
    cycle: int
    keys_found: int
    timestamp: Optional[str] = None
    scanner_stats: Optional[List[Dict]] = None


class ResultsResponse(BaseModel):
    """Response containing scan results."""
    total: int
    results: List[ScanResultInfo]


class ImprovementRequest(BaseModel):
    """Request to trigger self-improvement."""
    description: str = Field(
        ...,
        description="Natural language description of the improvement to make"
    )


class ImprovementResponse(BaseModel):
    """Response from a self-improvement request."""
    success: bool
    message: str
    code_generated: Optional[str] = None
    filename: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response containing self-improvement metrics."""
    metrics: Dict[str, Any]
    success_rate: float
    improvement_history: List[Dict]
    deployment_history: List[Dict]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
