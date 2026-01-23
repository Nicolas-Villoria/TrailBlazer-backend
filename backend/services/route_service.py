"""
Route service - handles route export formats
"""
import gpxpy
import gpxpy.gpx
import simplekml
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.utils import get_logger
from core.config import STATIC_DIR

logger = get_logger("route_service")


class RouteService:
    """Service for circular route export"""
    
    def __init__(self):
        pass
    
    def export_circular_gpx(self, coordinates: List[List[float]], job_id: str) -> str:
        """Export circular route to GPX file"""
        gpx = gpxpy.gpx.GPX()
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        
        for pt in coordinates:
            lon, lat = pt[0], pt[1]
            ele = pt[2] if len(pt) > 2 else None
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=ele))
            
        dir_path = Path(STATIC_DIR) / f"circular_{job_id}"
        dir_path.mkdir(parents=True, exist_ok=True)
        output_path = dir_path / f"route_{job_id}.gpx"
        
        with open(output_path, "w") as f:
            f.write(gpx.to_xml())
            
        return str(output_path)

    def export_circular_kml(self, coordinates: List[List[float]], job_id: str) -> str:
        """Export circular route to KML file"""
        kml = simplekml.Kml()
        # simplekml uses (longitude, latitude)
        lin = kml.newlinestring(name=f"Circular Route {job_id}", coords=coordinates)
        lin.style.linestyle.color = "ff00ff00"  # Green
        lin.style.linestyle.width = 4
        
        dir_path = Path(STATIC_DIR) / f"circular_{job_id}"
        dir_path.mkdir(parents=True, exist_ok=True)
        output_path = dir_path / f"route_{job_id}.kml"
        kml.save(str(output_path))
        
        return str(output_path)
