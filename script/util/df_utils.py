"""
Utility functions for processing dataframes
"""
import geopandas as gpd
import pandas as pd


def filter_lonlat(
        nodes_df: pd.DataFrame,
        edges_df: pd.DataFrame,
        lon_min, lon_max, lat_min, lat_max
):
    filt_n1 = (lon_min <= nodes_df.lon) & (nodes_df.lon <= lon_max)
    filt_n2 = (lat_min <= nodes_df.lat) & (nodes_df.lat <= lat_max)
    print(sum(filt_n1 & filt_n2))

    filt_e1 = (lon_min <= edges_df.lon0) & (edges_df.lon0 <= lon_max) & \
              (lon_min <= edges_df.lon1) & (edges_df.lon1 <= lon_max)
    filt_e2 = (lat_min <= edges_df.lat0) & (edges_df.lat0 <= lat_max) & \
              (lat_min <= edges_df.lat1) & (edges_df.lat1 <= lat_max)
    print(sum(filt_e1 & filt_e2))

    nodes_df = nodes_df.loc[filt_n1 & filt_n2, :].copy()
    edges_df = edges_df.loc[filt_e1 & filt_e2, :].copy()
    return nodes_df, edges_df


# -----------Below are some query methods-----------
def get_info_given_trip_id(
        # either from "stop_times.txt" or "df_trips.txt"
        df: pd.DataFrame,
        trip_id: int,
) -> pd.DataFrame:
    filt = (trip_id == df['trip_id'])
    df = df[filt].copy()
    return df


def get_trips_given_block_id(
        trips: pd.DataFrame,
        block_id: str,
) -> pd.DataFrame:
    filt = (trips['block_id'] == block_id)
    trips = trips[filt].copy()
    return trips


def get_route_given_1trip(df_1trip, df_routes):
    rid = df_1trip["route_id"].iloc[0]
    filt = (df_routes["route_id"] == rid)
    return df_routes[filt].copy()


def get_shape_given_1trip(df_1trip, df_shapes):
    shape_id = df_1trip["shape_id"].iloc[0]
    filt = (df_shapes["shape_id"] == shape_id)
    return df_shapes[filt].copy()


def get_stops_by_stop_id(stops, stop_ids):
    stop_names = []
    for stop_id in stop_ids:
        stop_names.append('_'.join(stop_id.split("_")[:-1]))
    stop_names = list(set(stop_names))
    # print("stop names:", stop_names)
    return stops.loc[stops["stop_id"].isin(stop_names), :].copy()


def display_stops_one_source(
        stops: pd.DataFrame,
        one_source_access_dict: dict,
) -> gpd.GeoDataFrame:
    print("stops shape:", stops.shape)
    # print("stops head:")
    # print(stops.head())

    stops_acc = pd.DataFrame.from_dict(one_source_access_dict, orient='index')
    stops_acc = stops_acc.reset_index()
    stops_acc.columns = ["node_id", "acc_time"]
    print("stops_acc head:")
    print(stops_acc.head())
    print("stops_acc's shape:", stops_acc.shape)

    stops = stops[["stop_id", "stop_lat", "stop_lon", "stop_name", "node_id"]]
    stops = stops.merge(stops_acc, on="node_id", how="inner")
    # print("stops head:")
    # print(stops.head())
    print("stops shape after merge:", stops.shape)

    stops = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat)
    )
    stops = stops.set_crs('epsg:4326')

    # filter out -1 records (not accessible)
    stops = stops.loc[stops["acc_time"] >= 0, :]
    return stops

