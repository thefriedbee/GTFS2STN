"""
This module includes the basic methods that can be used/reused
by multiple pages app displaying GTFS information
"""

import os
from glob import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st

from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

from scipy.spatial import cKDTree
from sklearn.neighbors import BallTree
import folium
import branca.colormap as cm


# check all files previously stored for analysis
def init_agencies():
    global AGENCIES
    AGENCIES = os.walk(os.path.join("..", "GTFS_inputs"))
    AGENCIES = glob(os.path.join("..", "GTFS_inputs", "*"),
                    recursive=False)
    AGENCIES = [f.split('/')[-1] for f in AGENCIES]
    return AGENCIES


# display table and map information for the stops for analysis
def show_stops_table(GTFS_OBJ, w=600, h=600):
    # task: show top 5 rows of the station.txt file using Pandas
    GTFS_OBJ.display_table(fn="stops.txt", width=w, height=h)
    return GTFS_OBJ


def show_stops_map(GTFS_OBJ, w=600, h=600):
    GTFS_OBJ.display_stops_map(width=w, height=h)


def show_static_table(GTFS_OBJ, df_name, w=600, h=600):
    df = GTFS_OBJ.dfs[df_name]
    # display configuration
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=False,
                            paginationPageSize=10)
    gb.configure_selection(selection_mode="disabled",
                           use_checkbox=False)
    gridOptions = gb.build()
    selected_data = AgGrid(df, gridOptions=gridOptions)


def show_interact_table(GTFS_OBJ, df_name):
    df = GTFS_OBJ.dfs[df_name]
    # display configuration
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination()
    gb.configure_selection(selection_mode="multiple",
                           use_checkbox=True,
                           # pre_selected_rows=list(range(len(df)))
                           )
    gridOptions = gb.build()
    selected_data = AgGrid(df, gridOptions=gridOptions)
                           # allow_unsafe_jscode=True,
                           # update_mode=GridUpdateMode.NO_UPDATE)


# when building network, each stop needs to know its neighboring stops
# within walking distance, compute nearest points for each stop
def find_stops_neighbors_within_buffer(stops, bw_mile=0.25):
    # convert to geopandas
    stops = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat)
    )
    # print(stops.crs is None)
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
            r=bw_mile/3959.8,  # mile
            return_distance=True
        )
        neighbors.append(indicies[0])
        # convert distance from rad to miles
        dists.append(distances[0] * 3959.8)
    stops['neighbors'] = neighbors
    stops['dists'] = dists
    return stops


def display_one_origin_map(stops, GRAPH_OBJ, one_source_access_dict, one_source_path_dict):
    stops_acc = pd.DataFrame.from_dict(one_source_access_dict, orient='index')
    stops_acc = stops_acc.reset_index()
    stops_acc.columns = ["stop_id", "acc_time"]
    stops_pth = pd.DataFrame(pd.Series(one_source_path_dict))
    stops_pth = stops_pth.reset_index()
    stops_pth.columns = ["stop_id", "trajectory"]
    # merge info
    stops_acc = stops_acc.merge(stops_pth, on="stop_id", how="left")
    stops_acc["stop_id"] = stops_acc["stop_id"].str[:-2]
    print("stops_acc:")
    print(stops_acc.head(2))
    stops = stops[["stop_id", "stop_lat", "stop_lon", "stop_name", "stop_code"]]
    stops['stop_id'] = stops['stop_id'].astype(int)
    stops_acc['stop_id'] = stops_acc['stop_id'].astype(int)

    stops = stops.merge(stops_acc, on="stop_id", how="left")
    print("stops:")
    print(stops.head(2))
    m = folium.Map(location=[stops['stop_lat'].mean(),
                             stops['stop_lon'].mean()],
                   zoom_start=10)

    # create colormaps
    colormap = cm.LinearColormap(colors=['green', 'yellow', 'red'],
                                 vmin=0, vmax=120)

    def get_color(v):
        try:
            return colormap(v)
        except:
            return "#bbbbbb"

    # add stops
    for i, row_info in stops[["stop_id", "stop_lat", "stop_lon",
                              "stop_name", "stop_code", "acc_time",
                              "trajectory"]].iterrows():
        # for each trajectory, compute their travel time series
        if isinstance(row_info["trajectory"], float):
            wt_lst, tt_lst = [], []
        else:
            wt_lst, tt_lst = get_path_costs(GRAPH_OBJ, row_info["trajectory"])
        row_lst = row_info.values.tolist()
        popup_info = f"stop_id: {row_info[0]} <br>" \
                     f"travel time: {row_info[5]} <br>" \
                     f" trajectory: {row_info[6]} <br>" \
                     f" tt costs: {tt_lst} <br>"
        if row_lst[5] == -1.0:
            row_lst[5] = np.nan

        iframe = folium.IFrame(popup_info)
        popup = folium.Popup(iframe,
                             min_width=500, max_width=800,
                             min_height=100, max_height=500)

        folium.CircleMarker(
            row_lst[1:3],
            popup=popup,
            tooltip=f"travel time: {row_lst[5]:.2f} <br> stop id: {row_lst[0]}",
            radius=2,
            weight=5,
            color=get_color(row_lst[5])
        ).add_to(m)
    m.add_child(colormap)
    return m


# get subset trips given service ids
def filter_trips_by_service_ids(GTFS_OBJ, service_ids):
    # service_ids: a list of service ids
    trips = GTFS_OBJ.dfs["trips.txt"]
    filt = trips["service_id"].isin(service_ids)
    trips_subset = trips[filt]  # ["trip_id"].tolist()
    return trips_subset


def filter_stop_times_by_trip_ids(GTFS_OBJ, trip_ids):
    # trip_ids: a list of trip ids
    stop_times = GTFS_OBJ.dfs["stop_times.txt"]
    filt = stop_times["trip_id"].isin(trip_ids)
    stop_times_subset = stop_times[filt]
    return stop_times_subset


def filter_stops_by_stop_ids(GTFS_OBJ, stop_ids):
    stops = GTFS_OBJ.dfs["stops.txt"]
    filt = stops["stop_id"].isin(stop_ids)
    return stops[filt]


def get_path_costs(GRAPH_OBJ, nodes_lst):
    # print("node_lst:", nodes_lst)
    if len(nodes_lst) == 0:
        return np.nan, np.nan
    wt_lst, tt_lst = [], []
    edge_lst = []
    for i in range(len(nodes_lst)-1):
        node_i = nodes_lst[i]
        node_j = nodes_lst[i+1]
        edge = GRAPH_OBJ.G.edges[node_i, node_j]
        wt_lst += [round(float(edge['wt']), 2)]  # waiting time
        tt_lst += [round(float(edge['tt']), 2)]  # travel time
    return wt_lst, tt_lst

