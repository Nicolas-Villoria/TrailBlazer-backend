#!/usr/bin/env python3
"""
Database initialization script for TrailBlazer monuments
Run this to populate the database from monuments.dat
"""
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.monuments import MonumentStorage
from services.monument_service import MonumentService


def main():
    """Initialize the monuments database"""
    print("TrailBlazer Monument Database Initialization")
    print("=" * 50)
    
    # Path to monuments.dat file
    monuments_file = backend_dir.parent.parent / "monuments.dat"
    
    if not monuments_file.exists():
        print(f"Error: monuments.dat not found at {monuments_file}")
        print("   Please ensure the file is in the project root directory")
        return 1
    
    print(f"Found monuments.dat: {monuments_file}")
    
    try:
        # Initialize storage
        storage = MonumentStorage("monuments.db")
        print("Database initialized")
        
        # Load data from file
        print("Loading monuments from file...")
        count = storage.load_from_file(str(monuments_file))
        print(f"Successfully loaded {count} monuments")
        
        # Get statistics
        stats = storage.get_monument_types_stats()
        total = storage.get_total_count()
        
        print("\n Monument Statistics:")
        print(f"   Total monuments: {total}")
        for monument_type, count in stats.items():
            print(f"   {monument_type}: {count}")
        
        # Test the service
        print("\n Testing monument service...")
        service = MonumentService("monuments.db")
        
        types = service.get_monument_types()
        print(f"   Available types: {len(types)}")
        
        # Test getting monuments by type
        militar_monuments = service.get_monuments_by_type("militars", limit=5)
        print(f"   Sample militar monuments: {len(militar_monuments)}")
        
        if militar_monuments:
            print(f"   First monument: {militar_monuments[0].name}")
        
        print("\n Database initialization completed successfully!")
        print("   You can now start the API server with: python app.py")
        
        return 0
        
    except Exception as e:
        print(f" Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())