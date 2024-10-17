"""
Contain tools to process geographical information...
"""
from typing import Any

import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.neighbors import BallTree


# step 1. for each dot (stop_id), given remaining traveling time, computer a buffer zone
# step 2. merge the buffer zone together as a whole buffer zone.
def to_from_utm(shp, proj, inv=False):
    import shapely.geometry as shpgeo
    geo_interface = shp.__geo_interface__

    shpType = geo_interface['type']
    coords = geo_interface['coordinates']
    # print(shpType, coords)
    if shpType == 'Point':
        new_coord = [proj(*coords, inverse=inv)]
    if shpType == 'Polygon':
        new_coord = [[proj(*point, inverse=inv) for point in linring] for linring in coords]
    if shpType == 'MultiPolygon':
        new_coord = [[[proj(*point, inverse=inv) for point in linring] for linring in poly] for poly in coords]

    return shpgeo.shape({'type': shpType, 'coordinates': tuple(new_coord)})


def get_buffer_geom(
        stops_gdf: gpd.GeoDataFrame,
        tot_time: float,
        walking_speed: float = 1,
) -> gpd.GeoSeries:
    from shapely.ops import unary_union
    import utm
    import pyproj

    curr_proj = stops_gdf.crs
    stops_gdf = stops_gdf.to_crs("epsg:4326")  # to wgs84
    # print("stops_gdf head:")
    # print(stops_gdf.head())

    lat0, lon0 = stops_gdf['stop_lat'].mean(), stops_gdf['stop_lon'].mean()
    print("lat0, lon0:", lat0, lon0)
    __, __, zone, __ = utm.from_latlon(lat0, lon0)
    proj = pyproj.Proj(proj="utm", zone=zone, ellps="WGS84", datum="WGS84")

    buffs = []
    for i, row in stops_gdf.iterrows():
        _remain_time = tot_time - row["acc_time"]
        # walking distance in miles
        _remain_wd = (_remain_time / 60) * walking_speed

        _geom = row["geometry"]
        _geom_utm = to_from_utm(_geom, proj, "")
        _geom_utm = _geom_utm.buffer(_remain_wd * 1609.34)  # mile to meter
        _geom_buff = to_from_utm(_geom_utm, proj, inv=True)
        buffs.append(_geom_buff)
    # combine all buffs into one shape
    boundary = gpd.GeoSeries(unary_union(buffs), crs="epsg:4326")
    boundary = boundary.to_crs(curr_proj)
    return boundary


# when building network, each stop needs to know its neighboring stops
# within walking distance, compute nearest points for each stop
def find_stops_neighbors_within_buffer(
        stops: pd.DataFrame,
        bw_mile: float = 0.25,
) -> gpd.GeoDataFrame:
    # convert to geopandas
    stops = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat)
    )
    # add projection
    stops = stops.set_crs('epsg:3857')
    # set up indicies
    bt = BallTree(
        np.deg2rad(stops[['stop_lat', 'stop_lon']].values),
        metric='haversine')
    # for each row's (lat, lon), query neighbors
    neighbors, dists = [], []
    for i, row in stops.iterrows():
        indicies, distances = bt.query_radius(
            np.deg2rad(np.c_[row['stop_lat'], row['stop_lon']]),
            r=bw_mile / 3959.8,  # mile
            return_distance=True
        )
        neighbors.append(indicies[0])
        # convert distance from rad to miles
        dists.append(distances[0] * 3959.8)
    stops['neighbors'] = neighbors
    stops['dists'] = dists
    return stops


# Find neighbors given any coordinates
def find_nei_stops_given_coords(
        stops: gpd.GeoDataFrame,
        locs: list[tuple[float, float]],
        bw_mile: float = 0.5,
        return_all_neighbors=False,
) -> tuple[Any, Any]:
    # for each loc, get the nearest stops
    # set up indices
    bt = BallTree(
        np.deg2rad(stops[['stop_lat', 'stop_lon']].values),
        metric='haversine'
    )
    stops_idx = []
    dists = []
    for loc in locs:
        indices, distances = bt.query_radius(
            np.deg2rad(np.c_[loc[0], loc[1]]),
            r=bw_mile / 3959.8,  # mile
            return_distance=True
        )
        indices = indices[0]
        distances = distances[0]
        stops_idx += indices.flatten().tolist()
        dists += (distances * 3959.8).flatten().tolist()

    # stops_idx = np.concatenate(stops_idx).tolist()
    # dists = np.concatenate(dists).tolist()
    print("stops_idx:", stops_idx)
    print("dists:", dists)

    # merge and only keep the nearest points
    if return_all_neighbors is False:
        stops_idx = [stops.iloc[stops_idx[0]]["stop_id"]]
        dists = [dists[0]]
    else:
        stops_idx = [stops.iloc[idx]["stop_id"] for idx in stops_idx]

    return stops_idx, dists


