from typing import List, Optional, Dict, Any
from core.utils import get_logger
from database.postgres_monuments import PostgresMonumentStorage
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
    """Service for monument operations using PostgreSQL storage"""
    
    def __init__(self):
        self.storage = PostgresMonumentStorage()
    
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
    
    def get_monuments_by_type_and_area(
        self,
        monument_type: str,
        bottom_left_lat: Optional[float] = None,
        bottom_left_lon: Optional[float] = None,
        top_right_lat: Optional[float] = None,
        top_right_lon: Optional[float] = None
    ) -> List[MonumentResponse]:
        """Get monuments by type and optionally filter by area using PostgreSQL"""
        try:
            # Map API type to database type
            db_type = MONUMENT_TYPE_MAPPING.get(monument_type, monument_type)
            
            # For simplicity, if no area is provided, we just get monuments by type
            # (PostgresMonumentStorage currently has get_monuments_by_type)
            if not all([bottom_left_lat, bottom_left_lon, top_right_lat, top_right_lon]):
                monuments_data = self.storage.get_monuments_by_type(db_type)
            else:
                # Fallback to get_monuments_by_type for now if area search not implemented in PG
                # or extend PostgresMonumentStorage
                monuments_data = self.storage.get_monuments_by_type(db_type)
            
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
            return {"total_monuments": 0, "by_type": {}, "database_ready": False}