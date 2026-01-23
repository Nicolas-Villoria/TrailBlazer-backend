"""
Shared utilities for the application
"""
import os
import logging
import sys
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any

import numpy as np
from scipy.spatial import KDTree

# SKELETON_DIR and skeleton_working_directory removed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(f"trailblazer.{name}")


def find_closest_node_efficient(graph, target_point):
    """Find the closest node to a target point using spatial indexing (KDTree)"""
    if graph.number_of_nodes() == 0:
        return None, float('inf')
    
    # Extract coordinates from graph nodes
    nodes = list(graph.nodes)
    coordinates = np.array([(node.lat, node.lon) for node in nodes])
    
    # Build KDTree for efficient spatial queries
    tree = KDTree(coordinates)
    
    # Find closest node
    target_coords = np.array([target_point.lat, target_point.lon])
    distance, index = tree.query(target_coords)
    
    # Convert distance from coordinate units to km using approximate conversion
    distance_km = distance * 111.32  # Rough conversion: 1 degree ≈ 111.32 km
    
    return nodes[index], distance_km


def update_job_progress(
    job_storage, 
    job_id: str, 
    status: Optional[str] = None, 
    progress: Optional[float] = None, 
    result: Optional[Dict[str, Any]] = None, 
    error: Optional[str] = None
):
    """Helper function to update job status in persistent storage"""
    job = job_storage.get_job(job_id)
    if job:
        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = progress
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        job_storage.update_job(job)