"""
Configuration and settings models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str
    username: str
    password: str
    
    @property
    def connection_url(self) -> str:
        """Generate database connection URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class APIConfig(BaseModel):
    """API configuration settings"""
    title: str = "TrailBlazer API"
    version: str = "1.0.0"
    description: str = "API for monument route planning"
    debug: bool = False
    cors_origins: List[str] = ["*"]
    max_request_size: int = 10 * 1024 * 1024  # 10MB


class RouteCalculationSettings(BaseModel):
    """Settings for route calculation algorithms"""
    max_distance_km: float = Field(default=100.0, ge=1.0, le=1000.0)
    max_monuments: int = Field(default=50, ge=1, le=100)
    default_optimization: str = Field(default="shortest", pattern="^(shortest|most_monuments|balanced)$")
    algorithm_timeout_seconds: int = Field(default=300, ge=30, le=3600)


class CacheConfig(BaseModel):
    """Cache configuration"""
    redis_url: Optional[str] = None
    default_ttl_seconds: int = 3600
    monument_cache_ttl: int = 86400  # 24 hours
    route_cache_ttl: int = 1800      # 30 minutes


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size_mb: int = 100
    backup_count: int = 5


class AppSettings(BaseModel):
    """Complete application settings"""
    api: APIConfig = APIConfig()
    database: Optional[DatabaseConfig] = None
    route_calculation: RouteCalculationSettings = RouteCalculationSettings()
    cache: CacheConfig = CacheConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # File paths
    monuments_data_path: str = "monuments.dat"
    static_files_path: str = "static"
    
    # Feature flags
    enable_caching: bool = True
    enable_background_jobs: bool = True
    enable_metrics: bool = False