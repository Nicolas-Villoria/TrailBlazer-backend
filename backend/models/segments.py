"""
Segment-related models for route segments and previews
"""
from pydantic import BaseModel
from typing import List, Optional
from .common import PointModel


class SegmentResponse(BaseModel):
    """Individual route segment"""
    start: PointModel
    end: PointModel
    distance_km: Optional[float] = None
    duration_minutes: Optional[float] = None


class SegmentPreviewResponse(BaseModel):
    """Preview of route segments"""
    segments: List[SegmentResponse]
    total_count: int
    preview_count: int


class SegmentRequest(BaseModel):
    """Request for segments in an area"""
    bottom_left: PointModel
    top_right: PointModel
    limit: Optional[int] = 100


class SegmentListResponse(BaseModel):
    """Response containing list of segments"""
    segments: List[SegmentResponse]
    total_segments: int
    area_covered_km2: Optional[float] = None