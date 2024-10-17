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
import streamlit.components.v1 as components
import streamlit_mermaid as stmd
from PIL import Image
from script.basic_info import mermaid_text


def page_0_init():
    st.set_page_config(layout="wide", page_title="GTFS2STN", page_icon="🚌")
    global GTFS_OBJ, GRAPH_OBJ
    # create all global data holders
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]


# helper method
@st.cache_data(show_spinner=False)
def image_loader(pth):
    return Image.open(pth)


@st.cache_data(show_spinner=False)
def html_loader(pth):
    with open(pth) as f:
        file = f.read()
    return file


# everytime, this loading is the same...
def page_0():
    st.markdown("# Welcome to GTFS2STN: Convert transit GTFS data to spatiotemporal "
                "network for accessibility analysis")
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
        # image = image_loader('images/GTFS_introduction.png')
        # st.image(image,
        #          caption='The core relationship between GTFS tables \n '
        #                  '(source: https://github.com/tyleragreen/gtfs-schema)')
        stmd.st_mermaid(code=mermaid_text)
    st.markdown("## Introducing Spatio-temporal network: a directed diagram describing transit traffic")
    st.markdown("""
    Unlike traffic network, the edges are links are changing over time of the day.
    Thus, the spatio-temporal network is necessary for shortest paths analysis. For the problem below:
    - There are three routes (i.e., Route A, Route B, and Route C) in the transit system
    - Each route has a bus traveling back and force along the route
    - Thus, the spatio-temporal network can be drawn (see the 3-dimensional Figure on the right)
    - The grey vertical edges on the right Figure denote the choice of passengers waiting at the same bus stop
    """)
    # new columns
    col1, col2 = st.columns(2)
    with col1:
        components.html(html_loader("images/stops.html"), height=500)
    with col2:
        components.html(html_loader("images/tsn.html"), height=480)
    st.markdown("## GTFS2STN: Converting *any* GTFS data feeds to Spatio-temporal transit network")
    st.markdown("""
    In summary, similar to the above example, the project aims to generate a spatio-temporal directed diagram
    for shortest path analysis given any GTFS inputs.
    """)


page_0_init()
page_0()

