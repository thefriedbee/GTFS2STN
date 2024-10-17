"""
Contains function to generate folium in the app
"""
import folium
from folium.plugins import MousePosition
from folium.plugins import Draw
from streamlit_folium import st_folium, folium_static

import pandas as pd
import geopandas as gpd

from script.gtfs_controller import GTFSController
import script.visualization.folium_plots as folium_plots
from script.GTFSGraph import GTFSGraph


def show_stops_map(
        GTFS_OBJ: GTFSController,
        w: int = 1000,
        h: int = 400,
        render_static=True,
        set_draw=False,
        show_popup=True
) -> None | dict:
    m = GTFS_OBJ.display_stops_map()
    formatter = "function(num) {return L.Util.formatNum(num, 3) + ' &deg; ';};"
    MousePosition(
        position="topright",
        separator=" | ",
        empty_string="NaN",
        lng_first=True,
        num_digits=20,
        prefix="Coordinates:",
        lat_formatter=formatter,
        lng_formatter=formatter,
    ).add_to(m)

    if set_draw:
        Draw(
            export=True,
            draw_options={
                'polyline': False,
                'rectangle': False,
                'polygon': False,
                'circle': False,
                'marker': False,
            },
        ).add_to(m)

    # render results in Streamlit
    if render_static:
        st_data = folium_static(m, width=w, height=h)
    else:
        st_data = st_folium(
            m, width=w, height=h,
            returned_objects=["last_object_clicked"],
            return_on_hover=False,
        )
    return st_data


def display_one_origin_map(
        stops: gpd.GeoDataFrame,
        GRAPH_OBJ: GTFSGraph,
        one_source_access_dict,
        one_source_path_dict,
) -> folium.Map:
    stops_acc = pd.DataFrame.from_dict(one_source_access_dict, orient='index')
    stops_acc = stops_acc.reset_index()
    stops_acc.columns = ["stop_id", "acc_time"]
    stops_pth = pd.DataFrame(pd.Series(one_source_path_dict))
    stops_pth = stops_pth.reset_index()
    stops_pth.columns = ["stop_id", "trajectory"]

    # merge info
    stops_acc = stops_acc.merge(stops_pth, on="stop_id", how="left")
    stops_acc["stop_id"] = stops_acc["stop_id"].str[:-2]
    print("stops_acc:")
    print(stops_acc.head(2))
    stops = stops[["stop_id", "stop_lat", "stop_lon", "stop_name", "stop_code"]]

    stops['stop_id'] = stops['stop_id'].astype("string")
    stops_acc['stop_id'] = stops_acc['stop_id'].astype("string")

    stops = stops.merge(stops_acc, on="stop_id", how="left")
    print("stops:")
    print(stops.head(2))
    # init map
    m = folium_plots.display_map_background(stops=stops)
    m = folium_plots.display_one_origin_info(
        stops_extended=stops,
        GRAPH_OBJ=GRAPH_OBJ,
        m=m,
    )
    return m
