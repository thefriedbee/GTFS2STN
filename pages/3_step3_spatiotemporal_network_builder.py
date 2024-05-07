"""
Build spatio-temporal network based on needs
"""
import json
import pickle
import networkx as nx
from networkx.readwrite import json_graph
import streamlit as st

from script.GTFSGraph import GTFSGraph
from script.gtfs_controller import (
    build_network
)

import script.util.table_viewer as table_util


st.set_page_config(layout="wide", page_title="GTFS2STN", page_icon="🚌")
# init configuration data holder
network_config_info = {}


def init_page3():
    global GTFS_OBJ, GRAPH_OBJ
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    print("step3 GTFS_OBJ: ", GTFS_OBJ)
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = GTFSGraph()
    st.session_state["GRAPH_OBJ"] = GTFSGraph()
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]
    print("step3 GRAPH_OBJ: ", GRAPH_OBJ)

    # init button states the first time
    if "b3_1_clicked" not in st.session_state.keys():
        st.session_state["b3_1_clicked"] = False


def page_3():
    st.title("Step 3. Build transit network")
    col1, col2 = st.columns(2)
    with col1:
        # (1) choose service id
        sids = GTFS_OBJ.dfs["calendar.txt"]["service_id"].tolist()
        service_ids = st.multiselect("choose service id", sids, sids[0])
        # (2) choose walk buffer (maximal walking distance)
        bw_mile = st.slider(
            "Select maximum walking distance between stops (mile)",
            0.0, 0.5, 0.25, 0.05
        )
        # (3) choose walk speed
        walk_speed = st.slider(
            "Select walking speed (mph)",
            1, 3, 2, 1
        )
        # update configuration information:
        network_config_info["service_id"] = service_ids
        network_config_info["bw_mile"] = bw_mile
        network_config_info["walk_speed"] = walk_speed
    with col2:  # show service id table to select
        st.write("'Calendar.txt' for reference")
        with st.spinner('Loading table calendar.txt...'):
            table_util.show_static_table(GTFS_OBJ, 'calendar.txt')


def page_3_execute():
    global GTFS_OBJ, GRAPH_OBJ
    # start building the spatio-temporal network!
    # (5) a button to generate spatio-temporal network (nested buttons)
    if (st.button("Generate Transit Network over space and time!") or
            st.session_state["b3_1_clicked"]):
        st.session_state["b3_1_clicked"] = True
        print("network_config_info:", network_config_info)
        with st.spinner('Building transit network...'):
            GRAPH_OBJ, stops = build_network(
                network_config_info,
                GTFS_OBJ,
                GRAPH_OBJ,
            )

            # json_graph.node_link_data(GRAPH_OBJ.G)
            # nx.write_gpickle(GRAPH_OBJ.G, "temp_graph.pickle")

            st.session_state["GRAPH_OBJ"] = GRAPH_OBJ
            st.download_button(
                "Download network/graph in Python's pickle format!",
                data=pickle.dumps(GRAPH_OBJ.G),
                file_name='My_GTFS_Graph.pickle',
            )
        st.success('Network built successfully!')
        if "stops" not in st.session_state:
            st.session_state["stops"] = None
        st.session_state["stops"] = stops


init_page3()
# generate all stuff by running this function
if st.session_state["GTFS_OBJ"] is not None:
    page_3()  # draw basic layouts
    page_3_execute()

