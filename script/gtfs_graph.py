"""
GTFS networkx graph object.
Data is augumented in the class
"""
import numpy as np
import pandas as pd
import geopandas as gpd

import networkx as nx
from shapely.geometry import Point
from shapely.ops import nearest_points

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

import bisect
from sortedcontainers import SortedSet
from copy import deepcopy


class GTFS_Graph:
    def __init__(self):
        self.G = nx.DiGraph()  # spatial temporal graph
        self.nodes_time_map = {}
    
    def add_skeleton_nodes(self, stop_dict, times_info):
        stop_id = stop_dict["stop_id"]
        nodes_info = [(f"{stop_id}_{time_info}", stop_dict)
                      for i, time_info in enumerate(times_info)]
        self.G.add_nodes_from(nodes_info)
        self.nodes_time_map[stop_id] = SortedSet(times_info)

    def add_edge(self, stop_a, stop_b, node_a, node_b, t1=0, t2=0, properties=None):
        if properties is None:
            properties = {}
        self.G.add_edge(node_a, node_b, **properties)
        self.nodes_time_map[stop_a].add(int(t1))
        self.nodes_time_map[stop_b].add(int(t2))

    def add_edges_within_same_stops(self):
        for stop_id in self.nodes_time_map:
            ts = self.nodes_time_map[stop_id]
            for i in range(len(ts)-1):
                t1, t2 = ts[i], ts[i+1]
                node_a = f"{stop_id}_{t1}"
                node_b = f"{stop_id}_{t2}"
                self.add_edge(stop_id, stop_id, 
                              node_a, node_b,
                              t1, t2, 
                              properties={"tt": t2-t1, "wt": t2-t1})
    
    def add_hyper_nodes(self):
        stops = self.nodes_time_map.keys()
        # for each stop, add destionation hyper nodes
        nodes_info = []
        for stop_id in stops:
            nodes_info += [(f"{stop_id}_D", {"stop_id": stop_id})]
        self.G.add_nodes_from(nodes_info)
        # connect stops nodes over the day to destination nodes (for sure)
        for stop_id in stops:
            ts = self.nodes_time_map[stop_id]
            Os = [f"{stop_id}_{t}" for t in ts]
            for ori in Os:
                self.G.add_edge(ori, f"{stop_id}_D", 
                                **{"tt": 0, "wt": 0})
    
    def add_edges_walkable_stops(self, stops_b, walk_speed=1):
        # stops_b: with neighbors identified in new column "neighbor"
        # walk_speed: in mph
        # connect between neighboring end nodes (only at skeleton times)
        for stop_id in self.nodes_time_map:
            # check neighbors in stops_b
            # print(stops_b.loc[stops_b["stop_id"] == stop_id]['neighbors'])
            nei_ids = stops_b.loc[stops_b["stop_id"] == stop_id]['neighbors'].iloc[0]
            nei_IDs = stops_b.iloc[nei_ids]["stop_id"]
            dists = stops_b.loc[stops_b["stop_id"] == stop_id]['dists'].iloc[0]
            walk_ts = (dists / walk_speed) * 60  # convert time to minutes
            # add link to each neighbor for nodes at each time
            ts = self.nodes_time_map[stop_id]
            for i in range(len(ts)):
                t0 = ts[i]
                t_ends = t0 + walk_ts
                # print("t_ends:", t_ends)
                # add edge for each neighbor
                for j, nei_ID in enumerate(nei_IDs):
                    self.add_edge(stop_id, nei_ID,
                                  f"{stop_id}_{t0:.0f}", f"{nei_ID}_{t_ends[j]:.0f}",
                                  properties={"tt": walk_ts[j], "wt": walk_ts[j]})
    
    # query shortest path given origin stop_id and departure time (in minutes)
    def query_origin_stop_time(self, stop_id, depart_min, cutoff):
        # for now, round to the closest but earlier 15 minutes
        depart_min = int(int(depart_min / 15) * 15)
        node_id_origin = f"{stop_id}_{depart_min:.0f}"
        # shortest traveling time
        return nx.single_source_dijkstra(self.G, node_id_origin,
                                         cutoff=cutoff, weight="tt")
    
    # get shortest travel times from one stop to the others
    def get_shortest_tts(self, one_source_results):
        stops = self.nodes_time_map.keys()
        dest_dict = {}
        for stop_id in stops:
            # get travel times for each node
            try:
                one_source_tts = one_source_results[0][f"{stop_id}_D"]
            except:
                one_source_tts = -1  # placeholder for nonfeasible trips
            dest_dict[f"{stop_id}_D"] = one_source_tts
        return dest_dict

    def get_shortest_paths(self, one_source_results):
        stops = self.nodes_time_map.keys()
        path_dict = {}
        for stop_id in stops:
            # get travel times for each node
            try:
                one_source_paths = one_source_results[1][f"{stop_id}_D"]
            except:
                one_source_paths = []  # placeholder for nonfeasible trips
            path_dict[f"{stop_id}_D"] = one_source_paths
        return path_dict

    def get_subgraph_one_stop(self, stop_id):
        # get subgraphs belongs to one stop
        ts = self.nodes_time_map[stop_id]
        nodes = []
        for t_i in ts:
            nodes.append(f"{stop_id}_{t_i}")
        return self.G.subgraph(nodes)


# generate skeleton nodes over time-space for one stop
def generate_ts_nodes(stop_ser, G_obj, t0=0, t1=1440, t_step=15):
    stop_dict = stop_ser[['stop_id', 'stop_lat', 'stop_lon']].to_dict()
    nodes_info = []
    times_info = np.arange(t0, t1+1, t_step).tolist()
    # add one skeleton node for each t_step minutes
    for t in times_info:
        stop_dict['t'] = int(t)
        nodes_info.append(deepcopy(stop_dict))  # use deepcopy for now
    nodes_info = [(f"{node_info['stop_id']}_{(i*t_step):.0f}", node_info)
                  for i, node_info in enumerate(nodes_info)]
    G_obj.add_skeleton_nodes(stop_dict, times_info)


# add all skeleton nodes from stops.txt dataframe
def add_nodes_all_stops(stops, G_obj, t_step=15):
    stops.apply(generate_ts_nodes, axis=1, G_obj=G_obj, t_step=t_step)


# scanning all trips and add links between nodes
def generate_ts_edges(stop_times, G_obj):
    stop_times['arrive_minute'] = pd.to_timedelta(stop_times['arrival_time']).dt.seconds/60
    stop_times['departure_minute'] = pd.to_timedelta(stop_times['departure_time']).dt.seconds/60
    # ser_1trip_stops: trips stops of one trip_id
    stop_ids = stop_times['stop_id'].tolist()
    arr_ts = stop_times['arrive_minute'].tolist()
    for i in range(len(stop_ids)-1):
        # stop names and arrival times
        stop_i, stop_j = stop_ids[i], stop_ids[i+1]
        ti, tj = arr_ts[i], arr_ts[i+1]
        # node ids
        start_nid = f"{stop_i}_{ti:.0f}"
        end_nid = f"{stop_j}_{tj:.0f}"
        # add augment info
        G_obj.add_edge(stop_i, stop_j,
                       start_nid, end_nid,
                       ti, tj,
                       properties={"tt": tj-ti, "wt": 0})


# add all edges from stop_times.txt dataframe
def add_edges_all_stop_times(stop_times, G_obj):
    stop_times.groupby(["trip_id"]).apply(generate_ts_edges, G_obj)


# visualize one stop's information over time
def plot_one_stop_over_time(G_subgraph):
    fig, ax = plt.subplots(1, 1, figsize=(40, 5))
    nodes = list(G_subgraph.nodes())
    pos = {node:(int(node.split('_')[-1]), 0) for node in nodes}
    nx.draw(G_subgraph, pos=pos, node_size=5, ax=ax)
    plt.axis("on")
    ax.tick_params(left=True, bottom=True, labelleft=False, labelbottom=True)
    ax.set_xlim(-10, 1450)
    ax.set_ylim(-1, 1)
    ax.set_xticks([i*60 for i in range(24+1)])
    ax.set_xticklabels([str(i) for i in range(24+1)], fontsize=40)
    ax.set_xlabel("Hour of the day", fontsize=40)
    plt.grid(True)
    plt.show()



