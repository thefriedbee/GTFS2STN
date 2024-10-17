"""
This module creates an object that records
important path information of the interested GTFS
"""
from functools import reduce
import datetime
import glob
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString

import streamlit as st
from st_aggrid.grid_options_builder import GridOptionsBuilder
from streamlit_folium import st_folium, folium_static

import folium
import script.visualization.folium_plots as folium_plots

import script.graph_pipeline as gtfs_pipeline
from script.GTFSGraph import GTFSGraph
import script.analysis.graph_analysis as graph_analysis


class GTFSController:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.file_names = ["agency.txt", "stops.txt", "calendar.txt", "calendar_dates.txt",
                           "routes.txt", "shapes.txt", "stop_times.txt", "trips.txt"]
        self.dfs = {}  # hold all data here
        self.load_txt_files()
        self.shapes_gdf = self.process_shapes()

    def load_txt_files(self):
        # load txt files into memory
        for file in glob.glob(f"{self.root_dir}/*.txt"):
            fn = file.split('/')[-1]
            self.dfs[fn] = pd.read_csv(file)

        # change stops ids to string
        stops = self.dfs["stops.txt"]
        stops["stop_id"] = stops["stop_id"].astype(str)
        # change stop ids for stop_times
        stop_times = self.dfs["stop_times.txt"]
        stop_times["stop_id"] = stop_times["stop_id"].astype(str)
        # set calendar type
        cal = self.dfs["calendar.txt"]
        cal["start_date"] = cal["start_date"].astype(str)
        cal["end_date"] = cal["end_date"].astype(str)

    def process_shapes(self):
        df_shapes = self.dfs["shapes.txt"]

        # process list of coordinates to a LineString format
        def compact_shape(df):
            dst = df['shape_dist_traveled'].tolist()
            pts = [Point(loc) for loc in zip(df.shape_pt_lon.tolist(), 
                                             df.shape_pt_lat.tolist())]
            if len(pts) == 1:
                # a dumb line with no length for corner cases
                print("one pts coords:", pts[0])
                coords = None
            else:
                coords = LineString(pts)
            return pd.Series([dst, coords])

        df_shapes = df_shapes.groupby(['shape_id']).apply(compact_shape)
        df_shapes.columns = ['dist_traveled', 'line']
        df_shapes = gpd.GeoDataFrame(df_shapes, geometry=df_shapes['line'])
        return df_shapes

    def display_table(self, fn):
        # TODO: set width and height
        if fn in self.dfs.keys():
            # display configuration
            gb = GridOptionsBuilder.from_dataframe(self.dfs[fn])
            gb.configure_pagination(
                paginationAutoPageSize=False,
                paginationPageSize=10
            )
            gb.configure_selection(
                selection_mode="disabled",
                use_checkbox=True
            )
            gridOptions = gb.build()
            return self.dfs[fn], gridOptions
        else:
            st.write("possible file names:", self.dfs.keys())
            return None

    def display_map_tile(self, show_popup=True) -> folium.Map:
        # the most basic map to start with
        # let's use folium
        stops = self.dfs['stops.txt'][["stop_lat", "stop_lon", "stop_name", "stop_code", "stop_id"]]
        # add stops to map
        m = folium_plots.display_map_background(stops)
        m = folium_plots.display_gtfs_stops(stops, m, show_popup=show_popup)
        return m

    def display_stops_map(self, show_popup=True) -> folium.Map:
        stops = self.dfs['stops.txt'][["stop_lat", "stop_lon", "stop_name", "stop_code", "stop_id"]]
        # add stops to map
        m = folium_plots.display_map_background(stops)
        m = folium_plots.display_gtfs_stops(stops, m, show_popup=show_popup)
        return m

    def display_routes_map(self, m=None, width=400, height=400):
        # load routes and shapes
        # routes = self.dfs['routes.txt'][["route_id", "route_short_name", "route_long_name",
        #                                  "route_type", "route_color"]]
        lines = self.shapes_gdf['geometry']
        stops = self.dfs['stops.txt'][["stop_lat", "stop_lon", "stop_name", "stop_code", "stop_id"]]
        if m is None:
            m = folium_plots.display_map_background(stops=stops)
        m = folium_plots.display_gtfs_lines(lines, m)
        folium_static(m, width=width, height=height)


# given configurations, build network
def build_network(
        network_config_info,
        GTFS_OBJ: GTFSController,
        GRAPH_OBJ: GTFSGraph,
) -> None | tuple[GTFSGraph, pd.DataFrame]:
    if len(network_config_info) == 0:
        return None

    # load configuration variables
    service_ids = network_config_info["service_id"]
    bw_mile = network_config_info["bw_mile"]
    walk_speed = network_config_info["walk_speed"]

    # filter stop_times dataframe based on service ids
    trips_subset = filter_trips_by_service_ids(GTFS_OBJ, service_ids)
    trips_ids = trips_subset["trip_id"].tolist()
    stop_times = filter_stop_times_by_trip_ids(GTFS_OBJ, trips_ids)

    # filter the stops that is used in "stop_times" get stops information
    stop_ids = list(set(stop_times["stop_id"].to_list()))
    stops = filter_stops_by_stop_ids(GTFS_OBJ, stop_ids)
    stops = graph_analysis.find_stops_neighbors_within_buffer(stops, bw_mile=bw_mile)

    # build spatio-temporal networks
    gtfs_pipeline.add_nodes_all_stops(stops, GRAPH_OBJ, t_step=1440)
    gtfs_pipeline.add_edges_all_stop_times(stop_times, GRAPH_OBJ)  # actual transit trips
    GRAPH_OBJ.add_edges_walkable_stops(stops, walk_speed=walk_speed)  # transfer between stops
    GRAPH_OBJ.add_edges_within_same_stops()  # add edges within the same stop
    GRAPH_OBJ.add_hyper_nodes()  # add destination nodes

    # print information
    print("num. of nodes:", len(GRAPH_OBJ.G.nodes()))
    print("num. of edges:", len(GRAPH_OBJ.G.edges()))
    return GRAPH_OBJ, stops


# -----------Below are some filter methods for data query-----------
# get subset trips given service ids
def filter_trips_by_service_ids(
        GTFS_OBJ: GTFSController,
        service_ids: list[int],
) -> pd.DataFrame:
    trips = GTFS_OBJ.dfs["trips.txt"]
    filt = trips["service_id"].isin(service_ids)
    trips_subset = trips[filt]  # ["trip_id"].tolist()
    return trips_subset


def filter_stop_times_by_trip_ids(
        GTFS_OBJ: GTFSController,
        trip_ids: list[int],
) -> pd.DataFrame:
    stop_times = GTFS_OBJ.dfs["stop_times.txt"]
    filt = stop_times["trip_id"].isin(trip_ids)
    stop_times_subset = stop_times[filt]
    return stop_times_subset


def filter_stops_by_stop_ids(
        GTFS_OBJ: GTFSController,
        stop_ids: list[int],
) -> pd.DataFrame:
    print("num of stop ids: ", len(stop_ids))
    stops = GTFS_OBJ.dfs["stops.txt"]
    filt = stops["stop_id"].isin(stop_ids)
    print("filt sum:", filt.sum())
    # only keep filtered stops...
    GTFS_OBJ.dfs["stops.txt"] = stops[filt]
    return GTFS_OBJ.dfs["stops.txt"]


def filt_service_id_by_weekday(
        services: pd.DataFrame,
        sel_weekday: str,  # selected weekdays
):
    # services = GTFS_OBJ.dfs["calendar.txt"]
    dfs = []
    filt = (services[sel_weekday] == 1)
    return filt


def filter_service_id_by_date(
    services: pd.DataFrame,
    the_date: datetime.datetime | None,
) -> pd.DataFrame:
    WEEKDAYS = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
        5: "saturday",
        6: "sunday"
    }
    the_date = pd.to_datetime(the_date)
    the_weekday = WEEKDAYS[the_date.weekday()]

    services["start_date"] = pd.to_datetime(
        services["start_date"], format="%Y%m%d"
    )
    services["end_date"] = pd.to_datetime(
        services["end_date"], format="%Y%m%d"
    )

    filts = []
    # the queried time range is totally covered by the time range...
    if the_date is not None:
        filts += [services["start_date"] <= the_date]
        filts += [services["end_date"] >= the_date]
        # also, filter by weekday...
        filts += [filt_service_id_by_weekday(services, the_weekday)]
    else:
        st.error(f"{the_date} is not a valid date for analysis")
    # get weekday also...

    concat_and = lambda x, y: x & y
    filt = reduce(concat_and, filts)

    print("the date for analysis:", the_date)
    print("filts")
    print(filts[0].sum())
    print(filts[1].sum())
    print(filt.sum())

    if filt.sum() == 0:
        st.error("no feasible services for that date found.")

    return services.loc[filt, :]

