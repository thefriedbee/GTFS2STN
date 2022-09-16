import sys
import numpy as np
import os
import time
import streamlit as st
import pandas as pd

# from step1_choose_gtfs_document import AGENCIES, GTFS_OBJ
sys.path.append("..")
import script.gtfs_graph
from script.gtfs_graph import GTFS_Graph
import script.utils as ut

st.set_page_config(layout="wide", page_title="GTFS2STN", page_icon="🚌")

def page_2_init():
    global GTFS_OBJ
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    print("step2 GTFS_OBJ:", GTFS_OBJ)


def page_2_2():
    st.write("Step 2. Table interative analyzer")
    # ["agency.txt", "stops.txt", "calendar.txt", "calendar_dates.txt",
    #  "routes.txt", "shapes.txt", "stop_times.txt", "trips.txt"]
    all_tabs = st.tabs(GTFS_OBJ.file_names)  # one tab for each table
    # provide designated visualization for each type of table
    with all_tabs[0]:  # agency
        try:
            ut.show_static_table(GTFS_OBJ, 'agency.txt', w=1000)
        except:
            st.subheader("'agency.txt' are not found!!")

    with all_tabs[1]:  # stops
        col1, col2 = st.columns(2)
        with col1:
            if st.checkbox("display table", key="stops_table"):
                ut.show_stops_table(GTFS_OBJ)
        with col2:
            if st.checkbox("display map", key="stops_map"):
                ut.show_stops_map(GTFS_OBJ)

    with all_tabs[2]:  # calendar
        ut.show_static_table(GTFS_OBJ, 'calendar.txt', w=1000)

    with all_tabs[3]:  # calendar dates
        try:
            ut.show_static_table(GTFS_OBJ, 'calendar_dates.txt', w=1000)
        except:
            st.subheader("'calendar_dates.txt' are not found!")

    with all_tabs[4]:  # routes
        try:
            ut.show_static_table(GTFS_OBJ, 'routes.txt', w=1000)
        except:
            st.subheader("'routes.txt' are not found!")

    with all_tabs[5]:  # shapes
        # try:
        col1, col2 = st.columns(2)
        with col1:
            if st.checkbox("display table", key="shapes_table"):
                ut.show_static_table(GTFS_OBJ, 'shapes.txt')
        with col2:
            if st.checkbox("display map", key="shapes_map"):
                GTFS_OBJ.display_routes_map()
        # except:
        #     st.subheader("'shapes.txt' are not found!")

    with all_tabs[6]:  # stop_times
        try:
            ut.show_static_table(GTFS_OBJ, 'stop_times.txt', w=1000)
        except:
            st.subheader("'stop_times.txt' are not found!")

    with all_tabs[7]:  # trips
        try:
            ut.show_static_table(GTFS_OBJ, 'trips.txt', w=1000)
        except:
            st.subheader("'trip.txt' are not found!")


page_2_init()
page_2_2()

