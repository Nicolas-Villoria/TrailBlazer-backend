"""
Segment service - handles trail segment operations
Port of skeleton/segments.py to web backend
Now uses Overpass API for 10-50x faster downloads!
"""
import requests
import gpxpy
from sklearn.cluster import MiniBatchKMeans  # Much faster than KMeans!
import staticmap
from haversine import haversine
import json
import os
from datetime import datetime
from typing import List, Tuple, Set
from pathlib import Path

from models import PointModel, BoxModel
from core.utils import get_logger
from core.config import STATIC_DIR
from services.overpass_service import OverpassService

logger = get_logger("segment_service")


class SegmentService:
    """Service for segment operations - now with Overpass API for fast downloads!"""
    
    def __init__(self, settings_path: str = "settings_file.json"):
        """Initialize segment service with settings"""
        self.settings_path = settings_path
        self.load_settings()
        self.overpass = OverpassService()  # NEW: Fast Overpass API service
    
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            # Try to load from backend directory
            backend_dir = Path(__file__).parent.parent
            settings_file = backend_dir / self.settings_path
            
            if not settings_file.exists():
                # Try skeleton directory
                settings_file = backend_dir.parent.parent / "skeleton" / self.settings_path
            
            if not settings_file.exists():
                # Use defaults
                logger.warning("Settings file not found, using defaults")
                self.time_delta = 300
                self.distance_delta = 0.1
                self.n_clusters = 500
                return
            
            with open(settings_file, "r") as f:
                data = json.load(f)
                self.time_delta = data.get("time_delta", 300)
                self.distance_delta = data.get("distance_delta", 0.1)
                self.n_clusters = data.get("n_clusters", 500)
                self.max_download_pages = data.get("max_download_pages", 50)  # NEW: limit downloads
                
            logger.info(f"Loaded settings: time_delta={self.time_delta}, "
                       f"distance_delta={self.distance_delta}, n_clusters={self.n_clusters}, "
                       f"max_download_pages={self.max_download_pages}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}", exc_info=True)
            # Use defaults
            self.time_delta = 300
            self.distance_delta = 0.1
            self.n_clusters = 500
            self.max_download_pages = 50  
    
    def _get_directory_name(self, box: BoxModel) -> str:
        """Get directory name for a bounding box"""
        return f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    
    def _download_points(self, box: BoxModel, filename: str, max_pages: int = 50) -> None:
        """
        Download GPS points in the bounding box from OpenStreetMap.
        
        Args:
            box: Bounding box
            filename: Output filename
            max_pages: Maximum number of pages to download (default 50 = ~50k points)
                      Set to None for unlimited (dangerous!)
        """
        box_str = f"{box.bottom_left.lon},{box.bottom_left.lat},{box.top_right.lon},{box.top_right.lat}"
        page = 0
        count = 0
        
        # Create directory in static files
        dir_name = self._get_directory_name(box)
        dir_path = Path(STATIC_DIR) / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / filename
        
        logger.info(f"📥 Downloading points for box {box_str} (max {max_pages} pages)")
        
        with open(file_path, "w") as file:
            while True:
                # Safety check: limit number of pages
                if max_pages and page >= max_pages:
                    logger.warning(f"⚠️  Reached max pages limit ({max_pages}). Downloaded {count} points so far.")
                    break
                
                url = f"https://api.openstreetmap.org/api/0.6/trackpoints?bbox={box_str}&page={page}"
                try:
                    logger.info(f"📥 Downloading page {page}... ({count} points so far)")
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    
                    gpx_content = response.content.decode("utf-8")
                    gpx = gpxpy.parse(gpx_content)
                    
                    if len(gpx.tracks) == 0:
                        logger.info(f"✅ No more tracks on page {page}. Download complete.")
                        break
                    
                    for t, track in enumerate(gpx.tracks):
                        for segment in track.segments:
                            if all(point.time is not None for point in segment.points):
                                segment.points.sort(key=lambda p: p.time)  # type: ignore
                                for p in segment.points:
                                    file.write(
                                        f"{p.latitude},{p.longitude},{p.time},{t},{page}\n"
                                    )
                                    count += 1
                    
                    # Log progress every 5 pages
                    if page % 5 == 0 and page > 0:
                        logger.info(f"📊 Progress: Page {page}, {count} points downloaded")
                    
                    page += 1
                    
                except requests.RequestException as e:
                    logger.error(f"❌ Error downloading page {page}: {e}")
                    break
        
        logger.info(f"✅ Download complete: {count} points in {page} pages → {file_path}")
        
        # Warn if we downloaded too many points
        if count > 500000:
            logger.warning(f"⚠️  Downloaded {count} points - this is a LOT! Consider using a smaller bounding box.")
    
    def _load_points_fast(self, box: BoxModel) -> List[Tuple[PointModel, PointModel]]:
        """
        Load trail segments using Overpass API (FAST!)
        
        This is 10-50x faster than the old _download_points + _load_points approach:
        - Single API request instead of 20+ pages
        - JSON parsing instead of GPX parsing
        - Binary cache instead of text files
        - Returns segments directly (no need for separate clustering)
        
        Returns:
            List of (start_point, end_point) tuples representing trail segments
        """
        logger.info(f"🚀 Loading segments with Overpass API (fast mode)")
        return self.overpass.download_trails(box)
    
    def _load_points(self, box: BoxModel, filename: str) -> List[Tuple[float, float, datetime, int, int]]:
        """Load points from file, downloading if necessary (OLD SLOW METHOD - deprecated)"""
        points = []
        dir_name = self._get_directory_name(box)
        file_path = Path(STATIC_DIR) / dir_name / filename
        
        if not file_path.exists():
            logger.info(f"Points file not found, downloading...")
            self._download_points(box, filename, max_pages=self.max_download_pages)  # Use setting!
        
        try:
            with open(file_path, "r") as file:
                for line in file:
                    lat, lon, time, track, page = line.strip().split(",")
                    t = datetime.strptime(time.split("+")[0], "%Y-%m-%d %H:%M:%S")
                    points.append((float(lat), float(lon), t, int(track), int(page)))
            
            logger.info(f"Loaded {len(points)} points from {file_path}")
            return points
            
        except Exception as e:
            logger.error(f"Error loading points: {e}", exc_info=True)
            return []
    
    def download_segments(self, box: BoxModel, filename: str = "segments.txt") -> int:
        """
        Download and process segments for a bounding box.
        Now uses Overpass API for 10-50x faster downloads!
        
        Returns:
            Number of segments created
        """
        logger.info(f"🚀 Processing segments for box {self._get_directory_name(box)} (FAST mode)")
        
        # Use Overpass API to get segments directly (FAST!)
        try:
            segments_raw = self._load_points_fast(box)
            
            if len(segments_raw) < 2:
                logger.warning("Not enough segments found in area")
                return 0
            
            logger.info(f" Got {len(segments_raw)} raw trail segments from Overpass API")
            
            # Convert to clustered segments for cleaner output
            # Extract all unique points
            all_points = []
            for start, end in segments_raw:
                all_points.append((start.lat, start.lon))
                all_points.append((end.lat, end.lon))
            
            # Remove duplicates
            unique_points = list(set(all_points))
            
            if len(unique_points) < 2:
                logger.warning("Not enough unique points")
                return 0
            
            # Adaptive clustering: skip for small datasets, use MiniBatchKMeans for large ones
            if len(unique_points) < 1000:
                # Small dataset: no clustering needed (fast!)
                logger.info(f"✅ Small dataset ({len(unique_points)} points), skipping clustering")
                point_to_cluster = {point: point for point in unique_points}
            else:
                # Large dataset: use MiniBatchKMeans (5-10x faster than regular KMeans)
                # Adaptive cluster count: fewer clusters for larger datasets
                adaptive_clusters = min(
                    self.n_clusters,
                    len(unique_points) // 10,  # 1 cluster per 10 points
                    2000  # Cap at 2000 clusters max
                )
                
                logger.info(f"⚡ Fast clustering: {len(unique_points)} points → {adaptive_clusters} clusters")
                
                # MiniBatchKMeans is much faster for large datasets
                kmeans = MiniBatchKMeans(
                    n_clusters=adaptive_clusters,
                    random_state=0,
                    batch_size=1000,  # Process in batches for speed
                    max_iter=100,  # Limit iterations
                    n_init=3  # Fewer initializations (faster)
                ).fit(unique_points)
                
                centers = kmeans.cluster_centers_
                
                # Create mapping from original points to cluster centers
                point_to_cluster = {}
                for point in unique_points:
                    cluster_idx = kmeans.predict([point])[0]
                    point_to_cluster[point] = tuple(centers[cluster_idx])
            
            # Map segments to cluster centers
            segments: Set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
            
            for start, end in segments_raw:
                p1 = (start.lat, start.lon)
                p2 = (end.lat, end.lon)
                
                c1 = point_to_cluster.get(p1, p1)
                c2 = point_to_cluster.get(p2, p2)
                
                # Skip if same cluster
                if c1 == c2:
                    continue
                
                # Add segment (ensure consistent ordering)
                if c1 < c2:
                    segments.add((c1, c2))
                else:
                    segments.add((c2, c1))
            
            logger.info(f"✅ Created {len(segments)} unique clustered segments")
            
        except Exception as e:
            logger.error(f"Error using Overpass API, falling back to old method: {e}")
            # Fallback to old slow method
            return self._download_segments_slow(box, filename)
        
        # Save segments to file
        dir_name = self._get_directory_name(box)
        dir_path = Path(STATIC_DIR) / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / filename
        
        with open(file_path, "w") as f:
            for (lat1, lon1), (lat2, lon2) in segments:
                f.write(f"{lat1},{lon1},{lat2},{lon2}\n")
        
        logger.info(f"Saved {len(segments)} segments to {file_path}")
        return len(segments)
    
    def _download_segments_slow(self, box: BoxModel, filename: str = "segments.txt") -> int:
        """
        OLD SLOW METHOD - Fallback when Overpass API fails
        Downloads points page-by-page from OSM (very slow!)
        """
        logger.warning("⚠️  Using slow download method (fallback)")
        
        # Load all points
        all_points = self._load_points(box, "pointinfo.txt")
        
        if len(all_points) < 2:
            logger.warning("Not enough points to create segments")
            return 0
        
        # Extract coordinates for clustering
        coords = [(lat, lon) for lat, lon, _, _, _ in all_points]
        
        # Adaptive clustering for old slow method
        if len(coords) < 1000:
            logger.info(f"✅ Small dataset ({len(coords)} points), skipping clustering")
            # No clustering - map each point to itself
            labels = list(range(len(coords)))
            centers = coords
        else:
            adaptive_clusters = min(
                self.n_clusters,
                len(coords) // 10,
                2000
            )
            
            logger.info(f"⚡ Fast clustering: {len(coords)} points → {adaptive_clusters} clusters")
            
            kmeans = MiniBatchKMeans(
                n_clusters=adaptive_clusters,
                random_state=0,
                batch_size=1000,
                max_iter=100,
                n_init=3
            ).fit(coords)
            
            centers = kmeans.cluster_centers_
            labels = kmeans.labels_
        
        # Find segments
        segments: Set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
        
        for i in range(1, len(all_points)):
            _, _, time1, track1, page1 = all_points[i - 1]
            _, _, time2, track2, page2 = all_points[i]
            lat1, lon1 = centers[labels[i - 1]]
            lat2, lon2 = centers[labels[i]]
            
            # Check if points form a valid segment
            if (
                abs(time2 - time1).total_seconds() < self.time_delta
                and haversine((lat1, lon1), (lat2, lon2)) < self.distance_delta
                and labels[i - 1] != labels[i]
                and track1 == track2
                and page1 == page2
            ):
                # Ensure consistent ordering
                if i + 1 < len(all_points) and labels[i + 1] < labels[i]:
                    segments.add(((lat1, lon1), (lat2, lon2)))
                else:
                    segments.add(((lat2, lon2), (lat1, lon1)))
        
        # Save segments to file
        dir_name = self._get_directory_name(box)
        dir_path = Path(STATIC_DIR) / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / filename
        
        with open(file_path, "w") as f:
            for (lat1, lon1), (lat2, lon2) in segments:
                f.write(f"{lat1},{lon1},{lat2},{lon2}\n")
        
        logger.info(f"Saved {len(segments)} segments to {file_path}")
        return len(segments)
    
    def load_segments(self, box: BoxModel, filename: str = "segments.txt") -> List[Tuple[PointModel, PointModel]]:
        """Load segments from file"""
        segments = []
        dir_name = self._get_directory_name(box)
        file_path = Path(STATIC_DIR) / dir_name / filename
        
        if not file_path.exists():
            logger.warning(f"Segments file not found: {file_path}")
            return []
        
        try:
            with open(file_path, "r") as f:
                for line in f:
                    lat1, lon1, lat2, lon2 = line.strip().split(",")
                    start = PointModel(lat=float(lat1), lon=float(lon1))
                    end = PointModel(lat=float(lat2), lon=float(lon2))
                    segments.append((start, end))
            
            logger.info(f"Loaded {len(segments)} segments from {file_path}")
            return segments
            
        except Exception as e:
            logger.error(f"Error loading segments: {e}", exc_info=True)
            return []
    
    def get_segments(self, box: BoxModel, filename: str = "segments.txt") -> List[Tuple[PointModel, PointModel]]:
        """
        Get segments for a bounding box, downloading if necessary.
        
        Args:
            box: Geographic bounding box
            filename: Name of segments file
            
        Returns:
            List of segment tuples (start_point, end_point)
        """
        # Check if segments file exists
        dir_name = self._get_directory_name(box)
        file_path = Path(STATIC_DIR) / dir_name / filename
        
        if not file_path.exists():
            logger.info("Segments file not found, downloading and processing...")
            self.download_segments(box, filename)
        
        return self.load_segments(box, filename)
    
    def create_segment_preview_image(
        self, 
        segments: List[Tuple[PointModel, PointModel]], 
        filename: str
    ) -> str:
        """
        Create a PNG preview image of segments.
        
        Args:
            segments: List of segment tuples
            filename: Output filename (will be saved in static directory)
            
        Returns:
            Path to saved image file
        """
        try:
            map_obj = staticmap.StaticMap(800, 800)
            
            for start, end in segments:
                map_obj.add_line(
                    staticmap.Line(
                        [
                            (start.lon, start.lat),
                            (end.lon, end.lat),
                        ],
                        "blue",
                        2,
                    )
                )
            
            image = map_obj.render()
            output_path = Path(STATIC_DIR) / filename
            image.save(str(output_path))
            
            logger.info(f"Created segment preview image: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating preview image: {e}", exc_info=True)
            raise
