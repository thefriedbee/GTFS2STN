"""
Analyze Travel Time Reliability between an OD pair
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import streamlit as st

import script.util.map_viewer as map_ut
import script.util.df_utils as df_ut
import script.visualization.folium_plots as folium_plots
import script.visualization.mpl_plots as mpl_plots
import script.analysis.geo_analysis as geo_analysis


st.set_page_config(layout="wide", page_title="GTFS2STN", page_icon="🚌")
if "b5_1_clicked" not in st.session_state.keys():
    st.session_state["b5_1_clicked"] = False
if "stop_id" not in st.session_state.keys():
    st.session_state["stop_id"] = ""

if "orig_coords" not in st.session_state.keys():
    st.session_state["orig_coords"] = ""
if "dest_coords" not in st.session_state.keys():
    st.session_state["dest_coords"] = ""


def page5_init():
    global GTFS_OBJ, GRAPH_OBJ
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    GRAPH_OBJ = st.session_state["GRAPH_OBJ"]
    print(f"step4 GTFS_OBJ: {GTFS_OBJ}")
    print(f"step4 GRAPH_OBJ: {GRAPH_OBJ}")
    if "stops" not in st.session_state:
        st.session_state["stops"] = None


def page_5() -> tuple[gpd.GeoDataFrame, str, str, tuple[int, int], float, str]:
    stops = st.session_state["stops"]
    # stops need to be filtered for the schedule...
    st.title("Step 5. Query travel time variation of the day")
    col1, col2 = st.columns([1, 3])

    with col2:
        st.write("map reference of stops")
        with st.spinner('Loading map...'):
            st_data = map_ut.show_stops_map(
                GTFS_OBJ,
                render_static=False,
                set_draw=False,
                show_popup=True,
            )
    with col1:
        # get last active drawing
        def get_last_active_drawing(st_data):
            ret_coords = st_data["last_object_clicked"]
            return ret_coords

        print('st.session_state["orig_coords"]', st.session_state["orig_coords"])
        print('st.session_state["dest_coords"]', st.session_state["dest_coords"])

        is_origin_fixed = st.checkbox("freeze origin")
        placeholder_orig = st.empty()
        stop_orig_coords = placeholder_orig.text_input("enter origin coordinate (can click on map)")
        if is_origin_fixed and st.session_state["orig_coords"] is not None:
            stop_orig_coords = placeholder_orig.text_input(
                "enter origin coordinate (can click on map)",
                value=st.session_state["orig_coords"],
            )
        elif is_origin_fixed:
            pass
        elif st_data is not None:
            stop_orig_coords = placeholder_orig.text_input(
                "enter origin coordinate (can click on map)",
                value=get_last_active_drawing(st_data),
            )
            st.session_state["orig_coords"] = stop_orig_coords

        is_dest_fixed = st.checkbox("freeze destination")
        placeholder_dest = st.empty()
        stop_dest_coords = placeholder_dest.text_input("enter destination coordinate (can click on map)")
        if is_dest_fixed and st.session_state["dest_coords"] is not None:
            stop_dest_coords = placeholder_dest.text_input(
                "enter destination coordinate (can click on map1)",
                value=st.session_state["dest_coords"],
            )
        elif is_dest_fixed:
            pass
        elif st_data is not None:
            stop_dest_coords = placeholder_dest.text_input(
                "enter destination coordinate (can click on map2)",
                value=get_last_active_drawing(st_data),
            )
            st.session_state["dest_coords"] = stop_dest_coords

        # time scope
        depart_time_range = st.slider(
            "Select departure time range during the day (in hours)",
            0, 23, (7, 10)
        )

        # TODO: select walking radius
        walk_dist = st.slider(
            "walking distance (in miles)",
            0.1, 3.0, .5, 0.2,
        )

        # select multiple origin or multiple destinations
        run_mode = st.radio(
            "Available mode for running the Dijkstra's algorithm:",
            [
                "1 source, 1 destination",
                "1 source, 1+ destination",
                "1+ source, 1 destination",
                "1+ source, 1+ destination"
            ]
        )

    return stops, stop_orig_coords, stop_dest_coords, depart_time_range, walk_dist, run_mode


def page_5_find_stops_given_coords(
        stops: gpd.GeoDataFrame,
        stop_orig_coords: str,
        stop_dest_coords: str,
        walk_dist: float,
        run_code: int,
):
    # parse str returns
    stop_orig_coords = stop_orig_coords.replace("\'", "\"")
    stop_dest_coords = stop_dest_coords.replace("\'", "\"")
    stop_orig_coords = json.loads(stop_orig_coords)
    stop_dest_coords = json.loads(stop_dest_coords)
    stop_orig_coords = [(stop_orig_coords["lat"], stop_orig_coords["lng"])]
    stop_dest_coords = [(stop_dest_coords["lat"], stop_dest_coords["lng"])]

    print("stop_orig_coords:", stop_orig_coords)
    print("stop_dest_coords:", stop_dest_coords)

    # find all available stops within 0.25 mile buffer
    return_all_origs = True
    if run_code != 2:
        return_all_origs = False
    stop_orig_ids, stop_orig_dists = geo_analysis.find_nei_stops_given_coords(
        stops,
        stop_orig_coords,
        bw_mile=walk_dist,
        return_all_neighbors=return_all_origs
    )

    return_all_dests = True
    if run_code != 1:
        return_all_dests = False
    stop_dest_ids, stop_dest_dists = geo_analysis.find_nei_stops_given_coords(
        stops,
        stop_dest_coords,
        bw_mile=walk_dist,
        return_all_neighbors=return_all_dests
    )
    return stop_orig_ids, stop_dest_ids


def page_5_od_reliability(
        stops: gpd.GeoDataFrame,
        stop_orig_coords: str,
        stop_dest_coords: str,
        depart_time_range: tuple[int, int],
        walk_dist: float,
        run_mode: str,
):
    # decode run mode
    run_code = -1
    if run_mode == "1 source, 1 destination":
        run_code = 0
    elif run_mode == "1 source, 1+ destination":
        run_code = 1
    elif run_mode == "1+ source, 1 destination":
        run_code = 2
    elif run_mode == "1+ source, 1+ destination":
        run_code = 3

    st.title("Generate travel variability between od over time")

    if (
            st.button("Start Analysis & plot results") or
            st.session_state.b5_1_clicked
    ):
        st.session_state["b5_1_clicked"] = True
        # decode coordinates to nearest bus stops within walking distance
        stop_orig_ids, stop_dest_ids = page_5_find_stops_given_coords(
            stops=stops,
            stop_orig_coords=stop_orig_coords,
            stop_dest_coords=stop_dest_coords,
            walk_dist=walk_dist,
            run_code=run_code,
        )
        st.text_input("closest transit station near the origin coordinates:", stop_orig_ids)
        st.text_input("closest transit station near the destination coordinates:", stop_dest_ids)

        transit_ts_min, wait_ts_min, walk_ts_min, total_ts_min = [], [], [], []
        hour_start, hour_end = depart_time_range
        min_start, min_end = hour_start * 60, hour_end * 60 + 1
        for depart_min in np.arange(min_start, min_end, step=10):  # step is every 10 minutes
            print("run code:", run_code)
            if run_code == 0:
                pth = GRAPH_OBJ.query_od_stops_time(
                    stop_orig_id=stop_orig_ids[0],
                    stop_dest_id=stop_dest_ids[0],
                    depart_min=depart_min,  # e.g., departure at 8 AM
                )
                all_paths = [pth]
            elif run_code == 1:
                all_paths = GRAPH_OBJ.query_od_stops_time_multiple_dest(
                    stop_orig_id=stop_orig_ids[0],
                    stop_dest_ids=stop_dest_ids,
                    depart_min=depart_min,
                )
            elif run_code == 2:
                all_paths = GRAPH_OBJ.query_od_stops_time_multiple_orig(
                    stop_orig_ids=stop_orig_ids,
                    stop_dest_id=stop_dest_ids[0],
                    depart_min=depart_min,
                )
            elif run_code == 3:
                all_paths = GRAPH_OBJ.query_od_stops_time_multiple_ods(
                    stop_orig_ids=stop_orig_ids,
                    stop_dest_id=stop_dest_ids,
                    depart_min=depart_min,
                )
            else:
                raise ValueError(f"run code {run_code} not recognized")

            travel_ts = []
            wait_ts, walk_ts, total_ts = [], [], []

            print("all_paths:", all_paths)
            for pth in all_paths:
                print("pth", pth)
                transit_t, wait_t, walk_t = GRAPH_OBJ.get_travel_time_info_from_pth(
                    GRAPH_OBJ.G,
                    pth,
                )
                tt = transit_t + wait_t + walk_t
                travel_ts.append(transit_t)
                wait_ts.append(wait_t)
                walk_ts.append(walk_t)
                total_ts.append(tt)

            def argmin(lst):
                return lst.index(min(lst))

            path_index = argmin(total_ts)

            transit_ts_min.append(travel_ts[path_index])
            wait_ts_min.append(wait_ts[path_index])
            walk_ts_min.append(walk_ts[path_index])
            total_ts_min.append(total_ts[path_index])

        print("total_ts_min", total_ts_min)
        wait_ts_min = np.array(wait_ts_min)
        walk_ts_min = np.array(walk_ts_min)
        transit_ts_min = np.array(transit_ts_min)
        total_ts_min = np.array(total_ts_min)

        ax = mpl_plots.plot_travel_time_over_time(
            total_ts=total_ts_min,
            wait_ts=wait_ts_min,
            walk_ts=walk_ts_min,
            min_start=min_start,
            min_end=min_end,
        )
        st.pyplot(plt.gcf())


page5_init()
if GTFS_OBJ is not None and GRAPH_OBJ is not None:
    stops, stop_orig_coords, stop_dest_coords, depart_time_range, walk_dist, run_mode = page_5()
    page_5_od_reliability(
        stops, stop_orig_coords, stop_dest_coords,
        depart_time_range, walk_dist, run_mode
    )

    # m = None
    # if m is not None:
    #     folium_static(m, width=700, height=500)
