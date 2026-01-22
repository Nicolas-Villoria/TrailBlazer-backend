import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import simplekml
from segments import Box, Point
from monuments import Monuments, Monument
from haversine import haversine
import os


class Routes:
    "Create a class that stores all shortest paths to a Monument, make it a graph."
    graph: nx.Graph
    start: Point
    endpoints: Monuments

    def __init__(self, start, endpoints) -> None:
        self.graph = nx.Graph()
        self.start = start
        self.endpoints = endpoints

    def dist(self, end: Monument) -> float:
        return nx.shortest_path_length(
            self.graph, self.start, end.location, weight="length"
        )


def find_routes(graph: nx.Graph, start: Point, endpoints: Monuments) -> Routes:
    """Find the shortest route between the starting point and all the endpoints."""
    routes = Routes(start, endpoints)
    for end in endpoints:
        try:
            dist, path = nx.single_source_dijkstra(
                graph, start, end.location, weight="weight"
            )
            for i in range(len(path) - 1):
                w = haversine(
                    (path[i].lat, path[i].lon), (path[i + 1].lat, path[i + 1].lon)
                )
                routes.graph.add_edge(path[i], path[i + 1], weight=w)
        except nx.NetworkXNoPath:
            continue
    return routes


def export_PNG_routes(box: Box, routes: Routes, filename: str) -> None:
    """Export the graph to a PNG file using staticmaps."""
    # Use staticmaps to create a map with the graph
    map = StaticMap(550, 550)
    for node in (routes.graph).nodes:
        lat, lon = node.lat, node.lon
        map.add_marker(CircleMarker((lon, lat), "black", 5))
    for edge in (routes.graph).edges:
        lat1, lon1 = edge[0].lat, edge[0].lon
        lat2, lon2 = edge[1].lat, edge[1].lon
        map.add_line(Line(((lon1, lat1), (lon2, lat2)), "blue", 2))
    for end in routes.endpoints:
        lat, lon = end.location.lat, end.location.lon
        map.add_marker(CircleMarker((lon, lat), "red", 5))
    map.add_marker(CircleMarker((routes.start.lon, routes.start.lat), "yellow", 5))
    image = map.render()
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    os.makedirs(dir_name, exist_ok=True)
    os.chdir(dir_name)
    image.save(filename)
    os.chdir("..")


def export_KML_routes(box: Box, routes: Routes, filename: str) -> None:
    """Export the graph to a KML file."""
    kml = simplekml.Kml()
    kml.newpoint(name="Origin-Point", coords=[(routes.start.lon, routes.start.lat)])
    # Create list of points from the graph segments
    for edge in routes.graph.edges:
        lin = kml.newlinestring(
            name="Camí",
            description="Camí entre dos punts",
            coords=[(edge[0].lon, edge[0].lat), (edge[1].lon, edge[1].lat)],
        )
        lin.style.linestyle.color = "ff0000ff"
        lin.style.linestyle.width = 4
    for end in routes.endpoints:
        try:
            kml.newpoint(
                name=end.name,
                coords=[(end.location.lon, end.location.lat)],
                description=f"Distància: {routes.dist(end)} km.",
            )
        except nx.NetworkXNoPath:
            point = kml.newpoint(
                name=end.name,
                coords=[(end.location.lon, end.location.lat)],
                description="No hi ha camí possible.",
            )
            point.style.iconstyle.icon.href = (
                "https://maps.google.com/mapfiles/kml/pal3/icon33.png"
            )
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    os.makedirs(dir_name, exist_ok=True)
    os.chdir(dir_name)
    kml.save(filename)
    os.chdir("..")
