"""
Route calculation related models
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .common import PointModel, BoxModel


class RouteRequest(BaseModel):
    """Request to calculate a route"""
    start_point: PointModel
    monument_type: str
    search_box: BoxModel
    settings: Optional[Dict[str, Any]] = None


class RouteResponse(BaseModel):
    """Response containing calculated route"""
    start_point: PointModel
    end_point: PointModel
    distance_km: float
    monuments_visited: int
    image_url: Optional[str] = None


class RouteCalculationRequest(BaseModel):
    """Extended route calculation request"""
    start_point: PointModel
    monument_type: str
    search_box: BoxModel
    max_distance_km: Optional[float] = None
    max_monuments: Optional[int] = None
    optimization_mode: Optional[str] = "shortest"  # "shortest", "most_monuments", "balanced"
    settings: Optional[Dict[str, Any]] = None


class CircularRouteRequest(BaseModel):
    """Request to calculate a circular route"""
    start_point: PointModel
    distance_target: float
    profile: str = "foot"
    seed: Optional[int] = None