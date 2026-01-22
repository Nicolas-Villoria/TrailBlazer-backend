"""
Graph service - handles graph creation and manipulation

Features:
- Graph construction from trail segments
- Graph simplification (collinear node removal)
- A* pathfinding with Haversine heuristic for optimal routing
"""
import networkx as nx
import heapq
from math import acos, degrees
from typing import List, Tuple, Dict, Set, Optional
import haversine

from models import PointModel
from core.utils import get_logger

logger = get_logger("graph_service")


# Type alias for graph nodes (lat, lon tuples)
Node = Tuple[float, float]


class GraphService:
    """Service for graph operations"""
    
    @staticmethod
    def make_graph(segments: List[Tuple[PointModel, PointModel]]) -> nx.Graph:
        """
        Create a graph from segments.
        
        Args:
            segments: List of tuples (start_point, end_point)
            
        Returns:
            NetworkX graph with points as nodes and segments as weighted edges
        """
        graph = nx.Graph()
        
        for start_point, end_point in segments:
            # Create hashable tuples for graph nodes
            start_node = (start_point.lat, start_point.lon)
            end_node = (end_point.lat, end_point.lon)
            
            # Calculate edge weight using haversine distance
            weight = haversine.haversine(
                (start_point.lat, start_point.lon),
                (end_point.lat, end_point.lon)
            )
            
            graph.add_edge(start_node, end_node, weight=weight)
        
        logger.info(f"Created graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    @staticmethod
    def simplify_graph(graph: nx.Graph, epsilon: float = 5.0) -> nx.Graph:
        """
        Simplify the graph by removing collinear nodes.
        
        Eliminates nodes with degree 2 that are nearly collinear with their neighbors.
        This reduces graph complexity while maintaining path accuracy.
        
        Args:
            graph: NetworkX graph to simplify
            epsilon: Maximum angle deviation from 180° to consider collinear (degrees)
            
        Returns:
            Simplified graph
        """
        # Find all nodes with exactly 2 connections
        nodes_degree_2 = [node for node in graph.nodes if graph.degree(node) == 2]
        removed_count = 0
        
        for node in nodes_degree_2:
            # Get the two neighbors
            neighbors = list(graph.adj[node])
            if len(neighbors) != 2:
                continue
                
            g1, g3 = neighbors
            
            # Calculate angle between the three points
            try:
                angle = GraphService._angle_of(g1, node, g3)
                
                # If angle is close to 180° (nearly straight line), remove the middle node
                if abs(180 - angle) < epsilon:
                    graph.remove_edge(g1, node)
                    graph.remove_edge(node, g3)
                    graph.remove_node(node)
                    
                    # Connect the two neighbors directly
                    weight = haversine.haversine(g1, g3)
                    graph.add_edge(g1, g3, weight=weight)
                    removed_count += 1
                    
            except (ValueError, ZeroDivisionError):
                # Skip nodes that cause calculation errors
                continue
        
        logger.info(f"Simplified graph: removed {removed_count} collinear nodes")
        logger.info(f"Final graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return graph
    
    @staticmethod
    def _angle_of(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """
        Calculate the angle at p2 formed by p1-p2-p3 using haversine distances.
        
        Args:
            p1, p2, p3: Points as (lat, lon) tuples
            
        Returns:
            Angle in degrees
        """
        # Calculate distances between points
        d1 = haversine.haversine(p1, p2)
        d2 = haversine.haversine(p2, p3)
        d3 = haversine.haversine(p1, p3)
        
        # Avoid division by zero
        if d1 == 0 or d2 == 0:
            return 180.0
        
        # Use law of cosines to find angle
        # cos(angle) = (d1² + d2² - d3²) / (2 * d1 * d2)
        cos_angle = (d1**2 + d2**2 - d3**2) / (2 * d1 * d2)
        
        # Clamp to [-1, 1] to avoid numerical errors in acos
        cos_angle = max(-1.0, min(1.0, cos_angle))
        
        return degrees(acos(cos_angle))
    
    @staticmethod
    def find_closest_node(graph: nx.Graph, point: PointModel) -> Node | None:
        """
        Find the closest graph node to a given point.
        
        Args:
            graph: NetworkX graph
            point: Target point
            
        Returns:
            Closest node as (lat, lon) tuple or None if graph is empty
        """
        min_dist = float("inf")
        closest_node = None
        
        target = (point.lat, point.lon)
        
        for node in graph.nodes:
            dist = haversine.haversine(target, node)
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        
        logger.debug(f"Found closest node at distance {min_dist:.3f} km")
        return closest_node
    
    @staticmethod
    def shortest_path(
        graph: nx.Graph, 
        start: Node, 
        end: Node,
    ) -> Tuple[float, List[Node]]:
        """
        Find shortest path between two nodes using A* algorithm with Haversine heuristic.
        
        A* is optimal for single-source single-target shortest path problems when
        you have an admissible heuristic (one that never overestimates the true cost).
        The Haversine distance is the great-circle distance, which is always ≤ actual
        path distance, making it a perfect admissible heuristic.
        
        Args:
            graph: NetworkX graph
            start: Start node as (lat, lon) tuple
            end: End node as (lat, lon) tuple
            
        Returns:
            Tuple of (total_distance, path_nodes)
            
        Raises:
            nx.NetworkXNoPath: If no path exists between start and end
        """
        distance, path = GraphService._astar_search(graph, start, end)
        logger.debug(f"A* found path of length {distance:.3f} km with {len(path)} nodes")
        return distance, path
    
    @staticmethod
    def _haversine_heuristic(node: Node, goal: Node) -> float:
        """
        Haversine distance heuristic for A* search.
        
        This computes the great-circle distance between two points on Earth,
        which is always less than or equal to any path distance through a road
        network. This makes it an admissible heuristic, guaranteeing A* finds
        the optimal path.
        
        Args:
            node: Current node as (lat, lon)
            goal: Goal node as (lat, lon)
            
        Returns:
            Distance in kilometers (same unit as edge weights)
        """
        return haversine.haversine(node, goal)
    
    @staticmethod
    def _astar_search(
        graph: nx.Graph, 
        start: Node, 
        goal: Node
    ) -> Tuple[float, List[Node]]:
        """
        A* search algorithm implementation with Haversine heuristic.
        
        A* maintains a priority queue ordered by f(n) = g(n) + h(n), where:
        - g(n) is the actual cost from start to node n
        - h(n) is the heuristic estimate from n to goal
        
        The algorithm explores nodes in order of their f-score, always expanding
        the most promising node first. This "pulls" the search toward the goal,
        drastically reducing nodes visited compared to Dijkstra.
        
        Performance characteristics:
        - Time: O(|E| log |V|) worst case, but typically much better due to heuristic
        - Space: O(|V|) for the priority queue and visited sets
        - Nodes visited: Typically 10-100x fewer than Dijkstra for geographic networks
        
        Args:
            graph: NetworkX graph with 'weight' edge attributes
            start: Start node as (lat, lon)
            goal: Goal node as (lat, lon)
            
        Returns:
            Tuple of (total_distance, path as list of nodes)
            
        Raises:
            nx.NetworkXNoPath: If no path exists
        """
        if start not in graph:
            raise nx.NodeNotFound(f"Start node {start} not in graph")
        if goal not in graph:
            raise nx.NodeNotFound(f"Goal node {goal} not in graph")
        
        # Priority queue: (f_score, counter, node)
        # Counter breaks ties to ensure consistent ordering
        counter = 0
        open_set: List[Tuple[float, int, Node]] = []
        heapq.heappush(open_set, (0, counter, start))
        
        # Track where we came from for path reconstruction
        came_from: Dict[Node, Node] = {}
        
        # g_score[n] = cost of cheapest path from start to n
        g_score: Dict[Node, float] = {start: 0}
        
        # f_score[n] = g_score[n] + h(n)
        f_score: Dict[Node, float] = {start: GraphService._haversine_heuristic(start, goal)}
        
        # Set of nodes already evaluated
        closed_set: Set[Node] = set()
        
        # Nodes currently in the open set (for O(1) lookup)
        open_set_hash: Set[Node] = {start}
        
        nodes_visited = 0
        
        while open_set:
            # Get node with lowest f_score
            _, _, current = heapq.heappop(open_set)
            open_set_hash.discard(current)
            nodes_visited += 1
            
            # Skip if already processed (can happen with duplicate entries)
            if current in closed_set:
                continue
            
            # Goal reached - reconstruct and return path
            if current == goal:
                path = GraphService._reconstruct_path(came_from, current)
                total_distance = g_score[current]
                logger.debug(f"A* visited {nodes_visited} nodes (graph has {graph.number_of_nodes()} nodes)")
                return total_distance, path
            
            closed_set.add(current)
            
            # Explore neighbors
            for neighbor in graph.neighbors(current):
                if neighbor in closed_set:
                    continue
                
                # Get edge weight (distance)
                edge_data = graph.get_edge_data(current, neighbor)
                edge_weight = edge_data.get('weight', 1.0)
                
                # Calculate tentative g_score
                tentative_g = g_score[current] + edge_weight
                
                # Is this a better path to the neighbor?
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    # Update path
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + GraphService._haversine_heuristic(neighbor, goal)
                    
                    # Add to open set if not already there
                    if neighbor not in open_set_hash:
                        counter += 1
                        heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                        open_set_hash.add(neighbor)
        
        # No path found
        raise nx.NetworkXNoPath(f"No path between {start} and {goal}")
    
    @staticmethod
    def _reconstruct_path(came_from: Dict[Node, Node], current: Node) -> List[Node]:
        """
        Reconstruct path from start to current by following came_from links.
        
        Args:
            came_from: Dictionary mapping each node to its predecessor
            current: The goal node
            
        Returns:
            List of nodes from start to goal
        """
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    @staticmethod
    def shortest_path_dijkstra(
        graph: nx.Graph, 
        start: Node, 
        end: Node,
    ) -> Tuple[float, List[Node]]:
        """
        Find shortest path using Dijkstra's algorithm (fallback/comparison method).
        
        Use this for multi-target scenarios where A* isn't optimal,
        or for benchmarking A* performance improvements.
        
        Args:
            graph: NetworkX graph
            start: Start node (lat, lon)
            end: End node (lat, lon)
            
        Returns:
            Tuple of (total_distance, path_nodes)
        """
        distance, path = nx.single_source_dijkstra(graph, start, end, weight="weight")
        logger.debug(f"Dijkstra found path of length {distance:.3f} km with {len(path)} nodes")
        return distance, path
