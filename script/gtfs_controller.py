"""
This module creates an object that records
important path information of the interested GTFS
"""
import glob, os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import numpy as np

import streamlit as st
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
from streamlit_folium import st_folium, folium_static
import folium


class GTFSController:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.file_names = ["agency.txt", "stops.txt", "calendar.txt", "calendar_dates.txt",
                           "routes.txt", "shapes.txt", "stop_times.txt", "trips.txt"]
        self.dfs = {}  # hold all data here
        self.load_txt_files()
        self.shapes_gdf = self.process_shapes()
        self.route_shape = None

    def load_txt_files(self):
        # load txt files into memory
        for file in glob.glob(f"{self.root_dir}/*.txt"):
            fn = file.split('/')[-1]
            self.dfs[fn] = pd.read_csv(file)

    def process_shapes(self):
        df_shapes = self.dfs["shapes.txt"]

        # process list of coordinates to a LineString format
        def compact_shape(df):
            dst = df['shape_dist_traveled'].tolist()
            pts = [Point(loc) for loc in zip(df.shape_pt_lon.tolist(), df.shape_pt_lat.tolist())]
            if len(pts) == 1:
                print("one pts coords:", pts[0])
                # a dumb line with no length for corner cases
                coords = None
            else:
                coords = LineString(pts)
            return pd.Series([dst, coords])

        df_shapes = df_shapes.groupby(['shape_id']).apply(compact_shape)
        df_shapes.columns = ['dist_traveled', 'line']
        df_shapes = gpd.GeoDataFrame(df_shapes, geometry=df_shapes['line'])
        # print("df_shapes head:")
        # print(df_shapes.head(2))
        return df_shapes

    def display_table(self, fn, width, height):
        # TODO: set width and height
        if fn in self.dfs.keys():
            # display configuration
            gb = GridOptionsBuilder.from_dataframe(self.dfs[fn])
            gb.configure_pagination(paginationAutoPageSize=False,
                                    paginationPageSize=10)
            gb.configure_selection(selection_mode="disabled",
                                   use_checkbox=True)
            gridOptions = gb.build()
            return self.dfs[fn], gridOptions
            # add grid
            # AgGrid(self.dfs[fn], gridOptions=gridOptions)
        else:
            st.write("possible file names:", self.dfs.keys())
            return None

    def display_map_tile(self):
        # the most basic map to start with
        # let's use folium
        stops = self.dfs['stops.txt'][["stop_lat", "stop_lon"]]
        # create folium map
        m = folium.Map(location=[stops['stop_lat'].mean(), stops['stop_lon'].mean()], zoom_start=10)
        return m

    def display_stops_map(self, m=None, width=600, height=600):
        if m is None:
            m = self.display_map_tile()
        stops = self.dfs['stops.txt'][["stop_lat", "stop_lon", "stop_name", "stop_code", "stop_id"]]
        # add stops
        for coords in stops[["stop_lat", "stop_lon", "stop_name", "stop_code", "stop_id"]].values.tolist():
            # iframe = folium.IFrame(f"stop name: {coords[2]} <br> stop code: {coords[3]}")
            # tooltip = folium.Popup(iframe, min_width=50, max_width=300)
            folium.CircleMarker(
                coords[:2],
                tooltip=f"stop name: {coords[2]} <br> stop code: {coords[3]}",
                popup=f"stop id: {coords[4]}",
                radius=2,
                weight=5,
            ).add_to(m)
        return m


    def display_routes_map(self, m=None, width=400, height=400):
        if m is None:
            m = self.display_map_tile()
        # load routes and shapes
        # routes = self.dfs['routes.txt'][["route_id", "route_short_name", "route_long_name",
        #                                  "route_type", "route_color"]]
        lines = self.shapes_gdf['geometry']
        lines_id = self.shapes_gdf.index.tolist()
        # print("lines_id:", lines_id)
        # just plot the raw shape (without consider trips/routes) is fine
        for i, line in enumerate(lines):
            x, y = line.coords.xy
            x = x.tolist()
            y = y.tolist()
            line = list(zip(y, x))
            folium.PolyLine(line,
                            popup=lines_id[i],
                            tooltip=lines_id[i]).add_to(m)
        print("shapes printed!")
        st_data = folium_static(m, width=width, height=height)







