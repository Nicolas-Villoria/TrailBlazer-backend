import networkx as nx
import simplekml
from staticmap import StaticMap, CircleMarker, Line
from segments import Box
import os


def export_PNG(box: Box, graph: nx.Graph, filename: str) -> None:
    """Export the graph to a PNG file using staticmaps."""
    # Use staticmaps to create a map with the graph
    map = StaticMap(550, 550)
    for node in graph.nodes:
        lat, lon = node.lat, node.lon
        map.add_marker(CircleMarker((lon, lat), "black", 5))
    for edge in graph.edges:
        lat1, lon1 = edge[0].lat, edge[0].lon
        lat2, lon2 = edge[1].lat, edge[1].lon
        map.add_line(Line(((lon1, lat1), (lon2, lat2)), "blue", 2))
    image = map.render()
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    os.makedirs(dir_name, exist_ok=True)
    os.chdir(dir_name)
    image.save(filename)
    os.chdir("..")


def export_KML(box: Box, graph: nx.Graph, filename: str) -> None:
    """Export the graph to a KML file."""
    kml = simplekml.Kml()
    # Create list of points from the graph segments
    for edge in graph.edges:
        l = [(node.lon, node.lat) for node in edge]
        lin = kml.newlinestring(
            name="Camí",
            description="Camí entre dos punts",
            coords=l,
        )
        lin.style.linestyle.color = "ff0000ff"
        lin.style.linestyle.width = 4

    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    os.makedirs(dir_name, exist_ok=True)
    os.chdir(dir_name)
    kml.save(filename)
    os.chdir("..")
