"""
Job processing and background task models
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class JobStatus(BaseModel):
    """Job status for background processing"""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobStartResponse(BaseModel):
    """Response when starting a new job"""
    job_id: str
    status: str
    message: Optional[str] = None


class JobListResponse(BaseModel):
    """Response containing list of jobs"""
    jobs: list[JobStatus]
    total_jobs: int
    active_jobs: int


class JobResultResponse(BaseModel):
    """Detailed job result response"""
    job_id: str
    status: str
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None