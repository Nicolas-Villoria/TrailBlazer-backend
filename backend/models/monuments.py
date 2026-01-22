"""
Monument-related Pydantic models
"""
from pydantic import BaseModel
from typing import List, Optional
from .common import PointModel


class MonumentModel(BaseModel):
    """Basic monument model"""
    name: str
    location: PointModel


class MonumentResponse(BaseModel):
    """Monument response for API endpoints"""
    name: str
    location: PointModel


class MonumentListResponse(BaseModel):
    """Response containing a list of monuments"""
    monuments: List[MonumentResponse]
    count: int


class MonumentTypeResponse(BaseModel):
    """Monument type information"""
    id: str
    name: str
    description: str
    icon: str


class MonumentTypesResponse(BaseModel):
    """Response containing available monument types"""
    types: List[MonumentTypeResponse]


class MonumentStatsResponse(BaseModel):
    """Monument statistics response"""
    total_monuments: int
    by_type: dict
    database_ready: bool
    error: Optional[str] = None


class MonumentSearchRequest(BaseModel):
    """Search request for monuments"""
    query: str
    limit: Optional[int] = 100
    monument_type: Optional[str] = None


class MonumentAreaRequest(BaseModel):
    """Request for monuments in a specific area"""
    monument_type: Optional[str] = None
    bottom_left_lat: float
    bottom_left_lon: float
    top_right_lat: float
    top_right_lon: float
    limit: Optional[int] = 1000


class MonumentNearPointRequest(BaseModel):
    """Request for monuments near a point"""
    point: PointModel
    radius_km: float
    monument_type: Optional[str] = None
    limit: Optional[int] = 100