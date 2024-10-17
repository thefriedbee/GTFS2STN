"""
Build spatio-temporal network based on needs
"""
import json
import streamlit as st

import script.graph_pipeline as graph_pipeline
from script.GTFSGraph import GTFSGraph
from script.gtfs_controller import (
    build_network,
    filter_service_id_by_date
)

from script.util.table_viewer import show_static_table, show_static_table_simple
import rustworkx as rx

st.set_page_config(
    layout="wide",
    page_title="GTFS2STN",
    page_icon="🚌"
)
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
    # # status check
    # if GTFS_OBJ is None:
    #     pass
    # init button states the first time
    if "b3_1_clicked" not in st.session_state.keys():
        st.session_state["b3_1_clicked"] = False


def page_3():
    st.title("Step 3. Build transit network")
    col1, col2 = st.columns([1, 4])
    with col1:
        # part (2): choose a specific date for analysis
        the_date = st.date_input("the date to evaluate", value=None)

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
        network_config_info["date"] = the_date
        network_config_info["bw_mile"] = bw_mile
        network_config_info["walk_speed"] = walk_speed
    with col2:  # show service id table to select
        st.write("'Calendar.txt' for reference")
        with st.spinner('Loading table calendar.txt...'):
            show_static_table_simple(GTFS_OBJ, 'calendar.txt')


def page_3_execute():
    # start building the spatio-temporal network!
    # (5) a button to generate spatio-temporal network (nested buttons)
    if (st.button("Generate Transit Network over space and time!") or
            st.session_state["b3_1_clicked"]):
        # unload parameters
        the_date = network_config_info["date"]
        if the_date is None:
            st.error("should fill a date for analysis...")

        # filter the data set...
        services = GTFS_OBJ.dfs["calendar.txt"].copy()
        services = filter_service_id_by_date(
            services=services,
            the_date=the_date
        )
        # selected service ids
        sel_sids = services["service_id"].tolist()
        print(f"selected service ids {sel_sids}")
        network_config_info["service_id"] = sel_sids
        st.session_state["b3_1_clicked"] = True
        print("network_config_info:", network_config_info)

        with st.spinner(f'Building transit network for the date {the_date}...'):
            GRAPH_OBJ = st.session_state["GRAPH_OBJ"]
            GRAPH_OBJ, stops = build_network(network_config_info, GTFS_OBJ, GRAPH_OBJ)
            st.session_state["GRAPH_OBJ"] = GRAPH_OBJ
            st.download_button(
                "Download network in JSON format!",
                data=json.dumps(rx.node_link_json(GRAPH_OBJ.G)),
                file_name='My_GTFS_Graph.json'
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
