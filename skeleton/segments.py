from typing import TypeAlias
from dataclasses import dataclass
import requests
import gpxpy
from sklearn.cluster import KMeans
import staticmap
from haversine import haversine
import json
import os
from datetime import datetime


@dataclass
class Point:
    lat: float
    lon: float

    def __hash__(self) -> int:
        return hash((self.lat, self.lon))


@dataclass
class Segment:
    start: Point
    end: Point


@dataclass
class Box:
    bottom_left: Point
    top_right: Point

    def __str__(self) -> str:
        return f"{self.bottom_left.lat}_{self.bottom_left.lon}_{self.top_right.lat}_{self.top_right.lon}"


Segments: TypeAlias = list[Segment]
PointsInfo: TypeAlias = list[
    tuple[float, float, datetime, int, int]
]  # lat, lon, time, track, page


def _download_points(box: Box, filename: str) -> None:
    """Download all points in the box and save them to the file."""
    box1 = f"{box.bottom_left.lon},{box.bottom_left.lat},{box.top_right.lon},{box.top_right.lat}"
    page = 0
    count = 0
    
    # Create directory if it doesn't exist
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    os.makedirs(dir_name, exist_ok=True)
    
    with open(
        os.path.join(dir_name, filename),
        "w",
    ) as file:
        while True:
            url = f"https://api.openstreetmap.org/api/0.6/trackpoints?bbox={box1}&page={page}"
            response = requests.get(url)
            gpx_content = response.content.decode("utf-8")
            gpx = gpxpy.parse(gpx_content)
            if len(gpx.tracks) == 0:
                break
            for t, track in enumerate(gpx.tracks):
                for segment in track.segments:
                    if all(point.time is not None for point in segment.points):
                        segment.points.sort(key=lambda p: p.time)  # type: ignore
                        for p in segment.points:
                            file.write(
                                f"{p.latitude},{p.longitude},{p.time},{t},{page}\n"
                            )
                            count += 1
            page += 1
    print(f"Downloaded {count} points to {filename}")


def _load_points(box: Box, filename: str) -> PointsInfo:
    """Load points from the file."""
    points: PointsInfo = []
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    try:
        with open(
            os.path.join(dir_name, filename),
            "r",
        ) as file:
            for line in file:
                lat, lon, time, track, page = line.split(",")
                t: datetime = datetime.strptime(time.split("+")[0], "%Y-%m-%d %H:%M:%S")
                points.append((float(lat), float(lon), t, int(track), int(page)))
    except FileNotFoundError:
        _download_points(box, filename)
        points = _load_points(box, filename)
    return points


def download_segments(box: Box, filename: str) -> None:
    """Download all segments in the box and save them to the file."""
    # import settings from settings_file.json
    with open("settings_file.json", "r") as f:
        data = json.load(f)
        time_delta = data["time_delta"]
        distance_delta = data["distance_delta"]
        n_clust = data["n_clusters"]

    # Load points from file
    all_points: PointsInfo = _load_points(box, "pointinfo.txt")

    # Perform Kmeans clustering
    kmeans = KMeans(n_clusters=n_clust, random_state=0, n_init=10).fit(
        [(lat, lon) for lat, lon, _, _, _ in all_points]
    )
    centers = kmeans.cluster_centers_
    labels = kmeans.labels_
    segments: set[tuple[Point, Point]] = set()

    # from the list of points we need to find a segment that has points in different labels,
    # the time difference is less than TIME_DELTA seconds, the distance is less than DISTANCE_DELTA km,
    # and the track and page are the same

    for i in range(1, len(all_points)):
        _, _, time1, track1, page1 = all_points[i - 1]
        _, _, time2, track2, page2 = all_points[i]
        lat1, lon1 = centers[labels[i - 1]]
        lat2, lon2 = centers[labels[i]]
        if (
            abs(time2 - time1).total_seconds() < time_delta
            and haversine((lat1, lon1), (lat2, lon2)) < distance_delta
            and labels[i - 1] != labels[i]
            and track1 == track2
            and page1 == page2
        ):
            if labels[i + 1] < labels[i]:
                segments.add((Point(lat1, lon1), Point(lat2, lon2)))
            else:
                segments.add((Point(lat2, lon2), Point(lat1, lon1)))

    # Save segments to file
    seg_count = 0
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    os.makedirs(dir_name, exist_ok=True)
    
    with open(
        os.path.join(dir_name, filename),
        "w",
    ) as f:
        for segment in segments:
            seg_count += 1
            f.write(
                f"{segment[0].lat},{segment[0].lon},{segment[1].lat},{segment[1].lon}\n"
            )
        print(f"Saved {seg_count} segments to {filename}")


def load_segments(box: Box, filename: str) -> Segments:
    """Load segments from the file."""
    segm: Segments = []
    dir_name = f"{box.bottom_left.lat}_{box.bottom_left.lon}_{box.top_right.lat}_{box.top_right.lon}"
    with open(
        os.path.join(dir_name, filename),
        "r",
    ) as f:
        for línia in f.readlines():
            lat1, lon1, lat2, lon2 = línia.split(",")
            segm.append(
                Segment(
                    Point(float(lat1), float(lon1)), Point(float(lat2), float(lon2))
                )
            )
    return segm


def get_segments(box: Box, filename: str) -> Segments:
    """Return all segments in the box."""
    download_segments(box, filename)
    return load_segments(box, filename)


def show_segments(segments: Segments, filename: str) -> None:
    """Show all segments in a PNG file using staticmap."""
    map = staticmap.StaticMap(400, 400)
    for segment in segments:
        map.add_line(
            staticmap.Line(
                [
                    (segment.start.lon, segment.start.lat),
                    (segment.end.lon, segment.end.lat),
                ],
                "blue",
                2,
            )
        )
    image = map.render()
    image.save(filename)
