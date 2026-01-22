from segments import get_segments, Box, Point, Segment, Segments
from graphmaker import make_graph, simplify_graph
from viewer import *
from monuments import get_monuments, Monument, Monuments
from routes import *

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.align import Align
from rich.prompt import Prompt

import json
import os
import time

from turfpy.measurement import bbox
from turfpy.transformation import circle as bounding_circle
from geojson import Feature
from geojson import Point as GeoPoint


BOX_CATALUNYA = Box(Point(40.475518, 0.055361), Point(42.903476, 3.494081))


console = Console()


class Settings:
    time_delta: int
    distance_delta: float
    n_clusters: int
    angle: int

    def __init__(self) -> None:
        with open("settings_file.json", "r") as f:
            data = json.load(f)
            self.time_delta = data["time_delta"]
            self.distance_delta = data["distance_delta"]
            self.n_clusters = data["n_clusters"]
            self.angle = data["angle"]


def _closest_point(graph: nx.Graph, point: Point) -> Point:
    """Find the closest node to the given point."""
    min_dist = float("inf")
    for node in graph.nodes:
        dist = haversine((point.lat, point.lon), (node.lat, node.lon))
        if dist < min_dist:
            min_dist = dist
            closest_point = node
    return closest_point


def _closest_edge(m: Monument, segments: Segments) -> Segment:
    """Find the closest edge to the monument."""
    min_dist = float("inf")
    for segment in segments:
        dist_end = haversine(
            (m.location.lat, m.location.lon), (segment.end.lat, segment.end.lon)
        )
        dist_start = haversine(
            (m.location.lat, m.location.lon), (segment.start.lat, segment.start.lon)
        )
        dist = min(dist_end, dist_start)
        if dist < min_dist:
            min_dist = dist
            closest_edge = segment
    return closest_edge


def _monuments_in_box(m: Monuments, box: Box) -> Monuments:
    """Get the monuments in the box."""
    m_in_box: Monuments = []
    for monument in m:
        if (
            monument.location.lat >= box.bottom_left.lat
            and monument.location.lat <= box.top_right.lat
            and monument.location.lon >= box.bottom_left.lon
            and monument.location.lon <= box.top_right.lon
        ):
            m_in_box.append(monument)
    return m_in_box


def _welcome_menu() -> str:
    """Shows the main menu."""
    console.clear()
    MARKDOWN = """### TRAILBLAZER"""
    md = Markdown(MARKDOWN)
    panel = Panel(md, style="bold green", expand=False)
    console.print(panel)

    text1 = Align.center("Welcome to Trailblazer!", style="bold yellow")
    text2 = Align.center("What would you like to explore today?", style="bold yellow")
    console.print(text1)
    console.print(text2)

    options = [
        "1 -> Military Buildings",
        "2 -> Religious Buildings",
        "3 -> Civil Buildings",
        "4 -> Other interesting places",
        "5 -> Settings",
        "6 -> Exit",
    ]
    console.print()
    console.print(
        Panel(
            "\n".join(options),
            title="Options:",
            expand=False,
            style="bold white",
            border_style="blue",
        ),
    )
    return Prompt.ask(
        "Select a valid option: ",
    )


def _select_monuments(options: str) -> Monuments:
    """Select the option."""
    opt = options.split("+")
    monuments: Monuments = []
    for o in opt:
        if o == "1":
            monuments.extend(get_monuments("edificacions-de-caracter-militar"))
        if o == "2":
            monuments.extend(get_monuments("edificacions-de-caracter-religios"))
        if o == "3":
            monuments.extend(get_monuments("edificacions-de-caracter-civil"))
        if o == "4":
            monuments.extend(get_monuments("altres-llocs-dinteres"))
    return monuments


def _get_current_location() -> Point | None:
    """Get the user's current location."""
    console.clear()

    MARKDOWN = """### TRAILBLAZER"""
    md = Markdown(MARKDOWN)
    panel = Panel(md, style="bold green", expand=False)
    console.print(panel)
    console.print(
        "Type 'q' to quit the program." + " Type 'r' to return to the main menu.",
        style="bold yellow",
    )
    console.print()
    ubi = Prompt.ask(
        "Where are you right now? (latitude, longitude) ex: 41.388725, 2.112347",
    )
    if ubi == "q":
        exit()
    if ubi == "r":
        return None
    print()
    try:
        loc = ubi.split(",")
        lat, long = float(loc[0]), float(loc[1])
        assert (
            BOX_CATALUNYA.bottom_left.lat <= lat <= BOX_CATALUNYA.top_right.lat
            and BOX_CATALUNYA.bottom_left.lon <= long <= BOX_CATALUNYA.top_right.lon
        )
        return Point(lat, long)
    except Exception as error:
        console.print("Invalid input. Please try again.", style="bold red")
        time.sleep(2)
        return _get_current_location()


def _generate_box(point: Point) -> Box | None:
    """Generate a box around the point."""
    print()
    dist_delta = Prompt.ask(
        "How far are you willing to walk? (in km) ex: 5.0, default= 5.0",
    )
    # Check if the user wants to quit the program
    if dist_delta == "q":
        exit()
    # Check if the user wants to return to the main menu
    if dist_delta == "r":
        return None
    print()
    try:
        dist = float(dist_delta)
        assert dist > 0
        p = Feature(geometry=GeoPoint((point.lat, point.lon)))
        circle = bounding_circle(p, int(dist) + 1)
        bbox_coords = bbox(circle)
        box = Box(
            Point(bbox_coords[0], bbox_coords[1]), Point(bbox_coords[2], bbox_coords[3])
        )
    except Exception as error:
        print(error)
        console.print("Invalid input. Please try again.", style="bold red")
        time.sleep(2)
        return _generate_box(point)
    print("Box:", box)
    return box


def _settings_menu(settings: Settings) -> None:
    """Shows the settings menu, where the user can choose the parameters for the graph."""
    console.clear()
    MARKDOWN = """### TRAILBLAZER"""
    md = Markdown(MARKDOWN)
    panel = Panel(md, style="bold green", expand=False)
    console.print(panel)
    settings_text = [
        f"Number of Clusters: {settings.n_clusters}",
        f"Time Delta: {settings.time_delta}",
        f"Distance Delta: {settings.distance_delta}",
        f"Angle: {settings.angle}",
    ]

    console.print(
        Panel(
            "\n".join(settings_text),
            title="Current Settings:",
            expand=False,
            style="bold white",
            border_style="bold magenta",
        ),
    )
    cont = Prompt.ask("Do you want to change the settings? (y/n)", default="n")
    if cont == "y":
        _change_settings(settings, invalid=False)
    else:
        return


def _change_settings(settings: Settings, invalid: bool) -> None:
    """Change the graph's parameters."""
    console.clear()
    MARKDOWN = """### TRAILBLAZER"""
    md = Markdown(MARKDOWN)
    panel = Panel(md, style="bold green", expand=False)
    console.print(panel)
    if invalid:
        console.print("Invalid input. Please try again.", style="bold red")
        invalid = False
    console.print("Change the settings:", style="bold yellow")
    n_clusters = Prompt.ask("Number of Clusters", default=settings.n_clusters)
    time_delta = Prompt.ask("Time Delta", default=settings.time_delta)
    distance_delta = Prompt.ask("Distance Delta", default=settings.distance_delta)
    angle = Prompt.ask("Angle", default=settings.angle)
    try:
        # Check if the input is valid
        assert int(n_clusters) > 0
        assert int(time_delta) > 0
        assert float(distance_delta) > 0
        assert int(angle) > 0
        settings.n_clusters = int(n_clusters)
        settings.time_delta = int(time_delta)
        settings.distance_delta = float(distance_delta)
        settings.angle = int(angle)
    except Exception as error:
        invalid = True
        _change_settings(settings, invalid)
    _save_file(settings)
    _settings_menu(settings)


def _save_file(settings: Settings) -> None:
    """Save the settings to a file."""
    with open("settings_file.json", "w") as f:
        json.dump(
            {
                "n_clusters": settings.n_clusters,
                "time_delta": settings.time_delta,
                "distance_delta": settings.distance_delta,
                "angle": settings.angle,
            },
            f,
        )


def _new_folder(box: Box) -> bool:
    """Create the folders if they do not exist."""
    if not os.path.exists(
        f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    ):
        os.mkdir(
            f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
        )
        return True
    else:
        console.print()
        console.print("You can find your routes here:", style="bold yellow")
        console.print(f"{box.__str__()}", style="bold cyan")
        console.print()
        if Prompt.ask("Do you want to overwrite the folder? (y/n)", default="n") == "y":
            return True

    return False


def _is_connex(graph: nx.Graph) -> bool:
    """Check if the graph is connected."""
    if not nx.is_connected(graph):
        console.print(
            "WARNING: Some routes might not exist, tread with caution.",
            style="bold red",
        )
        return False
    else:
        return True


def main() -> None:
    """Main function."""
    settings = Settings()
    options = _welcome_menu()
    while options != "6":

        # Change the settings
        if options == "5":
            _settings_menu(settings)
            options = _welcome_menu()
            continue

        # Download the selected monuments
        monuments = _select_monuments(options)
        print("Downloaded", len(monuments), "monuments.")

        # Get the current location and generate the box around it
        my_loc = _get_current_location()
        if my_loc is None:
            options = _welcome_menu()
            continue
        box = _generate_box(my_loc)
        if box is None:
            options = _welcome_menu()
            continue

        # Create the session folder
        if not _new_folder(box):
            options = _welcome_menu()
            continue

        # Load the segments
        segments = get_segments(box, "segments.txt")
        print("Downloaded", len(segments), "segments.")

        # Make and simplify the graph
        graph = make_graph(segments)
        graph_simpl = simplify_graph(graph, settings.angle)
        if not _is_connex(graph_simpl):  # Check if the graph is connected
            options = _welcome_menu()
            continue

        # Export the graph to a PNG and KML file
        export_PNG(box, graph_simpl, "graph.png")
        export_KML(box, graph, "graph.kml")

        # Select the monuments in the box
        mon_in_box = _monuments_in_box(monuments, box)
        print("Monuments in the box:", len(mon_in_box))

        # Find the closest edge to each monument and add the edges to the graph
        close_seg = [(m, _closest_edge(m, segments)) for m in mon_in_box]
        for m, seg in close_seg:
            graph.add_edge(m.location, seg.start)
            graph.add_edge(m.location, seg.end)

        # Find the closest graph node to a given point
        point = _closest_point(graph, my_loc)

        # Find the shortest routes to the monuments
        routes = find_routes(graph, point, mon_in_box)

        # Export the routes to a PNG and KML file
        export_PNG_routes(box, routes, "routes.png")
        export_KML_routes(box, routes, "routes.kml")
        console.print()
        console.print(f"You can find your routes here:", style="bold yellow")
        console.print(f"{box.__str__()}", style="bold cyan")
        time.sleep(5)
        options = _welcome_menu()


if __name__ == "__main__":
    main()
