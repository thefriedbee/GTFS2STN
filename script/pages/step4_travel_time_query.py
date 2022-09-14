"""
start from one origin to all destinations

"""

import streamlit as st
import sys
import numpy as np
sys.path.append("..")
import gtfs_graph
from gtfs_graph import GTFS_Graph
from gtfs_controller import GTFSController
import utils as ut
import networkx as nx
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
from sklearn.neighbors import BallTree

import bisect
from copy import deepcopy

import folium
import branca.colormap as cm
from streamlit_folium import st_folium


st.write("Step 4. Travel time index between same OD")
if "b4_1_clicked" not in st.session_state.keys():
    st.session_state["b4_1_clicked"] = False
if "stop_id" not in st.session_state.keys():
    st.session_state["stop_id"] = ""

GTFS_OBJ = st.session_state["GTFS_OBJ"]
GRAPH_OBJ = st.session_state["GRAPH_OBJ"]  # init object
print("step4 GTFS_OBJ", GTFS_OBJ)
print("step4 GRAPH_OBJ", GRAPH_OBJ)


# compute nearest points for each stop
def find_stops_neighbors_within_buffer(stops, bw_mile=0.25, walk_speed=0.05):
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
        dists.append(distances[0]* 3959.8)
    stops['neighbors'] = neighbors
    stops['dists'] = dists
    return stops


def page_3():
    max_tt = 60
    stops = GTFS_OBJ.dfs["stops.txt"]
    one_source_access_dict = {}
    col1, col2 = st.columns(2)
    m = None
    with col1:
        st.write("Step 4. Query shortest travel scheme from one origin at different time of the day")
        stop_id = st.text_input("choose stop id")
        max_tt = st.slider("Select maximum travel time (cutoff of the Dijkstra's algorithm)", 0, 180, 60, 15)
        depart_hr = st.slider("Departure time (hour of a day)", 0, 23, 8, 1)
        # start building network and query shortest paths
        if (st.button("Start analysis & plot results") or
                st.session_state.b4_1_clicked and
                stop_id != ""):  # if stop_id != "", no inputs, just enter the page
            st.session_state["b4_1_clicked"] = True
            st.session_state["stop_id"] = stop_id
            # find shortest paths from stop_id
            one_source_paths = GRAPH_OBJ.query_origin_stop_time(
                stop_id=stop_id,
                depart_min=60 * depart_hr,  # departure at 8 AM
                cutoff=max_tt)
            # get a dict of shortest path information
            one_source_access_dict = GRAPH_OBJ.get_shortest_tts(one_source_paths)
            one_source_path_dict = GRAPH_OBJ.get_shortest_paths(one_source_paths)
            # then, plot graph searched results
            m = ut.display_one_origin_map(stops,
                                          GRAPH_OBJ,
                                          one_source_access_dict,
                                          one_source_path_dict)
    with col2:
        # plot map for reference...
        st.write("visual reference of stops")
        ut.show_stops_map(GTFS_OBJ)
    return m


m = page_3()
if m is not None:
    st_data = st_folium(m, width=700, height=500)
