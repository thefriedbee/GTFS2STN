"""
Start from one origin to all destinations
"""
import folium
import numpy as np
import geopandas as gpd
import streamlit as st

from streamlit_folium import st_folium, folium_static

import script.util.map_viewer as map_ut
import script.util.df_utils as df_ut
import script.visualization.folium_plots as folium_plots

import script.graph_pipeline as graph_pipeline
from script.GTFSGraph import GTFSGraph
from script.gtfs_controller import GTFSController

st.set_page_config(
    layout="wide",
    page_title="GTFS2STN",
    page_icon="🚌"
)

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


def page_4() -> tuple[gpd.GeoDataFrame, str, float, int]:
    stops = st.session_state["stops"]
    print("step 4 stops length:", len(stops))
    # stops need to be filtered for the schedule...
    st.title("Step 4. Query shortest travel scheme from one origin at different time of the day")
    col1, col2 = st.columns([1, 3])
    with col1:
        stop_id = st.text_input("choose stop id")
        depart_hr = st.slider(
            "Departure time (hour of a day)",
            0, 23, 8, 1
        )
        max_tt = st.slider(
            "Select maximum travel time (cutoff of the Dijkstra's algorithm)",
            0, 180, 120, 15
        )
    with col2:
        # plot map for reference...
        st.write("map reference of stops")
        with st.spinner('Loading map...'):
            m = map_ut.show_stops_map(GTFS_OBJ, w=800, h=300)
    return stops, stop_id, depart_hr, max_tt


def page_4_execute(
        stops: gpd.GeoDataFrame,
        stop_id: str,
        depart_hr: float,
        max_tt: int
) -> folium.Map:
    m = None

    st.title("Generate Isochrone plot (accessibility from a single source)")
    # start building network and query the shortest path
    if (st.button("Start analysis & plot results") or
            st.session_state.b4_1_clicked and
            stop_id != ""
    ):  # if stop_id != "", no inputs, just enter the page
        st.session_state["b4_1_clicked"] = True
        st.session_state["stop_id"] = stop_id

        for key in GRAPH_OBJ.nodes_time_map:
            if not isinstance(key, str):
                stop_id = int(stop_id)
            break

        my_bar = st.progress(
            0,
            text='Analyzing shortest travel time to other stops...'
        )

        print(f"stop id: {stop_id}, type: {type(stop_id)}")
        # find the shortest paths from stop_id
        one_source_paths, one_source_dists = GRAPH_OBJ.query_origin_stop_time(
            stops_df=stops,
            stop_id=stop_id,
            depart_min=60 * depart_hr,
            # cutoff=max_tt,
        )
        print("one_source_paths len:", len(one_source_paths))
        print("one_source_dists len:", len(one_source_dists))
        my_bar.progress(70)

        stops["node_id"] = stops["stop_id"].apply(
            lambda x: GRAPH_OBJ.nodes_name_map[f"{x}_D"])
        stops_gdf = df_ut.display_stops_one_source(stops, one_source_dists)
        stops_gdf = stops_gdf.to_crs(epsg=3857)
        print("stops_gdf shape:", stops_gdf.shape)

        # acc_times = [(i+1)*20 for i in range(6)]
        acc_times = np.arange(10, max_tt, 10).tolist()
        m = folium_plots.plot_isochrone_combined_plot(acc_times, stops_gdf)

        my_bar.progress(100)
    return m


def page_4_od_reliability():
    st.title("Generate travel variability between od over time")
    pass


page4_init()

if GTFS_OBJ is not None and GRAPH_OBJ is not None:
    stops, stop_id, depart_hr, max_tt = page_4()
    m = page_4_execute(stops, stop_id, depart_hr, max_tt)
    if m is not None:
        folium_static(m, width=700, height=500)
