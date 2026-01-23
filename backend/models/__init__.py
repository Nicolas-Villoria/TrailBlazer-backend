"""
Centralized model imports for easy access across the application
"""

# Common models
from .common import (
    PointModel,
    BoxModel,
    HealthResponse,
    ApiInfoResponse
)

# Monument models
from .monuments import (
    MonumentModel,
    MonumentResponse,
    MonumentListResponse,
    MonumentTypeResponse,
    MonumentTypesResponse,
    MonumentStatsResponse,
    MonumentSearchRequest,
    MonumentAreaRequest,
    MonumentNearPointRequest
)

# Route models
from .routes import (
    RouteRequest,
    RouteResponse,
    RouteCalculationRequest,
    CircularRouteRequest
)


# Job models
from .jobs import (
    JobStatus,
    JobStartResponse,
    JobListResponse,
    JobResultResponse
)

# Error models
from .errors import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorResponse,
    NotFoundResponse,
    ServerErrorResponse
)

# Pagination models
from .pagination import (
    PaginationParams,
    SortParams,
    FilterParams,
    PaginationMeta,
    PaginatedResponse,
    MonumentFilters
)

# Export all models for easy importing
__all__ = [
    # Common
    "PointModel",
    "BoxModel", 
    "HealthResponse",
    "ApiInfoResponse",
    
    # Monuments
    "MonumentModel",
    "MonumentResponse",
    "MonumentListResponse",
    "MonumentTypeResponse",
    "MonumentTypesResponse",
    "MonumentStatsResponse",
    "MonumentSearchRequest",
    "MonumentAreaRequest",
    "MonumentNearPointRequest",
    
    # Routes
    "RouteRequest",
    "RouteResponse",
    "RouteCalculationRequest",
    "CircularRouteRequest",
    
    # Segments
    "SegmentResponse",
    "SegmentPreviewResponse",
    "SegmentRequest",
    "SegmentListResponse",
    
    # Jobs
    "JobStatus",
    "JobStartResponse",
    "JobListResponse",
    "JobResultResponse",
    
    # Errors
    "ErrorDetail",
    "ErrorResponse",
    "ValidationErrorResponse",
    "NotFoundResponse",
    "ServerErrorResponse",
    
    # Pagination
    "PaginationParams",
    "SortParams",
    "FilterParams",
    "PaginationMeta",
    "PaginatedResponse",
    "MonumentFilters",
]