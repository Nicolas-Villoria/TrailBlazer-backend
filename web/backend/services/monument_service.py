"""
Monument service - handles monument data operations
Uses database for efficient monument queries
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
from core.utils import get_logger
from database.monuments import MonumentStorage
from models import MonumentResponse, PointModel

logger = get_logger("monument_service")

# Monument type mapping for API compatibility
MONUMENT_TYPE_MAPPING = {
    "militars": "militar",
    "religiosos": "religiós", 
    "civils": "civil"
}

# Reverse mapping for response
REVERSE_TYPE_MAPPING = {v: k for k, v in MONUMENT_TYPE_MAPPING.items()}


class MonumentService:
    """Service for monument operations using database storage"""
    
    def __init__(self, db_path: str = "monuments.db"):
        self.storage = MonumentStorage(db_path)
        self._ensure_data_loaded()
    
    def _ensure_data_loaded(self):
        """Ensure monument data is loaded into database"""
        try:
            count = self.storage.get_total_count()
            if count == 0:
                logger.info("No monuments in database, loading from file...")
                monuments_file = Path(__file__).parent.parent.parent.parent / "monuments.dat"
                if monuments_file.exists():
                    loaded = self.storage.load_from_file(str(monuments_file))
                    logger.info(f"Loaded {loaded} monuments into database")
                else:
                    logger.warning(f"monuments.dat not found at {monuments_file}")
            else:
                logger.info(f"Database already contains {count} monuments")
        except Exception as e:
            logger.error(f"Error ensuring data loaded: {e}")
    
    def get_monument_types(self) -> List[Dict[str, Any]]:
        """Get available monument types with statistics"""
        try:
            stats = self.storage.get_monument_types_stats()
            return [
                {
                    "id": REVERSE_TYPE_MAPPING.get(db_type, db_type),
                    "name": db_type.title(),
                    "count": count,
                    "display_name": self._get_display_name(db_type)
                }
                for db_type, count in stats.items()
            ]
        except Exception as e:
            logger.error(f"Error getting monument types: {e}")
            return []
    
    def _get_display_name(self, monument_type: str) -> str:
        """Get display name for monument type"""
        display_names = {
            "militar": "Edificacions Militars",
            "religiós": "Edificacions Religioses", 
            "civil": "Edificacions Civils"
        }
        return display_names.get(monument_type, monument_type.title())
    
    def get_monuments_by_type(
        self,
        monument_type: str,
        limit: int = 1000
    ) -> List[MonumentResponse]:
        """Get monuments by type"""
        try:
            # Map API type to database type
            db_type = MONUMENT_TYPE_MAPPING.get(monument_type, monument_type)
            
            monuments_data = self.storage.get_monuments_by_type(db_type)
            
            return [
                MonumentResponse(
                    name=m["name"],
                    location=PointModel(
                        lat=m["latitude"],
                        lon=m["longitude"]
                    )
                )
                for m in monuments_data[:limit]
            ]
        except Exception as e:
            logger.error(f"Error getting monuments by type {monument_type}: {e}")
            return []
    
    def get_monuments_by_type_and_area(
        self,
        monument_type: str,
        bottom_left_lat: Optional[float] = None,
        bottom_left_lon: Optional[float] = None,
        top_right_lat: Optional[float] = None,
        top_right_lon: Optional[float] = None
    ) -> List[MonumentResponse]:
        """Get monuments by type and optionally filter by area using database"""
        try:
            # If no area specified, get all monuments of type
            if not all([bottom_left_lat, bottom_left_lon, top_right_lat, top_right_lon]):
                return self.get_monuments_by_type(monument_type)
            
            # Map API type to database type
            db_type = MONUMENT_TYPE_MAPPING.get(monument_type, monument_type)
            
            monuments_data = self.storage.get_monuments_in_area(
                db_type,
                bottom_left_lat,  # type: ignore
                bottom_left_lon,  # type: ignore
                top_right_lat,   # type: ignore
                top_right_lon    # type: ignore
            )
            
            return [
                MonumentResponse(
                    name=m["name"],
                    location=PointModel(
                        lat=m["latitude"],
                        lon=m["longitude"]
                    )
                )
                for m in monuments_data
            ]
            
        except Exception as e:
            logger.error(f"Error getting monuments by type and area: {e}")
            return []
    
    def get_monuments_near_point(
        self,
        point: PointModel,
        radius_km: float,
        monument_type: Optional[str] = None,
        limit: int = 100
    ) -> List[MonumentResponse]:
        """Get monuments within radius of a point"""
        try:
            # Map API type to database type if provided
            db_type = None
            if monument_type:
                db_type = MONUMENT_TYPE_MAPPING.get(monument_type, monument_type)
            
            monuments_data = self.storage.get_monuments_near_point(
                point.lat,
                point.lon,
                radius_km,
                db_type,
                limit
            )
            
            return [
                MonumentResponse(
                    name=m["name"],
                    location=PointModel(
                        lat=m["latitude"],
                        lon=m["longitude"]
                    )
                )
                for m in monuments_data
            ]
        except Exception as e:
            logger.error(f"Error getting monuments near point: {e}")
            return []
    
    def search_monuments(
        self,
        query: str,
        limit: int = 100
    ) -> List[MonumentResponse]:
        """Search monuments by name, town, or region"""
        try:
            monuments_data = self.storage.search_monuments(query, limit)
            
            return [
                MonumentResponse(
                    name=m["name"],
                    location=PointModel(
                        lat=m["latitude"],
                        lon=m["longitude"]
                    )
                )
                for m in monuments_data
            ]
        except Exception as e:
            logger.error(f"Error searching monuments: {e}")
            return []
    
    def get_monument_stats(self) -> Dict[str, Any]:
        """Get monument statistics"""
        try:
            total = self.storage.get_total_count()
            type_stats = self.storage.get_monument_types_stats()
            
            return {
                "total_monuments": total,
                "by_type": {
                    REVERSE_TYPE_MAPPING.get(db_type, db_type): count
                    for db_type, count in type_stats.items()
                },
                "database_ready": True
            }
        except Exception as e:
            logger.error(f"Error getting monument stats: {e}")
            return {
                "total_monuments": 0,
                "by_type": {},
                "database_ready": False,
                "error": str(e)
            }


# ARCHITECTURE NOTES:
# ===================
# This file contains the SERVICE/BUSINESS LOGIC layer
# 
# Responsibilities:
# - Business logic and rules
# - API type mapping ("militars" → "militar")
# - Data transformation (Dict → MonumentResponse models)
# - Error handling and logging
# - Input validation and sanitization
#
# What this layer does NOT do:
# - Direct database queries (handled by database/)
# - HTTP request handling (handled by routers/)
# - SQL operations (handled by database/)
#
# Database layer is in: database/monuments.py
# API endpoints are in: routers/monuments.py