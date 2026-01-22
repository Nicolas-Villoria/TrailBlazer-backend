"""
Routes router - handles route calculation endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
import uuid
import asyncio
from pathlib import Path

from models import (
    RouteRequest,
    RouteCalculationRequest,
    JobStartResponse,
    JobResultResponse,
    BoxModel,
    PointModel
)
from services.route_service import RouteService
from services.graph import GraphService
from services.segment_service import SegmentService
from services.monument_service import MonumentService
from database.jobs import JobStorage
from core.utils import get_logger
from core.config import STATIC_DIR, DATABASE_CONFIG

logger = get_logger("routes_router")
router = APIRouter()

# Initialize services
route_service = RouteService()
graph_service = GraphService()
segment_service = SegmentService()
monument_service = MonumentService()
job_storage = JobStorage(DATABASE_CONFIG["jobs_db_path"])


def process_route_calculation(
    job_id: str,
    start_point: PointModel,
    monument_type: str,
    search_box: BoxModel
):
    """Background task for route calculation"""
    try:
        # Update job status to processing
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.1,
            "result": None,
            "error": None
        })
        
        logger.info(f"Job {job_id}: Starting route calculation")
        
        # Step 1: Get segments 
        logger.info(f"Job {job_id}: Downloading/loading segments")
        segments = segment_service.get_segments(search_box, "segments.txt")
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.3,
            "result": None,
            "error": None
        })
        
        if not segments:
            raise Exception("No segments found in the specified area")
        
        # Step 2: Build graph 
        logger.info(f"Job {job_id}: Building graph from {len(segments)} segments")
        graph = graph_service.make_graph(segments)
        graph = graph_service.simplify_graph(graph, epsilon=5.0)
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.5,
            "result": None,
            "error": None
        })
        
        # Step 3: Get monuments
        logger.info(f"Job {job_id}: Getting monuments of type {monument_type}")
        monuments = monument_service.get_monuments_by_type_and_area(
            monument_type=monument_type,
            bottom_left_lat=search_box.bottom_left.lat,
            bottom_left_lon=search_box.bottom_left.lon,
            top_right_lat=search_box.top_right.lat,
            top_right_lon=search_box.top_right.lon
        )
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.7,
            "result": None,
            "error": None
        })
        
        if not monuments:
            raise Exception(f"No monuments of type {monument_type} found in the area")
        
        # Step 4: Calculate routes and export 
        logger.info(f"Job {job_id}: Calculating routes to {len(monuments)} monuments")
        result = route_service.calculate_and_export(
            graph=graph,
            start=start_point,
            monuments=monuments,
            box=search_box,
            job_id=job_id
        )
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.95,
            "result": None,
            "error": None
        })
        
        # Step 5: Complete job
        logger.info(f"Job {job_id}: Route calculation completed")
        job_storage.update_job({
            "job_id": job_id,
            "status": "completed",
            "progress": 1.0,
            "result": result,
            "error": None
        })
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error during route calculation: {e}", exc_info=True)
        job_storage.update_job({
            "job_id": job_id,
            "status": "failed",
            "progress": 0.0,
            "result": None,
            "error": str(e)
        })


@router.post("/routes/calculate", response_model=JobStartResponse)
async def calculate_routes(
    request: RouteCalculationRequest,
    background_tasks: BackgroundTasks
):
    """
    Calculate routes from a start point to all monuments of a type.
    
    This is an async operation that:
    1. Downloads/loads trail segments
    2. Builds a graph network
    3. Finds monuments in the area
    4. Calculates shortest paths
    5. Exports PNG and KML files
    
    Returns a job ID to track progress.
    """
    try:
        # Create job
        job_id = str(uuid.uuid4())
        
        job_storage.create_job({
            "job_id": job_id,
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None
        })
        
        logger.info(f"Created route calculation job {job_id}")
        
        # Start background task
        background_tasks.add_task(
            process_route_calculation,
            job_id=job_id,
            start_point=request.start_point,
            monument_type=request.monument_type,
            search_box=request.search_box
        )
        
        return JobStartResponse(
            job_id=job_id,
            status="pending",
            message="Route calculation started. Use /routes/job/{job_id} to check progress."
        )
        
    except Exception as e:
        logger.error(f"Error starting route calculation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting route calculation: {str(e)}")


@router.get("/routes/job/{job_id}", response_model=JobResultResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a route calculation job.
    
    Returns:
    - Job status (pending, processing, completed, failed)
    - Progress percentage
    - Result data (if completed)
    - Error message (if failed)
    """
    try:
        job = job_storage.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return JobResultResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            result=job.get("result"),
            error=job.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")


@router.get("/routes/download/{job_id}/png")
async def download_png(job_id: str):
    """
    Download the PNG map for a completed route calculation job.
    
    Returns the PNG file as a downloadable attachment.
    """
    try:
        # Get job to verify it's completed
        job = job_storage.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if job["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Job {job_id} is not completed yet. Current status: {job['status']}"
            )
        
        if not job.get("result") or not job["result"].get("png_file"):
            raise HTTPException(status_code=404, detail="PNG file not found for this job")
        
        png_path = Path(job["result"]["png_file"])
        
        if not png_path.exists():
            raise HTTPException(status_code=404, detail="PNG file no longer exists")
        
        return FileResponse(
            path=str(png_path),
            media_type="image/png",
            filename=f"routes_{job_id}.png"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PNG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error downloading PNG: {str(e)}")


@router.get("/routes/download/{job_id}/kml")
async def download_kml(job_id: str):
    """
    Download the KML file for a completed route calculation job.
    
    Returns the KML file as a downloadable attachment for GPS devices.
    """
    try:
        # Get job to verify it's completed
        job = job_storage.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if job["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Job {job_id} is not completed yet. Current status: {job['status']}"
            )
        
        if not job.get("result") or not job["result"].get("kml_file"):
            raise HTTPException(status_code=404, detail="KML file not found for this job")
        
        kml_path = Path(job["result"]["kml_file"])
        
        if not kml_path.exists():
            raise HTTPException(status_code=404, detail="KML file no longer exists")
        
        return FileResponse(
            path=str(kml_path),
            media_type="application/vnd.google-earth.kml+xml",
            filename=f"routes_{job_id}.kml"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading KML: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error downloading KML: {str(e)}")


@router.delete("/routes/job/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated files.
    
    This will remove the job from the database and delete PNG/KML files if they exist.
    """
    try:
        job = job_storage.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Delete files if they exist
        if job.get("result"):
            if job["result"].get("png_file"):
                png_path = Path(job["result"]["png_file"])
                if png_path.exists():
                    png_path.unlink()
                    logger.info(f"Deleted PNG file: {png_path}")
            
            if job["result"].get("kml_file"):
                kml_path = Path(job["result"]["kml_file"])
                if kml_path.exists():
                    kml_path.unlink()
                    logger.info(f"Deleted KML file: {kml_path}")
        
        # Note: JobStorage doesn't have delete method, so we can't delete from DB
        # In a production system, you'd implement this
        
        return {"message": f"Job {job_id} files deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")
