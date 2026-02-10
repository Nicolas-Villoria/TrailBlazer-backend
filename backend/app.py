"""
Main FastAPI application - Clean and modular
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from core.config import API_CONFIG, STATIC_DIR, DATABASE_CONFIG
from core.utils import get_logger
from database.jobs import JobStorage
from routers import monuments, routes

import uvicorn
from datetime import datetime
from models import HealthResponse
from models import ApiInfoResponse
import os




# Initialize logger
logger = get_logger("main")

# Initialize FastAPI app
app = FastAPI(
    title=API_CONFIG["title"],
    version=API_CONFIG["version"], 
    description=API_CONFIG["description"]
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:5173",  # Vite dev
        "https://trailblazer-pnlusbnkv-nicolas-villorias-projects.vercel.app" # Current preview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize services
job_storage = JobStorage(DATABASE_CONFIG["jobs_db_path"])

# Include routers
app.include_router(monuments.router, tags=["monuments"])
app.include_router(routes.router, tags=["routes"])


@app.get("/")
async def root():
    """Root endpoint - API status"""
    return ApiInfoResponse(
        message="TrailBlazer API is running!",
        version=API_CONFIG["version"],
        status="healthy"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )

if __name__ == "__main__":
    logger.info("Starting TrailBlazer API server", extra={
        "host": "0.0.0.0",
        "port": 8000,
        "api_url": "http://localhost:8000",
        "docs_url": "http://localhost:8000/docs"
    })
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Set to True for development
    )