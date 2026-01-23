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
    CircularRouteRequest,
    JobStartResponse,
    JobResultResponse,
    PointModel
)
from services.route_service import RouteService
from services.monument_service import MonumentService
from services.graphhopper_service import GraphHopperService
from database.jobs import JobStorage
from database.postgres_monuments import PostgresMonumentStorage
from core.utils import get_logger
from core.config import STATIC_DIR, DATABASE_CONFIG

logger = get_logger("routes_router")
router = APIRouter()

# Initialize services
route_service = RouteService()
monument_service = MonumentService()
pg_storage = PostgresMonumentStorage()
gh_service = GraphHopperService(pg_storage=pg_storage)
job_storage = JobStorage(DATABASE_CONFIG["jobs_db_path"])


def process_circular_route(
    job_id: str,
    start_point: PointModel,
    distance_target: float,
    profile: str,
    seed: Optional[int]
):
    """Background task for circular route calculation via GraphHopper"""
    try:
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.2,
            "result": None,
            "error": None
        })
        
        # Step 1: Call GraphHopper
        logger.info(f"Job {job_id}: Requesting circular route from GraphHopper")
        gh_response = gh_service.get_pseudo_circular_route(
            lat=start_point.lat,
            lon=start_point.lon,
            distance_target=distance_target,
            profile=profile,
            seed=seed
        )
        
        job_storage.update_job({
            "job_id": job_id,
            "status": "processing",
            "progress": 0.6,
            "result": None,
            "error": None
        })
        
        # Extract geometry (assuming points_encoded=false)
        path = gh_response["paths"][0]
        coordinates = path["points"]["coordinates"] # [lon, lat]
        
        # Convert to GeoJSON LineString for PostGIS
        route_geojson = {
            "type": "LineString",
            "coordinates": coordinates
        }
        
        # Step 2: Find monuments along route
        import json
        logger.info(f"Job {job_id}: Finding monuments along route")
        # Increase buffer to 500m to catch monuments near the trail
        raw_monuments = pg_storage.get_monuments_near_route(json.dumps(route_geojson), buffer_m=500)
        
        # Format monuments to nested structure expected by frontend
        nearby_monuments = [
            {
                "name": m["name"],
                "type": m.get("monument_type", "civil"),
                "location": {
                    "lat": m["latitude"],
                    "lon": m["longitude"]
                }
            }
            for m in raw_monuments
        ]
        
        # Step 3: Export files
        logger.info(f"Job {job_id}: Exporting files")
        gpx_path = route_service.export_circular_gpx(coordinates, job_id)
        kml_path = route_service.export_circular_kml(coordinates, job_id)
        
        # Use 3D coordinates (lon, lat, elev) for both the map and elevation profile
        geometry = coordinates
        
        result = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates
                    },
                    "properties": {
                        "distance_m": path["distance"],
                        "time_ms": path["time"],
                        "ascent": path.get("ascend", 0),
                        "descent": path.get("descend", 0)
                    }
                }
            ],
            # Fields expected by the frontend RouteResult interface
            "geometry": geometry,  # Array of [lon, lat, elev]
            "distance_km": round(path["distance"] / 1000, 2),
            "elevation_gain": round(path.get("ascend", 0)),
            "duration_min": round(path["time"] / (1000 * 60)),
            "nearby_monuments": nearby_monuments,
            "gpx_url": f"/static/{Path(gpx_path).relative_to(STATIC_DIR)}",
            "kml_url": f"/static/{Path(kml_path).relative_to(STATIC_DIR)}",
            # Additional metadata
            "job_id": job_id,
            "time_ms": path["time"],
            "ascent": round(path.get("ascend", 0)),
            "descent": round(path.get("descend", 0))
        }
        
        job_storage.update_job({
            "job_id": job_id,
            "status": "completed",
            "progress": 1.0,
            "result": result,
            "error": None
        })
        
    except Exception as e:
        logger.error(f"Job {job_id}: Circular route failed: {e}", exc_info=True)
        job_storage.update_job({
            "job_id": job_id,
            "status": "failed",
            "progress": 0.0,
            "result": None,
            "error": str(e)
        })

@router.post("/routes/circular", response_model=JobStartResponse)
async def calculate_circular_route(
    request: CircularRouteRequest,
    background_tasks: BackgroundTasks
):
    """Start circular route calculation"""
    job_id = str(uuid.uuid4())
    job_storage.create_job({
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "result": None,
        "error": None
    })
    
    background_tasks.add_task(
        process_circular_route,
        job_id=job_id,
        start_point=request.start_point,
        distance_target=request.distance_target,
        profile=request.profile,
        seed=request.seed
    )
    
    return JobStartResponse(
        job_id=job_id,
        status="pending",
        message="Circular route calculation started."
    )


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
