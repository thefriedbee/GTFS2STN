"""
Build spatio-temporal network based on needs
"""
import sys
import json
import time
import numpy as np

sys.path.append("..")
import script.gtfs_graph
from script.gtfs_graph import GTFS_Graph
from script.gtfs_controller import GTFSController
import script.utils as ut

import networkx as nx
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st


# init configuration data holder
network_config_info = {}


def init_page3():
    global GTFS_OBJ, GRAPH_OBJ
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    print("step3 GTFS_OBJ: ", GTFS_OBJ)
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = GTFS_Graph()
    st.session_state["GRAPH_OBJ"] = GTFS_Graph()
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]
    print("step3 GRAPH_OBJ: ", GRAPH_OBJ)
    # filtered stops:

    # init button states the first time
    if "b3_1_clicked" not in st.session_state.keys():
        st.session_state["b3_1_clicked"] = False


def page_3():
    st.write("Step 3. Build transit network")
    col1, col2 = st.columns(2)
    with col1:
        # (1) choose service id
        sids = GTFS_OBJ.dfs["calendar.txt"]["service_id"].tolist()
        service_ids = st.multiselect("choose service id", sids, sids[0])
        # (2) choose walk buffer (maximal walking distance)
        bw_mile = st.slider("Select maximum walking distance between stops (mile)",
                            0.0, 1.5, 0.5, 0.05)
        # (3) choose walk speed
        walk_speed = st.slider("Select walking speed (mph)",
                               1, 3, 2, 1)
        # (4) choose network's time resolution (15 minutes)
        time_res = st.select_slider("choose time resolution for entering/existing the transit system (minutes)",
                                    options=[5, 15, 30, 60], value=15)
        # update variables
        # update configuration information:
        network_config_info["service_id"] = service_ids
        network_config_info["bw_mile"] = bw_mile
        network_config_info["walk_speed"] = walk_speed
        network_config_info["time_res"] = time_res
    with col2:  # show service id table to select
        st.write("'Calendar.txt' for reference")
        with st.spinner('Loading table calendar.txt...'):
            ut.show_static_table(GTFS_OBJ, 'calendar.txt')


def page_3_execute():
    # start building the spatio-temporal network!
    # (5) a button to generate spatio-temporal network (nested buttons)
    if (st.button("Generate Transit Network over space and time!") or
            st.session_state["b3_1_clicked"]):
        st.session_state["b3_1_clicked"] = True
        print("network_config_info:", network_config_info)
        with st.spinner('Building transit network...'):
            GRAPH_OBJ, stops = build_network(network_config_info)
            st.session_state["GRAPH_OBJ"] = GRAPH_OBJ
            st.download_button("Download network in JSON format!",
                               data=json.dumps(nx.to_dict_of_lists(GRAPH_OBJ.G)),
                               file_name='My_GTFS_Graph.json')
        st.success('Network built successfully!')
        if "stops" not in st.session_state:
            st.session_state["stops"] = None
        st.session_state["stops"] = stops


# given configurations, build network
def build_network(network_config_info):
    if len(network_config_info) == 0:
        return None
    print("step3 GRAPH_OBJ in build_network:", GRAPH_OBJ)
    # load configuration variables
    service_ids = network_config_info["service_id"]
    bw_mile = network_config_info["bw_mile"]
    walk_speed = network_config_info["walk_speed"]
    time_res = network_config_info["time_res"]
    # filter stop_times dataframe based on service ids
    trips_subset = ut.filter_trips_by_service_ids(GTFS_OBJ, service_ids)
    trips_ids = trips_subset["trip_id"].tolist()
    stop_times = ut.filter_stop_times_by_trip_ids(GTFS_OBJ, trips_ids)
    # also, filter the stops that is used in "stop_times"
    # get stops information
    stop_ids = list(set(stop_times["stop_id"].to_list()))
    stops = ut.filter_stops_by_stop_ids(GTFS_OBJ, stop_ids)
    # stops = GTFS_OBJ.dfs["stops.txt"]
    stops = ut.find_stops_neighbors_within_buffer(stops, bw_mile=bw_mile)
    # stop_times = GTFS_OBJ.dfs["stop_times.txt"]
    # build spatio-temporal networks
    gtfs_graph.add_nodes_all_stops(stops, GRAPH_OBJ, t_step=time_res)
    gtfs_graph.add_edges_all_stop_times(stop_times, GRAPH_OBJ)
    GRAPH_OBJ.add_edges_walkable_stops(stops, walk_speed=walk_speed)
    # add edges within the same stop
    GRAPH_OBJ.add_edges_within_same_stops()
    # add destination nodes
    GRAPH_OBJ.add_hyper_nodes()
    return GRAPH_OBJ, stops


init_page3()
# generate all stuff by running this function
if st.session_state["GTFS_OBJ"] is not None:
    page_3()  # draw basic layouts
    page_3_execute()

