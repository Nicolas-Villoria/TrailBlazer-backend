"""
Monument storage database layer - Production Ready
Efficiently stores and queries monuments from monuments.dat file
"""
import sqlite3
import threading
import re
import math
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Monument:
    """Monument data structure"""
    id: Optional[int]
    original_id: int
    name: str
    monument_type: str
    town: str
    region: str
    latitude: float
    longitude: float
    full_location: str


class MonumentStorage:
    """High-performance database storage for monuments"""
    
    def __init__(self, db_path: str = "monuments.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable spatial optimizations
            self._local.connection.execute("PRAGMA cache_size = -64000")  # 64MB cache
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Initialize the monuments database schema"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monuments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    monument_type TEXT NOT NULL,
                    town TEXT NOT NULL,
                    region TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    full_location TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create optimized indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monuments_type 
                ON monuments(monument_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monuments_location 
                ON monuments(latitude, longitude)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monuments_region 
                ON monuments(region)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monuments_town 
                ON monuments(town)
            """)
            
            # Composite index for spatial + type queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monuments_type_location 
                ON monuments(monument_type, latitude, longitude)
            """)
    
    def _parse_monument_line(self, line: str) -> Optional[Monument]:
        """Parse a single line from monuments.dat"""
        try:
            parts = line.strip().split(';')
            if len(parts) != 3:
                return None
            
            name_location, lat_str, lon_str = parts
            
            # Extract ID and name
            if '. ' not in name_location:
                return None
            
            id_part, name_part = name_location.split('. ', 1)
            original_id = int(id_part)
            
            # Parse name and location
            if ' - ' in name_part:
                name, location = name_part.rsplit(' - ', 1)
            elif ' / ' in name_part:
                name, location = name_part.rsplit(' / ', 1)
            else:
                name = name_part
                location = ""
            
            # Extract town and region
            town = ""
            region = ""
            if ' / ' in location:
                town_part, region = location.rsplit(' / ', 1)
                town = town_part
            else:
                region = location
            
            # Determine monument type
            monument_type = self._extract_monument_type(name)
            
            return Monument(
                id=None,
                original_id=original_id,
                name=name.strip(),
                monument_type=monument_type,
                town=town.strip(),
                region=region.strip(),
                latitude=float(lat_str),
                longitude=float(lon_str),
                full_location=location.strip()
            )
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing line: {line} - {e}")
            return None
    
    def _extract_monument_type(self, name: str) -> str:
        """Extract monument type from name"""
        # Common monument types in Catalan
        type_patterns = {
            'militar': [r'^Castell', r'^Torre', r'^Muralla', r'^Fortalesa'],
            'religiós': [r'^Església', r'^Capella', r'^Ermita', r'^Santuari', r'^Monestir', r'^Convent'],
            'civil': [r'^Casa', r'^Palau', r'^Pont', r'^Molí', r'^Hospital', r'^Universitat']
        }
        
        name_lower = name.lower()
        
        for monument_type, patterns in type_patterns.items():
            for pattern in patterns:
                if re.search(pattern.lower(), name_lower):
                    return monument_type
        
        return 'civil'  # Default type
    
    def load_from_file(self, file_path: str) -> int:
        """Load monuments from monuments.dat file into database"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Clear existing data
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM monuments")
        
        loaded_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            monuments_batch = []
            
            for line_num, line in enumerate(f, 1):
                monument = self._parse_monument_line(line)
                if monument:
                    monuments_batch.append((
                        monument.original_id,
                        monument.name,
                        monument.monument_type,
                        monument.town,
                        monument.region,
                        monument.latitude,
                        monument.longitude,
                        monument.full_location
                    ))
                    
                    # Batch insert for performance
                    if len(monuments_batch) >= 1000:
                        self._insert_monuments_batch(monuments_batch)
                        loaded_count += len(monuments_batch)
                        monuments_batch = []
                        print(f"Loaded {loaded_count} monuments...")
            
            # Insert remaining monuments
            if monuments_batch:
                self._insert_monuments_batch(monuments_batch)
                loaded_count += len(monuments_batch)
        
        print(f"Successfully loaded {loaded_count} monuments from {file_path}")
        return loaded_count
    
    def _insert_monuments_batch(self, monuments_batch: List[Tuple]):
        """Insert a batch of monuments efficiently"""
        with self._get_cursor() as cursor:
            cursor.executemany("""
                INSERT INTO monuments (
                    original_id, name, monument_type, town, region,
                    latitude, longitude, full_location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, monuments_batch)
    
    def get_monuments_by_type(self, monument_type: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all monuments of a specific type - DATABASE LAYER ONLY"""
        query = """
            SELECT * FROM monuments 
            WHERE monument_type = ?
            ORDER BY name
        """
        params: List[Any] = [monument_type]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            
        with self._get_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_monuments_in_area(
        self, 
        monument_type: Optional[str],
        bottom_left_lat: float,
        bottom_left_lon: float, 
        top_right_lat: float,
        top_right_lon: float,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get monuments in a specific geographic area"""
        query = """
            SELECT * FROM monuments 
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
        """
        params: List[Any] = [bottom_left_lat, top_right_lat, bottom_left_lon, top_right_lon]
        
        if monument_type:
            query += " AND monument_type = ?"
            params.append(monument_type)
        
        query += " ORDER BY name LIMIT ?"
        params.append(limit)
        
        with self._get_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_monuments_near_point(
        self, 
        lat: float, 
        lon: float, 
        radius_km: float,
        monument_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get monuments within radius of a point"""
        # Simple bounding box approximation (faster than haversine for small areas)
        lat_delta = radius_km / 111.32  # Rough km to degree conversion
        lon_delta = radius_km / (111.32 * math.cos(math.radians(lat)))
        
        return self.get_monuments_in_area(
            monument_type,
            lat - lat_delta,
            lon - lon_delta,
            lat + lat_delta,
            lon + lon_delta,
            limit
        )
    
    def search_monuments(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search monuments by name, town, or region"""
        search_pattern = f"%{query}%"
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM monuments 
                WHERE name LIKE ? OR town LIKE ? OR region LIKE ?
                ORDER BY name
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_monument_types_stats(self) -> Dict[str, int]:
        """Get statistics of monument types"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT monument_type, COUNT(*) as count
                FROM monuments
                GROUP BY monument_type
                ORDER BY count DESC
            """)
            
            return {row['monument_type']: row['count'] for row in cursor.fetchall()}
    
    def get_total_count(self) -> int:
        """Get total number of monuments"""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM monuments")
            return cursor.fetchone()['count']


# ARCHITECTURE NOTES:
# ===================
# This file contains ONLY the database storage layer (DATA ACCESS)
# 
# Responsibilities:
# - Raw SQL queries and database operations
# - Data persistence and retrieval
# - Database schema management
# - Returns raw Dict[str, Any] data
