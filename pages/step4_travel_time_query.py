"""
Start from one origin to all destinations

"""

import streamlit as st
import sys
import time
import numpy as np
sys.path.append("..")
import script.gtfs_graph as gtfs_graph
from script.gtfs_graph import GTFS_Graph
from script.gtfs_controller import GTFSController
import script.utils as ut
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
from streamlit_folium import st_folium, folium_static


if "b4_1_clicked" not in st.session_state.keys():
    st.session_state["b4_1_clicked"] = False
if "stop_id" not in st.session_state.keys():
    st.session_state["stop_id"] = ""


def page4_init():
    global GTFS_OBJ, GRAPH_OBJ
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]
    print("step4 GTFS_OBJ", GTFS_OBJ)
    print("step4 GRAPH_OBJ", GRAPH_OBJ)
    if "stops" not in st.session_state:
        st.session_state["stops"] = None


def page_4():
    stops = st.session_state["stops"]
    print("step 4 stops length:", len(stops))
    # stops need to be filtered for the schedule...
    # stops = GTFS_OBJ.dfs["stops.txt"]
    col1, col2 = st.columns(2)
    with col1:
        st.write("Step 4. Query shortest travel scheme from one origin at different time of the day")
        stop_id = st.text_input("choose stop id")
        depart_hr = st.slider("Departure time (hour of a day)",
                              0, 23, 8, 1)
        max_tt = st.slider("Select maximum travel time (cutoff of the Dijkstra's algorithm)",
                           0, 180, 120, 15)
    with col2:
        # plot map for reference...
        st.write("map reference of stops")
        with st.spinner('Loading map...'):
            # ut.show_stops_map(GTFS_OBJ)
            m = ut.show_stops_given_df(stops, w=600, h=600)
            folium_static(m)
    return stops, stop_id, depart_hr, max_tt


def page_4_execute(stops, stop_id, depart_hr, max_tt):
    m = None
    for key in GRAPH_OBJ.nodes_time_map:
        if not isinstance(key, str):
            stop_id = int(stop_id)
        break
    # start building network and query shortest paths
    if (st.button("Start analysis & plot results") or
            st.session_state.b4_1_clicked and
            stop_id != ""):  # if stop_id != "", no inputs, just enter the page
        st.session_state["b4_1_clicked"] = True
        st.session_state["stop_id"] = stop_id

        my_bar = st.progress(0)

        with st.spinner('Analyzing shortest travel time to other stops...'):
            # find shortest paths from stop_id
            one_source_paths = GRAPH_OBJ.query_origin_stop_time(
                stop_id=stop_id,
                depart_min=60 * depart_hr,  # departure at 8 AM
                cutoff=max_tt)
            # with st.spinner('Analyzing shortest travel time to other stops...'):
            my_bar.progress(25)
            # get a dict of shortest path information
            one_source_access_dict = GRAPH_OBJ.get_shortest_tts(one_source_paths)
            my_bar.progress(50)
            one_source_path_dict = GRAPH_OBJ.get_shortest_paths(one_source_paths)
            my_bar.progress(75)
            # then, plot graph searched results
            m = ut.display_one_origin_map(stops,
                                          GRAPH_OBJ,
                                          one_source_access_dict,
                                          one_source_path_dict)
            my_bar.progress(100)
    return m


page4_init()

if GTFS_OBJ is not None and GRAPH_OBJ is not None:
    stops, stop_id, depart_hr, max_tt = page_4()
    m = page_4_execute(stops, stop_id, depart_hr, max_tt)
    if m is not None:
        folium_static(m, width=700, height=500)
