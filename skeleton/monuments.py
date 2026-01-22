from dataclasses import dataclass
from typing import TypeAlias
from segments import *
from bs4 import BeautifulSoup
import requests
import requests.exceptions
from rich.progress import Progress
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class Monument:
    name: str
    location: Point


Monuments: TypeAlias = list[Monument]


def _process_monument(mon: BeautifulSoup) -> Monument | None:
    """Download the monument from the link."""
    try:
        link = mon.find("a")
        response_link = requests.get(link.get("href"))
        soup_link = BeautifulSoup(response_link.content, "html.parser")
        info = soup_link.find_all("p")
        for i in info:
            if "Localització" in i.text:
                return Monument(link.text, _get_coordinates(i.text))
    except (
        ValueError,
        AttributeError,
        requests.exceptions.RequestException,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ConnectionError,
    ):
        return None
    return None


def download_monuments(type: str) -> Monuments:
    """Download monuments from Catalunya Medieval."""
    m: Monuments = []
    url = f"https://www.catalunyamedieval.es/{type}/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    count = 0
    pos_mon = [
        ["castell", "torre", "epoca-carlina", "muralles"],
        ["casa-forta", "palau", "pont", "torre-colomer"],
        ["basilica", "catedral", "ermita", "esglesia", "monestir"],
    ]
    if type == "edificacions-de-caracter-militar":
        posmon = pos_mon[0]
    elif type == "edificacions-de-caracter-civil":
        posmon = pos_mon[1]
    elif type == "edificacions-de-caracter-religios":
        posmon = pos_mon[2]
    else:
        posmon = [type]

    all_monuments = []
    for pos in posmon:
        all_monuments.extend(soup.find_all("li", class_=pos))

    count = 0
    # Show progress bar
    with Progress() as progress:
        task = progress.add_task(
            "Downloading all monuments...", total=len(all_monuments)
        )
        # Uses ThreadPoolExecutor to download the monuments concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(_process_monument, mon): mon for mon in all_monuments
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    m.append(result)
                    count += 1
                progress.update(task, advance=1)

    print(f"Downloaded {count} monuments out of {len(all_monuments)}")
    return m


def _get_coordinates(text: str) -> Point:
    """Get the coordinates from a text."""
    index_N = text.index("N")
    localitzacio = "".join(
        c for c in text[index_N : index_N + 26] if c.isdigit() or c == "." or c == " "
    )
    return _location_to_point(localitzacio)


def _location_to_point(loc: str) -> Point:
    """Convert location to a point."""
    h1, min1, sec1, h2, min2, sec2 = loc.split()
    lat = float(h1) + float(min1) / 60 + float(sec1) / 3600
    lon = float(h2) + float(min2) / 60 + float(sec2) / 3600
    return Point(lat, lon)


def load_monuments(filename: str) -> Monuments:
    """Load monuments from a file."""
    m: Monuments = []
    with open(filename, "r") as f:
        for line in f:
            name, lat, lon = line.strip().split(";")
            m.append(Monument(name, Point(float(lat), float(lon))))
    return m


def get_monuments(filename: str) -> Monuments:
    """
    Get all monuments in the box.
    If filename exists, load monuments from the file.
    Otherwise, download monuments and save them to the file.
    """
    try:
        m = load_monuments(filename)
    except FileNotFoundError:
        m = download_monuments(filename)
        with open(filename, "w", encoding="utf-8") as f:
            for monument in m:
                f.write(
                    f"{monument.name};{monument.location.lat};{monument.location.lon}\n"
                )
    return m
