import googlemaps
from datetime import datetime
import os
import dotenv
import itertools

import pandas as pd


def get_transit_time(api_key: str, origin: str, destination: str, t0: datetime | None = None) -> tuple[str, str]:
    # Initialize the Google Maps client
    gmaps = googlemaps.Client(key=api_key)
    if t0 is None:
        t0 = datetime.now()

    # Request directions via public transit
    directions_result = gmaps.directions(
        origin,
        destination,
        mode="transit",
        departure_time=t0
    )

    # Extract the travel time
    if directions_result:
        leg = directions_result[0]['legs'][0]
        # duration in minutes...
        duration = int(leg['duration']['value']) / 60
        # add wait time
        if "departure_time" in leg:  # walk only mode has no departure time...
            ts = int(leg["departure_time"]["value"])
            tz = leg["departure_time"]["time_zone"]
            t1 = pd.to_datetime(ts, unit="s").tz_localize("utc").tz_convert(tz)
            t1_minutes = t1.hour * 60 + t1.minute
            t0_minutes = t0.hour * 60 + t0.minute
            pad_time = t1_minutes - t0_minutes
            # print(t0, t1)
            # print("pad_time", pad_time, t1_minutes, t0_minutes)
            duration = duration + pad_time
        
        # duration = float(duration.split(" ")[0])
        print(f"Travel time from {origin} to {destination} is {duration:.2f} minutes.")
        return duration, directions_result
    else:
        print("No transit route found.")
        return None, None


def coord_to_str(coord: tuple[float, float]) -> str:
    return f"{coord[0]},{coord[1]}"


def query_all_times(coords: list[tuple[float, float]], t0: datetime, MAP_API: str) -> list[float]:
    times = []
    ODs = list(itertools.permutations(coords, 2))
    ODs = [OD for OD in ODs if OD[0] != OD[1]]

    for orig_coord, dest_coord in ODs:
        orig_str = coord_to_str(orig_coord)
        dest_str = coord_to_str(dest_coord)
        tt, __ = get_transit_time(MAP_API, orig_str, dest_str, t0)
        times.append(tt)
    return times


if __name__ == "__main__":
    # Replace with your actual API key
    dotenv.load_dotenv()
    MAP_API = os.getenv('MAP_API')
    print("MAP_API: ", MAP_API)
    # Define the origin and destination coordinates
    origin = "37.7749,-122.4194"  # Example: San Francisco, CA
    destination = "34.0522,-118.2437"  # Example: Los Angeles, CA
    get_transit_time(MAP_API, origin, destination)
