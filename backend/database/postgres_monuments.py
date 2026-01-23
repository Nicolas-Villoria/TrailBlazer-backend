import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import os
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class PostgresMonumentStorage:
    """PostgreSQL storage for monuments with PostGIS support"""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.user = os.getenv("DB_USER", "trailblazer")
        self.password = os.getenv("DB_PASSWORD", "password")
        self.dbname = os.getenv("DB_NAME", "trailblazer_db")
        self._local = threading.local()

    def _get_connection(self):
        if not hasattr(self._local, 'connection'):
            self._local.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.dbname,
                cursor_factory=RealDictCursor
            )
        return self._local.connection

    @contextmanager
    def _get_cursor(self):
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

    def get_monuments_by_type(self, db_type: str, limit: int = 1000) -> List[Dict[str, Any]]:
        query = "SELECT name, ST_Y(location) as latitude, ST_X(location) as longitude FROM monuments WHERE monument_type = %s LIMIT %s"
        with self._get_cursor() as cursor:
            cursor.execute(query, (db_type, limit))
            return cursor.fetchall()

    def get_monuments_near_route(self, route_geojson: str, buffer_m: float = 100) -> List[Dict[str, Any]]:
        """
        Find monuments within buffer_m of the given route.
        Using 4326 (Degrees) so buffer_m needs to be converted or use ST_DWithin with geography.
        """
        # 100m is roughly 0.001 degrees at this latitude
        # For precision, we use geography cast if available, or ST_DWithin(geography, geography, distance_m)
        query = """
            SELECT name, monument_type, ST_Y(location) as latitude, ST_X(location) as longitude
            FROM monuments
            WHERE ST_DWithin(location::geography, ST_GeomFromGeoJSON(%s)::geography, %s)
        """
        with self._get_cursor() as cursor:
            cursor.execute(query, (route_geojson, buffer_m))
            return cursor.fetchall()

    def get_nearest_monument(self, lat: float, lon: float, max_dist_m: float = 500) -> Optional[Dict[str, Any]]:
        """Find the nearest monument within max_dist_m."""
        query = """
            SELECT name, monument_type, ST_Y(location) as latitude, ST_X(location) as longitude
            FROM monuments
            WHERE ST_DWithin(location::geography, ST_SetSRID(ST_Point(%s, %s), 4326)::geography, %s)
            ORDER BY location::geography <-> ST_SetSRID(ST_Point(%s, %s), 4326)::geography
            LIMIT 1
        """
        with self._get_cursor() as cursor:
            cursor.execute(query, (lon, lat, max_dist_m, lon, lat))
            return cursor.fetchone()

    def get_total_count(self) -> int:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM monuments")
            return cursor.fetchone()['count']

    def get_monument_types_stats(self) -> Dict[str, int]:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT monument_type, COUNT(*) as count FROM monuments GROUP BY monument_type")
            return {row['monument_type']: row['count'] for row in cursor.fetchall()}
