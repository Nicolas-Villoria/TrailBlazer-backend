"""
Pagination and filtering models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, List

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for requests"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and limit"""
        return (self.page - 1) * self.limit


class SortParams(BaseModel):
    """Sorting parameters"""
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$")


class FilterParams(BaseModel):
    """Base filtering parameters"""
    search: Optional[str] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None


class PaginationMeta(BaseModel):
    """Pagination metadata for responses"""
    current_page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def create(cls, page: int, limit: int, total_items: int) -> 'PaginationMeta':
        """Create pagination metadata"""
        total_pages = (total_items + limit - 1) // limit  # Ceiling division
        return cls(
            current_page=page,
            per_page=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    data: List[T]
    meta: PaginationMeta


class MonumentFilters(FilterParams):
    """Monument-specific filters"""
    monument_type: Optional[str] = None
    region: Optional[str] = None
    town: Optional[str] = None
    min_latitude: Optional[float] = None
    max_latitude: Optional[float] = None
    min_longitude: Optional[float] = None
    max_longitude: Optional[float] = None