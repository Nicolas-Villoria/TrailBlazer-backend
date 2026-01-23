import requests
import os
import random
import math
from typing import Dict, Any, List, Optional
from core.utils import get_logger

logger = get_logger("graphhopper_service")

def calculate_point(start_lat, start_lon, distance, bearing_rad):
    # Simple approximation for lat/lon offset
    d_lat = (distance / 111000.0) * math.cos(bearing_rad)
    d_lon = (distance / (111000.0 * math.cos(math.radians(start_lat)))) * math.sin(bearing_rad)
    return start_lat + d_lat, start_lon + d_lon

class GraphHopperService:
    """Service for interacting with the GraphHopper Routing API"""
    
    BASE_URL = "https://graphhopper.com/api/1/route"
    
    def __init__(self, api_key: Optional[str] = None, pg_storage = None):
        self.api_key = api_key or os.getenv("GRAPHHOPPER_API_KEY")
        self.pg_storage = pg_storage
        if not self.api_key:
            logger.warning("GraphHopper API key not found in environment variables")

    def get_pseudo_circular_route(
        self, 
        lat: float, 
        lon: float, 
        distance_target: float, 
        profile: str = "foot",
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a circular route using the "Monument-Centric" logic:
        1. Apply tortuosity buffer ( trails are not straight).
        2. Generate theoretical waypoints A and B.
        3. Search for real monuments in the database to replace these waypoints.
        4. Request a standard route through [Start, Monument A, Monument B, Start].
        """
        
        # 1. APPLY TORTUOSITY BUFFER
        # trails wind and curve, so we shrink the theoretical perimeter.
        buffer_factor = 1.45 
        effective_dist = distance_target / buffer_factor
        leg_dist = effective_dist / 3.0

        # 2. GENERATE THEORETICAL TARGETS
        random.seed(seed)
        angle_rad = random.uniform(0, 2 * math.pi)
        
        # Theoretical Point A
        t_lat_a, t_lon_a = calculate_point(lat, lon, leg_dist, angle_rad)
        # Theoretical Point B (120 degrees apart)
        angle_b_rad = angle_rad + (2 * math.pi / 3.0)
        t_lat_b, t_lon_b = calculate_point(lat, lon, leg_dist, angle_b_rad)

        # 3. MONUMENT INTEGRATION
        # Replace theoretical points with real monuments if found nearby
        lat_a, lon_a, hint_a = self._find_nearest_monument_info(t_lat_a, t_lon_a)
        lat_b, lon_b, hint_b = self._find_nearest_monument_info(t_lat_b, t_lon_b)

        params = {
            "point": [
                f"{lat},{lon}", 
                f"{lat_a},{lon_a}", 
                f"{lat_b},{lon_b}", 
                f"{lat},{lon}"
            ],
            "type": "json",
            "locale": "en",
            "key": self.api_key,
            "profile": profile,
            "points_encoded": "false",
            "elevation": "true",
            "snap_radius": 1500, # Large radius to snap monuments to the nearest trail
        }
        
        if hint_a or hint_b:
            # point_hint must have same number of elements as point
            params["point_hint"] = ["", hint_a or "", hint_b or "", ""]
        
        logger.info(f"Target: {distance_target}m | Effective: {effective_dist:.0f}m")
        logger.info(f"Route via A({lat_a:.4f}, {lon_a:.4f}) and B({lat_b:.4f}, {lon_b:.4f})")
        
        response = requests.get(self.BASE_URL, params=params)
        data = response.json()
        
        if "paths" in data:
            actual_dist = data["paths"][0]["distance"]
            logger.info(f"Resulting route distance: {actual_dist:.0f}m")
            
        return data

    def _find_nearest_monument_info(self, lat: float, lon: float) -> tuple:
        """Helper to find nearest monument or return original point as fallback"""
        if self.pg_storage:
            mon = self.pg_storage.get_nearest_monument(lat, lon, max_dist_m=800)
            if mon:
                logger.info(f"Targeting monument: {mon['name']}")
                return mon["latitude"], mon["longitude"], mon["name"]
        return lat, lon, None
