"""
Application configuration and constants
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Default Catalunya bounding box
class DefaultBox:
    BOTTOM_LEFT_LAT = 40.475518
    BOTTOM_LEFT_LON = 0.055361
    TOP_RIGHT_LAT = 42.903476
    TOP_RIGHT_LON = 3.494081

# Monument type mappings
MONUMENT_TYPE_MAPPING = {
    "militars": "edificacions-de-caracter-militar",
    "religiosos": "edificacions-de-caracter-religios", 
    "civils": "edificacions-de-caracter-civil"
}

# Monument type definitions
MONUMENT_TYPES = [
    {
        "id": "militars", 
        "name": "Military Buildings", 
        "description": "Castles, towers, fortifications",
        "icon": "🏰"
    },
    {
        "id": "religiosos", 
        "name": "Religious Buildings", 
        "description": "Churches, monasteries, chapels",
        "icon": "⛪"
    },
    {
        "id": "civils", 
        "name": "Civil Buildings", 
        "description": "Houses, palaces, civil architecture",
        "icon": "🏛️"
    }
]

# Database configuration
DATABASE_CONFIG = {
    "jobs_db_path": "jobs.db",
    "monuments_db_path": "monuments.db"  # For future use
}

# API configuration
API_CONFIG = {
    "title": "TrailBlazer API",
    "version": "1.0.0",
    "description": "API for finding routes to historical monuments in Catalunya"
}