"""
Contains some simple Matplotlib plots to generate results...
"""
import os
import sys

import networkx as nx
import numpy as np
import pandas as pd
import geopandas as gpd
import contextily as cx

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

import script.util.df_utils as df_ut
import script.analysis.geo_analysis as gpd_ut


# generate a 2d plot use "df_st_1trip"
def time_space_plot_given_1trip(
        df_st: pd.DataFrame,
        ax: plt.Axes = None,
) -> plt.Axes:
    if ax is None:
        fig, ax = plt.subplots(1, 1)

    # convert str to time if it hasn't
    try:
        df_st["arrival_time"] = pd.to_datetime(
            "2000-01-01, " + df_st["arrival_time"],
        )
        df_st["departure_time"] = pd.to_datetime(
            "2000-01-01, " + df_st["departure_time"],
        )
    except Exception:
        # print("failed to convert to datetime")
        pass

    arrive_ts = pd.to_datetime(df_st["arrival_time"])
    depart_ts = pd.to_datetime(df_st["departure_time"])

    ax.plot(arrive_ts, df_st["shape_dist_traveled"], 'gx')
    ax.plot(depart_ts, df_st["shape_dist_traveled"], 'g+-')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_xlabel("time of the day")
    ax.set_ylabel("distance traveled")
    # TODO: use a second y axis to view stop names
    return ax


# get a set of trips given the block id
# plot time & space for every trip sharing one block (one operating vehicle)
def time_space_plot_given_1block(df_stop_times, df_trips, block_id):
    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    # get all trips by block id
    trips = df_ut.get_trips_given_block_id(df_trips, block_id)
    trip_ids = trips['trip_id'].tolist()
    for trip_id in trip_ids:
        df_st_1t = df_ut.get_info_given_trip_id(df_stop_times, trip_id)
        ax = time_space_plot_given_1trip(df_st_1t, ax)
    return ax


def plot_subgraph(G: nx.DiGraph):
    def get_pos(G, node):
        node = G.nodes[node]
        x, y, z = node['lon'], node['lat'], node['time']
        return x, y, z

    # Extract node and edge positions from the layout
    node_xyz = np.array([get_pos(G, v) for v in G.nodes()])
    edge_xyz = np.array([(get_pos(G, u), get_pos(G, v)) for u, v in G.edges()])
    print(node_xyz.shape)
    print(edge_xyz.shape)
    # Create the 3D figure
    fig = plt.figure(figsize=(15, 15))
    ax = fig.add_subplot(111, projection="3d")
    # Plot the nodes - alpha is scaled by "depth" automatically
    ax.scatter(node_xyz.T[0], node_xyz.T[1], node_xyz.T[2], s=100, ec="w")
    # Plot the edges
    for viz_edge in edge_xyz:
        ax.plot(*viz_edge.T, color="tab:gray")


def plot_isochrone_grid_plots(
        nodes_df: pd.DataFrame,
        stops_gdf: gpd.GeoDataFrame,
) -> plt.Axes:
    fig, axes = plt.subplots(2, 3, figsize=(30, 20), tight_layout=True, dpi=300)
    acc_times = [(i + 1) * 20 for i in range(6)]

    # prepare scope of visualization
    bds_minx = nodes_df['lon'].min()
    bds_maxx = nodes_df['lon'].max()
    bds_miny = nodes_df['lat'].min()
    bds_maxy = nodes_df['lat'].max()

    for I, acct in enumerate(acc_times):
        i, j = int(I / 3), I % 3
        print(i, j)
        _df = stops_gdf.loc[(stops_gdf["acc_time"] <= acct), :]
        _df.plot(legend=False, ax=axes[i, j], color="blue", markersize=5)
        axes[i, j].axis('off')
        axes[i, j].set_title(f"maximum travel time: {acct} minutes")
        axes[i, j].set_xlim(bds_minx, bds_maxx)
        axes[i, j].set_ylim(bds_miny, bds_maxy)

        cx.add_basemap(
            axes[i, j],
            source=cx.providers.OpenStreetMap.Mapnik,
            crs=stops_gdf.crs
        )
        _buff = gpd_ut.get_buffer_geom(stops_gdf, acc_times[I])[0]

        geoInterface = _buff.__geo_interface__
        shpType = geoInterface['type']
        print(shpType)
        if shpType == "Polygon":
            xs, ys = _buff.exterior.xy
            axes[i, j].fill(xs, ys, alpha=0.2, color="red")  # fc='r', ec='none',
        else:  # Multipolygon
            for geom in _buff.geoms:
                xs, ys = geom.exterior.xy
                axes[i, j].plot(xs, ys, color="red")

    plt.tight_layout()
    return plt.gca()


def plot_isochrone_combined_plot(
        acc_times: list[float],  # a list of departure/arrival time
        stops_gdf: gpd.GeoDataFrame,
        map_bounds: tuple[float, float, float, float],
) -> plt.Axes:
    # unload map bounds
    bds_minx, bds_maxx, bds_miny, bds_maxy = map_bounds
    # task: plot all 6 diagrams into one plot
    fig, ax = plt.subplots(
        1, 1, figsize=(10, 10),
        tight_layout=True, dpi=200
    )

    cmap = plt.cm.get_cmap('jet', 7)
    cmap_list = [cmap(i) for i in range(cmap.N)]
    legends = [f"accessible range in {(i + 1) * 20} minutes" for i in range(6)]

    tot_num_buffers = len(acc_times)
    for I, acct in enumerate(acc_times):
        print(I)
        _df = stops_gdf.loc[(stops_gdf["acc_time"] <= acct), :]
        _buff = gpd_ut.get_buffer_geom(stops_gdf, acc_times[I])[0]
        geo_interface = _buff.__geo_interface__
        shp_type = geo_interface['type']
        if shp_type == "Polygon":
            xs, ys = _buff.exterior.xy
            ax.fill(
                xs, ys, alpha=0.8,
                color=cmap_list[I], label=legends[I],
                zorder=tot_num_buffers - I
            )
        else:  # Multipolygon
            for geom in _buff.geoms:
                xs, ys = geom.exterior.xy
                ax.fill(
                    xs, ys, alpha=0.8,
                    color=cmap_list[I], label=legends[I],
                    zorder=tot_num_buffers - I
                )

    # just plot all stops at once
    stops_gdf.plot(
        legend=False, ax=ax, color="blue", markersize=5,
        zorder=tot_num_buffers,  # highest order
        label="bus stops"
    )
    ax.axis('off')
    # ax.set_title(f"maximum travel time: {acct} minutes")
    ax.set_xlim(bds_minx, bds_maxx)
    ax.set_ylim(bds_miny, bds_maxy)
    # drop pin for the starting point
    _df = stops_gdf.loc[(stops_gdf["acc_time"] <= 0.0), :]
    _df.plot(
        legend=False, ax=ax,
        marker='*', color='green', markersize=50,
        zorder=tot_num_buffers,  # highest order
        label="starting point"
    )

    cx.add_basemap(
        ax,
        source=cx.providers.OpenStreetMap.Mapnik,
        # crs=stops_gdf.crs
    )
    plt.tight_layout()
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())
    return ax


def get_stops_borders(
        stops_df: pd.DataFrame | gpd.GeoDataFrame
):
    bds_minx, bds_miny, bds_maxx, bds_maxy = stops_df["geometry"].total_bounds
    print("map bounds:", bds_minx, bds_maxx, bds_miny, bds_maxy)
    return bds_minx, bds_maxx, bds_miny, bds_maxy


# plot travel time reliability
def plot_travel_time_over_time(
        total_ts: np.array,
        walk_ts: np.array,
        wait_ts: np.array,
        min_start: int,
        min_end: int,
) -> plt.Axes:
    def format_tick_labels(x, pos):
        return f'{x/60:.0f}'

    fig, ax = plt.subplots(1, 1, figsize=(8, 2), dpi=300)
    x_times = np.arange(min_start, min_end, step=10)

    ax.fill_between(x_times, 0, walk_ts, alpha=0.5, label="walking time")
    ax.fill_between(x_times, walk_ts, walk_ts+wait_ts, alpha=0.5, label="waiting time")
    ax.fill_between(x_times, wait_ts+walk_ts, total_ts, alpha=0.5, label="transit time")
    ax.plot(x_times, total_ts, 'r-', label="Total travel time")
    ax.set_ylabel("Minutes")
    ax.set_xlabel("Hour of the day")

    ax.set_xticks(np.arange(min_start, min_end, step=60))
    ax.set_xlim(min_start-1, min_end+1)

    ax.xaxis.set_major_formatter(FuncFormatter(format_tick_labels))
    plt.legend()
    plt.grid()
    return ax

