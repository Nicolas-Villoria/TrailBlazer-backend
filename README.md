# TrailBlazer Backend

TrailBlazer is a geospatial routing application designed to help users discover historical monuments in Catalunya while enjoying scenic hiking routes. The project facilitates the calculation of circular paths that prioritize visits to points of interest, bridging the gap between historical heritage and outdoor activities.

## Project Essence

The core of TrailBlazer lies in its ability to transform raw geospatial data into actionable hiking plans. By integrating historical monument data with modern routing engines, the application provides a specialized service for "cultural hiking."

### Key Features

* **Monument-Centric Routing:** Unlike standard navigation, our algorithm calculates circular routes that specifically target historical monuments from our database as waypoints.
* **Geospatial Intelligence:** We account for trail tortuosity (winding nature of paths) by applying a buffer factor to theoretical distances, ensuring the resulting routes match user expectations.
* **Elevation Analysis:** Every generated route includes a detailed elevation profile, allowing users to assess the difficulty of the hike before starting.
* **Multi-Format Export:** Routes can be downloaded as GPX or KML files for use with standard GPS devices and mapping applications.

## Technical Architecture

The backend is built with efficiency and modularity in mind, focusing on reliable data processing and external API integration.

### Core Components

* **FastAPI:** A high-performance web framework used for the REST API, enabling asynchronous task handling and automatic documentation.
* **Postgres with PostGIS:** Our primary database for monument storage. The use of PostGIS allows for native spatial queries, such as finding monuments within a specific radius of a route.
* **GraphHopper API:** We utilize the GraphHopper routing engine to calculate paths. This provides access to up-to-date OpenStreetMap trail data without the overhead of maintaining a local graph.
* **Asynchronous Job Management:** Route calculations are processed as background jobs, allowing the system to remain responsive while complex paths are being generated.

### Data Processing Pipeline

1. **Start Point Selection:** The user selects a location and a target distance.
2. **Triangulation Waypoints:** The system calculates theoretical waypoints to form a loop, applying a tortuosity buffer to account for the actual length of trails.
3. **Monument Matching:** Theoretical coordinates are refined by searching the PostGIS database for the nearest historical monuments.
4. **Route Generation:** GraphHopper calculates the most efficient walkable path through these targeted points.
5. **Geometry Processing:** The resulting path is processed to include elevation data and exported for visualization.

## Frontend Integration

While this repository focuses on the backend service, TrailBlazer includes a dedicated frontend application. The frontend provides an interactive map interface for selecting start points, visualizing routes, and displaying elevation charts in real-time. It communicates with this API via asynchronous polling to track route calculation progress.

## Implementation Details for Developers

### Setup Environment

Install the necessary dependencies using pip:

```bash
pip install -r requirements.txt
```

### Database Initialization

Ensure you have a Postgres instance with the PostGIS extension enabled. Configure your connection details in a `.env` file based on the provided `.env.example`.

### Running the Server

Start the FastAPI application using the following command:

```bash
python backend/app.py
```

The API will be available at `http://localhost:8000`, with interactive documentation at `/docs`.

## Future Work

The current state of the project serves as a solid foundation for specialized routing. Future iterations could focus on expanding the monument dataset through automated scraping of broader Catalan heritage records and implementing a more robust caching layer for frequent geographic queries.
