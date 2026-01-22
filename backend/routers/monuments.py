"""
Monument router - handles monument-related endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

from models import MonumentListResponse, MonumentTypeResponse, MonumentTypesResponse
from services.monument_service import MonumentService
from core.utils import get_logger

logger = get_logger("monuments_router")
router = APIRouter()

# Initialize service
monument_service = MonumentService()


@router.get("/monument-types", response_model=MonumentTypesResponse)
async def get_monument_types():
    """Get available monument types"""
    try:
        types_data = monument_service.get_monument_types()
        types = [MonumentTypeResponse(**type_data) for type_data in types_data]
        return MonumentTypesResponse(types=types)
    except Exception as e:
        logger.error("Error getting monument types", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monuments", response_model=MonumentListResponse)
async def get_monuments(
    monument_type: str,
    bottom_left_lat: Optional[float] = None,
    bottom_left_lon: Optional[float] = None,
    top_right_lat: Optional[float] = None,
    top_right_lon: Optional[float] = None
):
    """Get monuments of a specific type in the given area"""
    try:
        monuments = monument_service.get_monuments_by_type_and_area(
            monument_type=monument_type,
            bottom_left_lat=bottom_left_lat,
            bottom_left_lon=bottom_left_lon,
            top_right_lat=top_right_lat,
            top_right_lon=top_right_lon
        )
        
        return MonumentListResponse(
            monuments=monuments,
            count=len(monuments)
        )
    
    except Exception as e:
        logger.error("Error getting monuments", extra={
            "monument_type": monument_type,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))