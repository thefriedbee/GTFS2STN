"""
Build spatiotemporal network based on needs
"""
import sys
import json
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
import streamlit as st


GTFS_OBJ = st.session_state["GTFS_OBJ"]
print("step3 GTFS_OBJ", GTFS_OBJ)
# init configuration data holder
network_config_info = {}

# init button states the first time
if "b3_1_clicked" not in st.session_state.keys():
    st.session_state["b3_1_clicked"] = False
if "GRAPH_OBJ" not in st.session_state.keys():
    st.session_state["GRAPH_OBJ"] = None
st.session_state["GRAPH_OBJ"] = GTFS_Graph()


def page_3():
    st.write("Step 3. Build transit network")
    col1, col2 = st.columns(2)
    with col1:
        # (1) choose service id
        sids = GTFS_OBJ.dfs["calendar.txt"]["service_id"].tolist()
        service_ids = st.multiselect("choose service id", sids, sids[0])
        # (2) choose walk speed
        walk_speed = st.slider("Select walking speed (mph)", 1, 3, 1, 1)
        # (3) choose walk buffer (maximal walking distance)
        bw_mile = st.slider("Select maximum walking distance between stops (mile)",
                            0.0, 1.5, 0.25, 0.05)
        # (4) choose network's time resolution (15 minutes)
        time_res = st.select_slider("choose time resolution for entering/existing the transit system (minutes)",
                                    options=[5, 15, 30, 60], value=15)
        # update variables
        # update configuration information:
        network_config_info["service_id"] = service_ids
        network_config_info["walk_speed"] = walk_speed
        network_config_info["bw_mile"] = bw_mile
        network_config_info["time_res"] = time_res
        # (5) a button to generate spatio-temporal network (nested buttons)
        if (st.button("Generate Transit Network over space and time!") or
                st.session_state["b3_1_clicked"]):
            st.session_state["b3_1_clicked"] = True
            # start building the spatio-temporal network!
            print("network_config_info:", network_config_info)
            GRAPH_OBJ = build_network(network_config_info)
            print("GRAPH OBJ after built:", GRAPH_OBJ)
            st.download_button("Download network in JSON format!",
                               data=json.dumps(nx.to_dict_of_lists(GRAPH_OBJ.G)),
                               file_name='My_GTFS_Graph.json')
    with col2:  # show service id table to select
        st.write("'Calendar.txt' for reference")
        ut.show_interact_table(GTFS_OBJ, 'calendar.txt')


# given configurations, build network
def build_network(network_config_info):
    if len(network_config_info) == 0:
        return None
    # init graph
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]
    print("step3 GRAPH_OBJ in build_network:", GRAPH_OBJ)
    # load configuration variables
    service_ids = network_config_info["service_id"]
    walk_speed = network_config_info["walk_speed"]
    bw_mile = network_config_info["bw_mile"]
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
    return GRAPH_OBJ


# generate all stuff by running this function
page_3()

