"""
Segments router - handles trail segment endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from models import (
    BoxModel, 
    SegmentResponse, 
    SegmentListResponse, 
    SegmentRequest,
    SegmentPreviewResponse
)
from services.segment_service import SegmentService
from core.utils import get_logger

logger = get_logger("segments_router")
router = APIRouter()

# Initialize service
segment_service = SegmentService()


@router.post("/segments/download", response_model=SegmentListResponse)
async def download_segments(request: SegmentRequest):
    """
    Download and process trail segments for a geographic area.
    
    This endpoint:
    1. Downloads GPS track data from OpenStreetMap
    2. Performs K-means clustering on track points
    3. Creates trail segments between clustered points
    4. Caches results for future use
    
    Note: This can take several minutes for large areas.
    """
    try:
        from models import BoxModel
        
        box = BoxModel(
            bottom_left=request.bottom_left,
            top_right=request.top_right
        )
        
        logger.info(f"Downloading segments for box: {box}")
        
        # Download and process segments
        count = segment_service.download_segments(box, "segments.txt")
        
        # Load the segments
        segments = segment_service.load_segments(box, "segments.txt")
        
        # Convert to response format
        segment_responses = [
            SegmentResponse(
                start=start,
                end=end,
                distance_km=None  # Could calculate if needed
            )
            for start, end in segments
        ]
        
        return SegmentListResponse(
            segments=segment_responses[:request.limit] if request.limit else segment_responses,
            total_segments=len(segment_responses)
        )
        
    except Exception as e:
        logger.error(f"Error downloading segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error downloading segments: {str(e)}")


@router.get("/segments", response_model=SegmentListResponse)
async def get_segments(
    bottom_left_lat: float,
    bottom_left_lon: float,
    top_right_lat: float,
    top_right_lon: float,
    download_if_missing: bool = True
):
    """
    Get trail segments for a geographic area.
    
    Returns cached segments if available, optionally downloads if missing.
    
    Query Parameters:
    - bottom_left_lat, bottom_left_lon: Southwest corner of bounding box
    - top_right_lat, top_right_lon: Northeast corner of bounding box
    - download_if_missing: Whether to download if segments don't exist (default: true)
    """
    try:
        from models import PointModel
        
        box = BoxModel(
            bottom_left=PointModel(lat=bottom_left_lat, lon=bottom_left_lon),
            top_right=PointModel(lat=top_right_lat, lon=top_right_lon)
        )
        
        logger.info(f"Getting segments for box: {box}")
        
        # Get segments (downloads if missing and flag is set)
        if download_if_missing:
            segments = segment_service.get_segments(box, "segments.txt")
        else:
            segments = segment_service.load_segments(box, "segments.txt")
        
        if not segments:
            raise HTTPException(
                status_code=404, 
                detail="No segments found. Try with download_if_missing=true"
            )
        
        # Convert to response format
        segment_responses = [
            SegmentResponse(start=start, end=end, distance_km=None)
            for start, end in segments
        ]
        
        return SegmentListResponse(
            segments=segment_responses,
            total_segments=len(segment_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting segments: {str(e)}")


@router.post("/segments/preview", response_model=SegmentPreviewResponse)
async def preview_segments(request: SegmentRequest):
    """
    Generate a preview image of trail segments.
    
    Creates a PNG map showing all trail segments in the specified area.
    Useful for visualizing the trail network before route calculation.
    """
    try:
        from models import BoxModel
        
        box = BoxModel(
            bottom_left=request.bottom_left,
            top_right=request.top_right
        )
        
        logger.info(f"Generating segment preview for box: {box}")
        
        # Get segments
        segments = segment_service.get_segments(box, "segments.txt")
        
        if not segments:
            raise HTTPException(status_code=404, detail="No segments found in this area")
        
        # Convert to response format
        segment_responses = [
            SegmentResponse(start=start, end=end, distance_km=None)
            for start, end in segments
        ]
        
        return SegmentPreviewResponse(
            segments=segment_responses[:request.limit] if request.limit else segment_responses,
            total_count=len(segment_responses),
            preview_count=min(request.limit or len(segment_responses), len(segment_responses))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")


@router.get("/segments/stats")
async def get_segment_stats(
    bottom_left_lat: float,
    bottom_left_lon: float,
    top_right_lat: float,
    top_right_lon: float
):
    """
    Get statistics about segments in an area without downloading.
    
    Returns information about cached segment data if available.
    """
    try:
        from models import PointModel
        from pathlib import Path
        from core.config import STATIC_DIR
        
        box = BoxModel(
            bottom_left=PointModel(lat=bottom_left_lat, lon=bottom_left_lon),
            top_right=PointModel(lat=top_right_lat, lon=top_right_lon)
        )
        
        # Check if segments exist
        dir_name = segment_service._get_directory_name(box)
        segment_file = Path(STATIC_DIR) / dir_name / "segments.txt"
        points_file = Path(STATIC_DIR) / dir_name / "pointinfo.txt"
        
        stats = {
            "box": {
                "bottom_left": {"lat": bottom_left_lat, "lon": bottom_left_lon},
                "top_right": {"lat": top_right_lat, "lon": top_right_lon}
            },
            "segments_cached": segment_file.exists(),
            "points_cached": points_file.exists(),
            "segment_count": 0,
            "settings": {
                "time_delta": segment_service.time_delta,
                "distance_delta": segment_service.distance_delta,
                "n_clusters": segment_service.n_clusters
            }
        }
        
        if segment_file.exists():
            segments = segment_service.load_segments(box, "segments.txt")
            stats["segment_count"] = len(segments)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")
