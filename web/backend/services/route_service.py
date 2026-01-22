"""
Route service - handles route calculation and export
Port of skeleton/routes.py to web backend
"""
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import simplekml
from haversine import haversine
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from models import PointModel, BoxModel, MonumentResponse
from core.utils import get_logger
from core.config import STATIC_DIR
from services.graph import GraphService

logger = get_logger("route_service")


class RouteCalculationResult:
    """Result of route calculation"""
    
    def __init__(self, start: PointModel, monuments: List[MonumentResponse]):
        self.graph = nx.Graph()
        self.start = start
        self.monuments = monuments
        self.reachable_monuments: List[MonumentResponse] = []
        self.unreachable_monuments: List[MonumentResponse] = []
    
    def get_distance(self, monument: MonumentResponse) -> Optional[float]:
        """Get distance to a monument in km"""
        try:
            start_node = (self.start.lat, self.start.lon)
            end_node = (monument.location.lat, monument.location.lon)
            return nx.shortest_path_length(self.graph, start_node, end_node, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "start": {"lat": self.start.lat, "lon": self.start.lon},
            "total_monuments": len(self.monuments),
            "reachable_monuments": len(self.reachable_monuments),
            "unreachable_monuments": len(self.unreachable_monuments),
            "routes": [
                {
                    "monument": m.name,
                    "location": {"lat": m.location.lat, "lon": m.location.lon},
                    "distance_km": self.get_distance(m)
                }
                for m in self.reachable_monuments
            ],
            "unreachable": [
                {
                    "monument": m.name,
                    "location": {"lat": m.location.lat, "lon": m.location.lon}
                }
                for m in self.unreachable_monuments
            ]
        }


class RouteService:
    """Service for route calculation and export"""
    
    def __init__(self):
        self.graph_service = GraphService()
    
    def find_routes(
        self, 
        graph: nx.Graph, 
        start: PointModel, 
        monuments: List[MonumentResponse]
    ) -> RouteCalculationResult:
        """
        Find shortest routes from start point to all monuments.
        
        Args:
            graph: NetworkX graph of trail network
            start: Starting point
            monuments: List of monument destinations
            
        Returns:
            RouteCalculationResult with all routes
        """
        logger.info(f"Calculating routes from {start} to {len(monuments)} monuments")
        
        result = RouteCalculationResult(start, monuments)
        
        # Find closest graph node to start point
        try:
            start_node = self.graph_service.find_closest_node(graph, start)
        except Exception as e:
            logger.error(f"Could not find start node: {e}")
            result.unreachable_monuments = monuments.copy()
            return result
        
        # Calculate route to each monument
        for monument in monuments:
            try:
                # Find closest graph node to monument
                end_node = self.graph_service.find_closest_node(graph, monument.location)
                
                # Calculate shortest path
                distance, path = self.graph_service.shortest_path(graph, start_node, end_node)
                
                # Add path edges to result graph
                for i in range(len(path) - 1):
                    node1 = path[i]
                    node2 = path[i + 1]
                    weight = haversine(node1, node2)
                    result.graph.add_edge(node1, node2, weight=weight)
                
                result.reachable_monuments.append(monument)
                logger.debug(f"Route to {monument.name}: {distance:.2f} km")
                
            except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
                logger.warning(f"No path to monument {monument.name}: {e}")
                result.unreachable_monuments.append(monument)
            except Exception as e:
                logger.error(f"Error calculating route to {monument.name}: {e}", exc_info=True)
                result.unreachable_monuments.append(monument)
        
        logger.info(f"Routes calculated: {len(result.reachable_monuments)} reachable, "
                   f"{len(result.unreachable_monuments)} unreachable")
        
        return result
    
    def export_png_routes(
        self, 
        box: BoxModel, 
        result: RouteCalculationResult, 
        filename: str
    ) -> str:
        """
        Export routes to PNG image.
        
        Args:
            box: Bounding box for directory naming
            result: Route calculation result
            filename: Output filename
            
        Returns:
            Path to exported PNG file
        """
        logger.info(f"Exporting routes to PNG: {filename}")
        
        try:
            # Create static map
            map_obj = StaticMap(1200, 1200)
            
            # Add route edges
            for edge in result.graph.edges:
                node1, node2 = edge
                map_obj.add_line(
                    Line(
                        [(node1[1], node1[0]), (node2[1], node2[0])],
                        "blue",
                        3
                    )
                )
            
            # Add trail intersections
            for node in result.graph.nodes:
                map_obj.add_marker(CircleMarker((node[1], node[0]), "black", 4))
            
            # Add monuments (red for reachable, gray for unreachable)
            for monument in result.reachable_monuments:
                map_obj.add_marker(
                    CircleMarker((monument.location.lon, monument.location.lat), "red", 10)
                )
            
            for monument in result.unreachable_monuments:
                map_obj.add_marker(
                    CircleMarker((monument.location.lon, monument.location.lat), "gray", 8)
                )
            
            # Add start point (yellow)
            map_obj.add_marker(
                CircleMarker((result.start.lon, result.start.lat), "yellow", 12)
            )
            
            # Render and save
            image = map_obj.render()
            
            # Create directory
            dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
            dir_path = Path(STATIC_DIR) / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            output_path = dir_path / filename
            image.save(str(output_path))
            
            logger.info(f"PNG exported to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exporting PNG: {e}", exc_info=True)
            raise
    
    def export_kml_routes(
        self, 
        box: BoxModel, 
        result: RouteCalculationResult, 
        filename: str
    ) -> str:
        """
        Export routes to KML file for GPS devices.
        
        Args:
            box: Bounding box for directory naming
            result: Route calculation result
            filename: Output filename
            
        Returns:
            Path to exported KML file
        """
        logger.info(f"Exporting routes to KML: {filename}")
        
        try:
            kml = simplekml.Kml()
            
            # Add starting point
            kml.newpoint(
                name="Punt d'Origen",
                coords=[(result.start.lon, result.start.lat)]
            )
            
            # Add route lines
            for edge in result.graph.edges:
                node1, node2 = edge
                lin = kml.newlinestring(
                    name="Camí",
                    description="Camí entre dos punts",
                    coords=[(node1[1], node1[0]), (node2[1], node2[0])]
                )
                lin.style.linestyle.color = "ff0000ff"  # Red in KML (AABBGGRR)
                lin.style.linestyle.width = 4
            
            # Add reachable monuments with distances
            for monument in result.reachable_monuments:
                distance = result.get_distance(monument)
                distance_str = f"{distance:.2f}" if distance else "N/A"
                
                kml.newpoint(
                    name=monument.name,
                    coords=[(monument.location.lon, monument.location.lat)],
                    description=f"Distància: {distance_str} km"
                )
            
            # Add unreachable monuments with special icon
            for monument in result.unreachable_monuments:
                point = kml.newpoint(
                    name=monument.name,
                    coords=[(monument.location.lon, monument.location.lat)],
                    description="No hi ha camí possible."
                )
                point.style.iconstyle.icon.href = (
                    "https://maps.google.com/mapfiles/kml/pal3/icon33.png"
                )
            
            # Create directory
            dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
            dir_path = Path(STATIC_DIR) / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            output_path = dir_path / filename
            kml.save(str(output_path))
            
            logger.info(f"KML exported to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exporting KML: {e}", exc_info=True)
            raise
    
    def calculate_and_export(
        self,
        graph: nx.Graph,
        start: PointModel,
        monuments: List[MonumentResponse],
        box: BoxModel,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Calculate routes and export to PNG and KML.
        
        This is the main method for route processing jobs.
        
        Args:
            graph: Trail network graph
            start: Starting point
            monuments: List of monuments
            box: Bounding box
            job_id: Job identifier for filenames
            
        Returns:
            Dictionary with result data and file paths
        """
        logger.info(f"Starting route calculation job {job_id}")
        
        try:
            # Calculate routes
            result = self.find_routes(graph, start, monuments)
            
            # Export to PNG
            png_filename = f"routes_{job_id}.png"
            png_path = self.export_png_routes(box, result, png_filename)
            
            # Export to KML
            kml_filename = f"routes_{job_id}.kml"
            kml_path = self.export_kml_routes(box, result, kml_filename)
            
            # Prepare result
            result_data = result.to_dict()
            result_data["png_file"] = png_path
            result_data["kml_file"] = kml_path
            result_data["png_url"] = f"/static/{Path(png_path).relative_to(STATIC_DIR)}"
            result_data["kml_url"] = f"/static/{Path(kml_path).relative_to(STATIC_DIR)}"
            
            logger.info(f"Route calculation job {job_id} completed successfully")
            return result_data
            
        except Exception as e:
            logger.error(f"Error in route calculation job {job_id}: {e}", exc_info=True)
            raise
