"""
Error and exception models for consistent API error responses
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ErrorDetail(BaseModel):
    """Individual error detail"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response format"""
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    status_code: int


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "validation_error"
    message: str
    validation_errors: List[ErrorDetail]
    invalid_fields: List[str]


class NotFoundResponse(BaseModel):
    """Not found error response"""
    error: str = "not_found"
    message: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class ServerErrorResponse(BaseModel):
    """Internal server error response"""
    error: str = "internal_server_error"
    message: str = "An unexpected error occurred"
    request_id: Optional[str] = None
    timestamp: Optional[str] = None