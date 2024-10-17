"""
Contains analysis methods using networkx module
"""
import sys

import numpy as np
import rustworkx as rx
import geopandas as gpd
import pandas as pd
# from scipy.spatial import cKDTree
from sklearn.neighbors import BallTree

import script.gtfs_controller as gtfs


# when building network, each stop needs to know its neighboring stops
# within walking distance, compute nearest points for each stop
def find_stops_neighbors_within_buffer(
        stops: pd.DataFrame,
        bw_mile: float = 0.5,
):
    # convert to GeoPandas
    stops = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat)
    )
    # set projection (Mercator projection system for web service)
    stops = stops.set_crs('epsg:4326')
    stops = stops.to_crs('epsg:3857')

    # set up indices
    bt = BallTree(
        np.deg2rad(stops[['stop_lat', 'stop_lon']].values),
        metric='haversine'
    )
    # for each row's (lat, lon), query neighbors
    neighbors, dists = [], []
    for i, row in stops.iterrows():
        indices, distances = bt.query_radius(
            np.deg2rad(np.c_[row['stop_lat'], row['stop_lon']]),
            r=bw_mile / 3959.8,  # mile
            return_distance=True
        )
        neighbors.append(indices[0])
        # convert distance from rad to miles
        dists.append(distances[0] * 3959.8)

    stops['neighbors'] = neighbors
    stops['dists'] = dists
    return stops


def get_memory_usage(graph: rx.PyDiGraph):
    edge_mem = sum([sys.getsizeof(e) for e in graph.edges()])
    node_mem = sum([sys.getsizeof(n) for n in graph.nodes()])

    print("Edge memory (MB):", edge_mem / 1024 / 1024)
    print("Node memory (MB):", node_mem / 1024 / 1024)
    print("Total memory (MB):", (edge_mem + node_mem) / 1024 / 1024)


# --------- Below are functions processing spatiotemporal diagram ---------
# view all nodes contain stop_ids in stops
def get_subgraph(
        stops: pd.DataFrame,
        G_obj: gtfs,
        t_start: int = 0,
        t_end: int = 1440,
):
    stop_ids = stops["stop_id"].to_numpy()
    stop_lons = stops["stop_lon"].to_numpy()
    stop_lats = stops["stop_lat"].to_numpy()
    nodes = []
    for stop_id in stop_ids:
        ts = G_obj.nodes_time_map[stop_id]
        ts = np.array(list(ts))
        filt = (t_start <= ts) & (ts <= t_end)
        ts = ts[filt]
        origin_nodes = [f"{stop_id}_{t}" for t in ts]
        # add properties for each node
        nodes += origin_nodes
    subgraph = G_obj.G.subgraph(nodes)
    # add attributes for each node
    # {'name': xxx, 'time': xxx, 'lon': xxx, 'lat': xxx}
    for node in subgraph.nodes():
        stop_name = node.split("_")[:-1]
        stop_name = '_'.join(stop_name)
        stop_time = int(node.split("_")[-1])
        idx = np.argwhere(stop_ids == stop_name)
        # print("stop_name:", stop_name, "node:", node, "idx:", idx)
        the_lon = stop_lons[idx[0]]
        the_lat = stop_lats[idx[0]]
        subgraph.nodes[node].update({
            "stop_id": stop_name,
            "time": stop_time,
            "lon": the_lon[0],
            "lat": the_lat[0],
        })
    return subgraph


def get_subgraph_from_nodes(stops, nodes, G_obj):
    # retrieve all stops information
    stop_ids = stops["stop_id"].to_numpy()
    stop_lons = stops["stop_lon"].to_numpy()
    stop_lats = stops["stop_lat"].to_numpy()

    # get subgraph
    subgraph = G_obj.G.subgraph(nodes)
    for node in subgraph.nodes():
        stop_name = node.split("_")[:-1]
        stop_name = '_'.join(stop_name)
        stop_time = node.split("_")[-1]
        if stop_time == "D":
            stop_time = "D"
        else:
            stop_time = int(stop_time)
        idx = np.argwhere(stop_ids == stop_name)
        # print("stop_name:", stop_name, "node:", node, "idx:", idx)
        the_lon = stop_lons[idx[0]]
        the_lat = stop_lats[idx[0]]
        subgraph.nodes[node].update({
            "stop_id": stop_name,
            "time": stop_time,
            "lon": the_lon[0],
            "lat": the_lat[0],
        })
    return subgraph


def select_subgraph_from_time(G_subgraph, t_start, t_end):
    node_lst = []
    for node in G_subgraph.nodes():
        n = G_subgraph.nodes[node]
        if t_start <= n["time"] and n["time"] <= t_end:
            node_lst.append(node)
    return G_subgraph.subgraph(node_lst)


def merge_nodes_to_stop_ids(stops, G_subgraph):
    stop_names = []
    for node in G_subgraph.nodes():
        stop_name = node.split("_")[:-1]
        stop_name = '_'.join(stop_name)
        stop_time = node.split("_")[-1]
        stop_names.append(stop_name)
    stop_names = list(set(stop_names))
    stops_sel = stops.loc[stops['stop_id'].isin(stop_names), :].copy()
    return stops_sel


def get_graph_stats(G: rx.PyDiGraph) -> None:
    num_nodes = len(G.nodes())
    num_edges = len(G.edges())
    num_compos = rx.number_weakly_connected_components(G)

    print(f"Number of nodes: {num_nodes}")
    print(f"Number of edges: {num_edges}")
    print(f"Number of weakly connected components: {num_compos}")


def get_graph_memory(G: rx.PyDiGraph) -> None:
    edge_mem = sum([sys.getsizeof(e) for e in G.edges()])
    node_mem = sum([sys.getsizeof(n) for n in G.nodes()])

    print(f"Edge memory (MB): {edge_mem / 1024 / 1024:.2f}")
    print(f"Node memory (MB): {node_mem / 1024 / 1024:.2f}")
    print(f"Total memory (MB): {(edge_mem + node_mem) / 1024 / 1024:.2f}")


# used for plotting it using Plotly
def get_subgraph_dfs(G: rx.PyDiGraph):
    def get_pos(G, node):
        node = G.nodes[node]
        x, y, z = node['lon'], node['lat'], node['time']
        return x,y,z
    # Extract node and edge positions from the layout
    node_xyz = np.array([get_pos(G, v) for v in G.nodes()])
    edge_xyz = np.array([(get_pos(G, u), get_pos(G, v)) for u, v in G.edges()])
    edge_mode = np.array([G[u][v]["mode"] for u, v in G.edges()])
    print(node_xyz.shape)
    print(edge_xyz.shape)
    nodes_df, edges_df = pd.DataFrame(), pd.DataFrame()
    nodes_df["lon"] = node_xyz.T[0]
    nodes_df["lat"] = node_xyz.T[1]
    nodes_df["time"] = node_xyz.T[2]
    edges_df["lon0"] = edge_xyz.T[0][0]
    edges_df["lon1"] = edge_xyz.T[0][1]
    edges_df["lat0"] = edge_xyz.T[1][0]
    edges_df["lat1"] = edge_xyz.T[1][1]
    edges_df["time0"] = edge_xyz.T[2][0]
    edges_df["time1"] = edge_xyz.T[2][1]
    edges_df["mode"] = edge_mode
    return nodes_df, edges_df



