import networkx as nx
from segments import Segments
from math import *
import haversine

def make_graph(segments: Segments) -> nx.Graph:
    """Make a graph from the segments."""
    graph = nx.Graph()
    for segment in segments:
        graph.add_edge(
            segment.start,
            segment.end,
            wheight=haversine.haversine(
                (segment.start.lat, segment.start.lon),
                (segment.end.lat, segment.end.lon),
            ),
        )
    return graph


def simplify_graph(graph: nx.Graph, epsilon: float) -> nx.Graph:
    """Simplify the graph."""
    # We eliminate nodes that are too close to a straight line if they have degree 2
    nodes_degree_2 = [node for node in graph.nodes if graph.degree(node) == 2]
    for node in nodes_degree_2:
        g1, g3 = graph.adj[node]
        if abs(180 - _angle_of(g1, node, g3)) < epsilon:
            graph.remove_edge(g1, node)
            graph.remove_edge(node, g3)
            graph.remove_node(node)
            graph.add_edge(g1, g3)
    return graph


def _angle_of(p1, p2, p3) -> float:
    """Calculate the angle between three points using haversine."""
    lat1, lon1 = p1.lat, p1.lon
    lat2, lon2 = p2.lat, p2.lon
    lat3, lon3 = p3.lat, p3.lon
    d1 = haversine.haversine((lat1, lon1), (lat2, lon2))
    d2 = haversine.haversine((lat2, lon2), (lat3, lon3))
    d3 = haversine.haversine((lat1, lon1), (lat3, lon3))
    return degrees(acos((d1**2 + d2**2 - d3**2) / (2 * d1 * d2)))
