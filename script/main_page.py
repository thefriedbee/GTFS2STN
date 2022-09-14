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

st.set_page_config(layout="wide")
st.write("Introducing the tool")

# create all global data holders
st.session_state["GTFS_OBJ"] = None
st.session_state["GRAPH_OBJ"] = None


