"""
# Transit accessibility analyzer and comparator
1. Step 1. upload and process raw GTFS data
2. Basic viewers (for 'facilities' routes, stations, lines, etc.)
    Left: table (list of stations/routes); select time; Right: map
    Bottom: histograms (changes over time)
    (1) Plot distribution of stations
    (2) For each route, generate stations with time table involved.
3. Grid analysis (generate network grids)
    (1) For each selected grid, the number of bus visits the grid over time
    (2) Given the starting grid, accessibility from the grid to other grids
"""

import streamlit as st
from PIL import Image


def page_0_init():
    st.set_page_config(layout="wide")
    global GTFS_OBJ, GRAPH_OBJ
    # create all global data holders
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]


def page_0():
    st.markdown("# Welcome to TSNG: Transit Spatio-temporal Network Generator")
    st.markdown("## Introducing GTFS: General Transit Feed Specification")

    # use two columns for page layout
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
         > "The General Transit Feed Specification (GTFS) is a data specification that allows
         > public transit agencies to publish their transit data in a format that can be consumed by
         > a wide variety of software applications. Today, the GTFS data format is used 
         > by thousands of public transport providers."
         >
         > -- https://gtfs.org/
        """)
    with col2:
        image = Image.open('images/GTFS_introduction.png')
        st.image(image,
                 caption='The core relationship between GTFS tables')
    st.markdown("## Introducing Spatio-temporal network: a directed diagram describing transit traffic")

    st.markdown("## TSNG: Generating Spatio-temporal transit network given *any* GTFS inputs")


page_0_init()
page_0()

