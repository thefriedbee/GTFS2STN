import folium
import branca.colormap as cm

import pandas as pd
import geopandas as gpd
import numpy as np

from script.GTFSGraph import GTFSGraph
import script.analysis.geo_analysis as gpd_ut


def display_map_background(
        stops: pd.DataFrame | gpd.GeoDataFrame
) -> folium.Map:
    # just load the background...
    # create folium map. Furthermore, add scales also...
    m = folium.Map(
        location=[stops['stop_lat'].mean(), stops['stop_lon'].mean()],
        zoom_start=10,
        control_scale=True,
    )
    return m


def display_gtfs_stops(
        stops: pd.DataFrame,
        m: folium.Map,
        show_popup=True,
) -> folium.Map:
    # folium bus stops...
    for coords in stops[["stop_lat", "stop_lon", "stop_name", "stop_code", "stop_id"]].values.tolist():
        # iframe = folium.IFrame(f"stop name: {coords[2]} <br> stop code: {coords[3]}")
        # tooltip = folium.Popup(iframe, min_width=50, max_width=300)
        if show_popup:
            folium.CircleMarker(
                location=coords[:2],
                popup=folium.Popup(f"stop id: {coords[4]}", parse_html=False),
                tooltip=f"stop name: {coords[2]} <br> stop code: {coords[3]} <br> stop id: {coords[4]}",
                radius=2,
                weight=5,
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=coords[:2],
                tooltip=f"stop name: {coords[2]} <br> stop code: {coords[3]} <br> stop id: {coords[4]}",
                radius=2,
                weight=5,
            ).add_to(m)
    return m


def display_gtfs_lines(
        lines: pd.DataFrame,
        m: folium.Map
) -> folium.Map:
    # lines are the bus lines (routes)...
    line_ids = lines.index.tolist()
    for i, line in enumerate(lines):
        x, y = line.coords.xy
        x = x.tolist()
        y = y.tolist()
        line = list(zip(y, x))
        folium.PolyLine(
            line,
            popup=line_ids[i],
            tooltip=line_ids[i]
        ).add_to(m)
    return m


def display_one_origin_info(
        stops_extended: pd.DataFrame,
        GRAPH_OBJ: GTFSGraph,
        m: folium.Map,
) -> folium.Map:
    # prepare colormap between 0-120 minutes
    colormap = cm.LinearColormap(
        colors=['green', 'yellow', 'red'],
        vmin=0, vmax=120,
    )

    def get_color(v):
        try:
            return colormap(v)
        except Exception:
            return "#bbbbbb"

    for i, row_info in stops_extended[
        ["stop_id", "stop_lat", "stop_lon",
         "stop_name", "stop_code", "acc_time",
         "trajectory"]
    ].iterrows():
        # TODO: implement this later...
        if isinstance(row_info["trajectory"], float):
            wt_lst, tt_lst = [], []
        else:
            wt_lst, tt_lst = get_path_costs(GRAPH_OBJ, row_info["trajectory"])
        row_lst = row_info.values.tolist()
        popup_info = f"""
        stop_id: {row_info[0]} <br>
        travel time: {row_info[5]} <br>
        trajectory: {row_info[6]} <br>
        tt costs: {tt_lst} <br>
        """
        if row_lst[5] == -1.0:
            row_lst[5] = np.nan

        iframe = folium.IFrame(popup_info)
        popup = folium.Popup(
            iframe,
            min_width=500, max_width=800,
            min_height=100, max_height=500
        )
        folium.CircleMarker(
            row_lst[1:3],
            popup=popup,
            tooltip=f"travel time: {row_lst[5]:.2f} <br> stop id: {row_lst[0]}",
            radius=2,
            weight=5,
            color=get_color(row_lst[5]),
        ).add_to(m)
    m.add_child(colormap)
    return m


def get_path_costs(GRAPH_OBJ, nodes_lst):
    # print("node_lst:", nodes_lst)
    if len(nodes_lst) == 0:
        return np.nan, np.nan
    wt_lst, tt_lst = [], []
    for i in range(len(nodes_lst) - 1):
        node_i = nodes_lst[i]
        node_j = nodes_lst[i + 1]
        edge = GRAPH_OBJ.G.edges[node_i, node_j]
        wt_lst += [round(float(edge['wt']), 2)]  # waiting time
        tt_lst += [round(float(edge['tt']), 2)]  # travel time
    return wt_lst, tt_lst


# task: given one stop, visualize the neighboring stops
def display_stops2(stops):
    stops = stops[["stop_id", "stop_lat", "stop_lon", "stop_name", "stop_code"]]
    m = folium.Map(
        location=[stops['stop_lat'].mean(),
                  stops['stop_lon'].mean()],
        zoom_start=10
    )

    # create colormaps
    colormap = cm.LinearColormap(
        colors=['green', 'yellow', 'red'],
        vmin=0, vmax=120
    )

    # add stops
    for i, row_info in stops[
        ["stop_id", "stop_lat", "stop_lon",
         "stop_name", "stop_code"]
    ].iterrows():
        row_lst = row_info.values.tolist()

        folium.CircleMarker(
            row_lst[1:3],
            popup=row_lst[0],
            tooltip=row_lst[3],
            radius=2,
            weight=5,
            color="red",
        ).add_to(m)
    m.add_child(colormap)
    return m


def plot_isochrone_combined_plot(
        acc_times: list[float],  # a list of departure/arrival time
        stops_gdf: gpd.GeoDataFrame,
        show_popup=True,
) -> folium.Map:
    # convert the projection system to epsg:4326
    stops_gdf = stops_gdf.to_crs("epsg:4326")
    buffers = get_buffers(stops_gdf, acc_times)
    num_buffers = len(buffers)

    cmap_lst = cm.LinearColormap(
        ["green", "yellow", "red"],
        vmin=0,
        vmax=acc_times[-1]
    ).to_step(num_buffers)
    print(num_buffers)
    print(cmap_lst)

    # let's show the stops in the first place...
    m = display_map_background(stops_gdf)
    # plot buffers

    for i in reversed(range(num_buffers)):
        print(i, cmap_lst(acc_times[i]))
        buff = buffers[[i]].to_json()
        folium.GeoJson(
            data=buff,
            style_function=lambda x, i=i: {
                "fillColor": cmap_lst(acc_times[i]),
                "color": cmap_lst(acc_times[i]),
                "fillOpacity": 0.4,
            },
        ).add_to(m)
    # plot stations
    m = display_gtfs_stops(stops_gdf, m, show_popup=show_popup)
    cmap_lst.add_to(m)
    return m


def get_buffers(stops_gdf, acc_times):
    # get buffers
    buffers = []
    for I, acct in enumerate(acc_times):
        _df = stops_gdf.loc[(stops_gdf["acc_time"] <= acct), :]
        _buff = gpd_ut.get_buffer_geom(stops_gdf, acc_times[I])[0]
        buffers.append(_buff)
    # change to GeoPandas type
    buffers = gpd.GeoSeries(
        buffers,
        name="geometry"
    )
    return buffers

