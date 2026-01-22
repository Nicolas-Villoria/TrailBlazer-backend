"""
Common/Base models used across multiple domains
"""
from pydantic import BaseModel


class PointModel(BaseModel):
    """Geographic point with latitude and longitude"""
    lat: float
    lon: float


class BoxModel(BaseModel):
    """Geographic bounding box defined by two corners"""
    bottom_left: PointModel
    top_right: PointModel


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str


class ApiInfoResponse(BaseModel):
    """API information response"""
    message: str
    version: str
    status: str