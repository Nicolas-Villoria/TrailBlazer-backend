# TrailBlazer Models Architecture

## 📁 Directory Structure

```
models/
├── __init__.py                 # Central imports for all models
├── common.py                   # Base models (PointModel, BoxModel, etc.)
├── monuments.py                # Monument-specific models
├── routes.py                   # Route calculation models
├── segments.py                 # Route segment models
├── jobs.py                     # Background job models
├── errors.py                   # Error response models
├── pagination.py               # Pagination and filtering models
└── config.py                   # Configuration models
```

## 🎯 Benefits of This Structure

### ✅ **Prevents Circular Dependencies**
- Each model file has clear, minimal imports
- No cross-dependencies between router files
- Clean separation of concerns

### ✅ **Easy Imports**
```python
# Import specific models you need
from models import MonumentResponse, PointModel, ErrorResponse

# Or import everything (for development)
from models import *
```

### ✅ **Organized by Domain**
- **Common**: Shared models across domains
- **Monuments**: Monument-specific request/response models  
- **Routes**: Route calculation models
- **Jobs**: Background processing models
- **Errors**: Standardized error responses
- **Pagination**: Reusable pagination patterns

### ✅ **Type Safety**
- Full Pydantic validation on all models
- IDE autocompletion and type checking
- Clear API documentation generation

## 🚦 Usage Examples

### Router Usage
```python
from models import (
    MonumentResponse,
    MonumentListResponse,
    MonumentSearchRequest,
    ErrorResponse
)

@router.post("/search", response_model=MonumentListResponse)
async def search_monuments(request: MonumentSearchRequest):
    # Type-safe request handling
    pass
```

### Service Usage
```python
from models import MonumentResponse, PointModel

def get_monuments() -> List[MonumentResponse]:
    return [
        MonumentResponse(
            name="Castle",
            location=PointModel(lat=41.0, lon=2.0)
        )
    ]
```

### Database Usage
```python
# Database layer returns raw Dict[str, Any]
# Service layer transforms to MonumentResponse models
raw_data = db.get_monuments()
return [MonumentResponse(**item) for item in raw_data]
```

## 📊 Model Statistics

- **Total Models**: 36+ Pydantic models
- **Categories**: 8 domain categories
- **Zero Circular Dependencies**: ✅
- **Full Type Coverage**: ✅
- **FastAPI Compatible**: ✅

## 🔄 Migration from Old Structure

### Before (models.py)
```python
# Everything in one file - 67 lines
from models import MonumentResponse  # Single file import
```

### After (models/ directory)
```python
# Organized by domain - Multiple focused files
from models import MonumentResponse  # Same import, better structure
from models.monuments import MonumentSearchRequest  # Specific imports
```

This architecture provides a **scalable, maintainable foundation** for your API models that will grow cleanly with your application.