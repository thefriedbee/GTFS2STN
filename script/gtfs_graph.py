"""
GTFS networkx graph object.
Data is augumented in the class
"""
import random
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
        self.G_reversed = None
        # augmented data structure to gather all nodes for each stop_id
        self.nodes_time_map = {}  # this one only records time with bus/transit vehicle arrived
        self.nodes_time_map_all = {}  # this one also contains all nodes, including "walking nodes"

    def add_skeleton_nodes(self, stop_dict, times_info):
        stop_id = stop_dict["stop_id"]
        # stop_id = str(stop_id)
        nodes_info = [(f"{stop_id}_{time_info}", stop_dict)
                      for i, time_info in enumerate(times_info)]
        self.G.add_nodes_from(nodes_info)
        self.nodes_time_map[stop_id] = SortedSet(times_info)
        self.nodes_time_map_all[stop_id] = SortedSet(times_info)

    def add_edge(self, stop_a, stop_b, node_a, node_b, t1=0, t2=0,
                 properties=None, map_to_skeleton=True):
        """
        If t1=0, t2=0, then in fact two new nodes are not recorded in self.nodes_time_map
        Strategy for now: only nodes with transit arrived are recorded in self.nodes_time_map
        """
        if properties is None:
            properties = {}
        self.G.add_edge(node_a, node_b, **properties)
        self.nodes_time_map_all[stop_a].add(int(t1))
        self.nodes_time_map_all[stop_b].add(int(t2))
        if map_to_skeleton:
            self.nodes_time_map[stop_a].add(int(t1))
            self.nodes_time_map[stop_b].add(int(t2))

    def add_edges_within_same_stops(self):
        """
        Strategy: chaining all nodes, including walking nodes
        :return:
        """
        for stop_id in self.nodes_time_map_all:
            ts = self.nodes_time_map_all[stop_id]
            for i in range(len(ts) - 1):
                t1, t2 = ts[i], ts[i + 1]
                node_a = f"{stop_id}_{t1}"
                node_b = f"{stop_id}_{t2}"
                # waiting at the same station, so waiting time equals travel time
                self.add_edge(stop_id, stop_id,
                              node_a, node_b,
                              t1, t2,
                              properties={"tt": t2 - t1, "wt": t2 - t1,
                                          "mode": "wait"},
                              map_to_skeleton=False)

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
                # edge to destinations are not tracked in self.nodes_time_map
                self.G.add_edge(ori, f"{stop_id}_D",
                                **{"tt": 0, "wt": 0,
                                   "mode": "arrived"})

    def add_edges_walkable_stops(self, stops_b, walk_speed=1):
        # stops_b: with neighbors identified in new column "neighbor"
        # walk_speed: in mph
        # connect between neighboring end nodes (only at skeleton times)
        for stop_id in self.nodes_time_map:
            # check neighbors in stops_b
            # print(stops_b.loc[stops_b["stop_id"] == stop_id]['neighbors'])
            nei_ids = stops_b.loc[stops_b["stop_id"] == stop_id]['neighbors'].iloc[0]
            nei_IDs = stops_b.iloc[nei_ids]["stop_id"]
            # retrieve distance (in miles)
            dists = stops_b.loc[stops_b["stop_id"] == stop_id]['dists'].iloc[0]
            # compute walking time (in minutes) (for each distance)
            walk_ts = (dists / walk_speed) * 60
            # add link to each neighbor for nodes at each time
            ts = self.nodes_time_map[stop_id]
            # IDEA: a fan of edges to the neighboring stops at transit's drop-off locations
            for i in range(len(ts)):
                t0 = ts[i]
                t_ends = t0 + walk_ts
                # add edge for each neighbor
                for j, nei_ID in enumerate(nei_IDs):
                    t_end = t_ends[j]
                    if nei_ID != stop_id:
                        self.add_edge(stop_id, nei_ID,
                                      f"{stop_id}_{t0:.0f}", f"{nei_ID}_{t_end:.0f}",
                                      t1=0, t2=t_end,
                                      properties={"tt": walk_ts[j], "wt": walk_ts[j],
                                                  "mode": "walk"},
                                      map_to_skeleton=False)

    # query shortest path given origin stop_id and departure time (in minutes)
    # new strategy: create a new source node pointing at nearest point
    def query_origin_stop_time(self, stops_df, stop_id, depart_min, cutoff, walk_speed=1):
        one_stop_df = stops_df.loc[stops_df["stop_id"] == stop_id, :].iloc[0]
        nei_idxs = one_stop_df["neighbors"]  # all neighbors index
        nei_dists = one_stop_df["dists"]  # distance in miles
        nei_stop_ids = stops_df.loc[nei_idxs, "stop_id"]  # all neighbors IDs
        nei_wts = np.array(nei_dists) / walk_speed * 60  # walking time in minutes
        print("nei wts:", nei_wts)
        depart_mins = depart_min + nei_wts
        # get all proposed starting nodes
        nodes_id_origin = [f"{stop_id}_{depart_mins[i]:.0f}"
                           for i, stop_id in enumerate(nei_stop_ids)]

        # from stop to next arrived vehicle
        next_mins = np.array([self.find_closest_next_time(stop_id, depart_mins[i])
                              for i, stop_id in enumerate(nei_stop_ids)])
        wait_mins = next_mins - depart_min  # minus the queried starting time here
        # get all proposed starting nodes to take transits
        nodes_id_next = [f"{stop_id}_{next_mins[i]:.0f}"
                         for i, stop_id in enumerate(nei_stop_ids)]
        # add link (no need to track for this in self.nodes_time_map)
        # just wait at the stop for transit to arrive
        # TODO: expand to start for neighboring stops, which is easy to do...
        # add all edges
        one_node_id = f"{stop_id}_{depart_min:.0f}"
        for i, sid in enumerate(nei_stop_ids):
            # add links
            self.G.add_edge(nodes_id_origin[i], nodes_id_next[i],
                            **{"tt": wait_mins[i], "wt": wait_mins[i],
                               "mode": "wait"})
            # add links from source to others
            if sid != stop_id:
                self.G.add_edge(one_node_id, nodes_id_origin[i],
                                **{"tt": nei_wts[i], "wt": nei_wts[i],
                                   "mode": "walk"})
            else:
                self.G.add_edge(one_node_id, nodes_id_origin[i],
                                **{"tt": nei_wts[i], "wt": nei_wts[i],
                                   "mode": "wait"})
            # remember to connect nodes_id_origin to destination points
            self.G.add_edge(nodes_id_origin[i], f"{sid}_D",
                            **{"tt": 0, "wt": 0,
                               "mode": "arrive"})

        # start searching...
        return nx.single_source_dijkstra(self.G, one_node_id, cutoff=cutoff, weight="tt")

    # query shortest path
    def query_destination_stop_time(self, stops_df, stop_id, arrive_min, cutoff,
                                    walk_speed=1, renew_reversed=False, run_dijkstra=True):
        if self.G_reversed is None or renew_reversed:
            self.generate_reverse_network()

        one_stop_df = stops_df.loc[stops_df["stop_id"] == stop_id, :].iloc[0]
        nei_idxs = one_stop_df["neighbors"]  # all neighbors index
        nei_dists = one_stop_df["dists"]  # distance in miles
        nei_stop_ids = stops_df.loc[nei_idxs, "stop_id"]  # all neighbors IDs
        nei_wts = np.array(nei_dists) / walk_speed * 60  # walking time in minutes
        print("nei wts:", nei_wts)
        depart_mins = arrive_min - nei_wts
        # get all proposed starting nodes
        nodes_id_origin = [f"{stop_id}_{depart_mins[i]:.0f}"
                           for i, stop_id in enumerate(nei_stop_ids)]

        # from stop to prev arrived vehicle
        prev_mins = np.array([self.find_closest_prev_time(stop_id, depart_mins[i])
                              for i, stop_id in enumerate(nei_stop_ids)])
        wait_mins = arrive_min - prev_mins  # minus the queried starting time here
        # get all proposed starting nodes to take transits
        nodes_id_prev = [f"{stop_id}_{prev_mins[i]:.0f}"
                         for i, stop_id in enumerate(nei_stop_ids)]
        # add link (no need to track for this in self.nodes_time_map)
        # just wait at the stop for transit to arrive
        # TODO: expand to start for neighboring stops, which is easy to do...
        # note: graph is already reversed, so here the order doesn't need to be changed...
        # add all edges
        one_node_id = f"{stop_id}_{arrive_min:.0f}"
        for i, sid in enumerate(nei_stop_ids):
            # add links
            self.G_reversed.add_edge(nodes_id_origin[i], nodes_id_prev[i],
                                     **{"tt": wait_mins[i], "wt": wait_mins[i],
                                        "mode": "wait"})
            # add links from source to others
            if sid != stop_id:
                self.G_reversed.add_edge(one_node_id, nodes_id_origin[i],
                                         **{"tt": nei_wts[i], "wt": nei_wts[i],
                                            "mode": "walk"})
            else:
                self.G_reversed.add_edge(one_node_id, nodes_id_origin[i],
                                         **{"tt": nei_wts[i], "wt": nei_wts[i],
                                            "mode": "wait"})
            # remember to connect nodes_id_origin to destination points
            self.G_reversed.add_edge(nodes_id_origin[i], f"{sid}_D",
                                     **{"tt": 0, "wt": 0,
                                        "mode": "arrive"})
        if run_dijkstra:
            return nx.single_source_dijkstra(self.G_reversed, one_node_id,
                                             cutoff=cutoff, weight="tt")

    def query_destination_stops_time(self, stops_df, stop_ids, arrive_min, cutoff,
                                     walk_speed=1, renew_reversed=False):
        nodes_id = [f"{stop_id}_{arrive_min:.0f}" for stop_id in stop_ids]
        print(nodes_id)
        for stop_id in stop_ids:
            self.query_destination_stop_time(stops_df, stop_id, arrive_min, cutoff,
                                             walk_speed=walk_speed, renew_reversed=renew_reversed, run_dijkstra=False)
        # run multiple source search
        return nx.multi_source_dijkstra_path_length(self.G_reversed, nodes_id, cutoff=cutoff, weight="tt")

    def query_od_stops_time(self, stop_id_o, stop_id_d, depart_min):
        """
        Between one pair
        :param stop_id_o: origin stop id
        :param stop_id_d: destination stop id
        :return:
        """
        node_id_origin = f"{stop_id_o}_{depart_min:.0f}"
        node_id_dest = f"{stop_id_d}_D"
        # add on edge...?
        next_min = self.find_closest_next_time(stop_id_o, depart_min)
        wait_min = next_min - depart_min
        node_id_next = f"{stop_id_o}_{next_min:.0f}"
        # add link (no need to track this in self.nodes_time_map)
        self.G.add_edge(node_id_origin, node_id_next,
                        **{"tt": wait_min, "wt": wait_min,
                           "mode": "wait"})

        # TODO: add walking distance from node_id_origin to other nodes
        # start searching
        return nx.shortest_path(self.G,
                                source=node_id_origin, target=node_id_dest, weight="tt")

    def generate_reverse_network(self):
        # get the network with all edges reversed, used for reversed search
        self.G_reversed = self.G.reverse(copy=True)
        # but don't reverse links for the destination links (e.g., xxx_D)
        all_dest_nodes = []
        for i, k in enumerate(self.nodes_time_map.keys()):
            all_dest_nodes += [k + "_D"]
        # reverse back destination nodes
        for e_start in all_dest_nodes:
            edges = list(self.G_reversed.out_edges(e_start))
            for e in edges:
                attrs = self.G_reversed.edges[e]
                self.G_reversed.remove_edge(e[0], e[1])
                self.G_reversed.add_edge(e[1], e[0], **attrs)

    def find_closest_next_time(self, stop_id, time_min):
        idx = self.nodes_time_map[stop_id].bisect_left(time_min)
        return self.nodes_time_map[stop_id][idx]  # return the next time

    def find_closest_prev_time(self, stop_id, time_min):
        idx = self.nodes_time_map[stop_id].bisect_left(time_min)
        return self.nodes_time_map[stop_id][idx - 1]  # return the next time

    # get shortest travel times from one stop to the others
    def get_shortest_tts(self, one_source_results, ignore_fail=False):
        stops = self.nodes_time_map.keys()
        dest_dict = {}
        for stop_id in stops:
            # get travel times for each node
            try:
                one_source_tts = one_source_results[f"{stop_id}_D"]
            except:
                if ignore_fail:
                    continue
                one_source_tts = -1  # placeholder for nonfeasible trips
            dest_dict[f"{stop_id}_D"] = one_source_tts
        return dest_dict

    # get travel time/waiting time given path (a list of nodes)
    def get_ttwt_from_pth(self, G, path_nodes):
        n0 = path_nodes[0]
        transit_time = 0  # total travel time
        wait_time, walk_time = 0, 0  # total waiting time
        for i, n1 in enumerate(path_nodes):
            if i == 0:
                continue
            the_mode = G[n0][n1]['mode']
            if the_mode == "walk":
                walk_time += G[n0][n1]['tt']
            if the_mode == "wait":
                wait_time += G[n0][n1]['wt']
            if the_mode == "transit":
                transit_time += G[n0][n1]['tt']
            n0 = n1

        transit_time = round(transit_time, 2)
        wait_time = round(wait_time, 2)
        return transit_time, wait_time, walk_time

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

    def get_subgraph_one_stop(self, stop_id, show_all=False):
        # get sub-graph with all nodes that belongs to this specific stop
        if show_all:
            ts = self.nodes_time_map_all[stop_id]
        else:
            ts = self.nodes_time_map[stop_id]
        nodes = []
        for t_i in ts:
            nodes.append(f"{stop_id}_{t_i}")
        return self.G.subgraph(nodes)


# generate skeleton nodes over time-space for one stop
def generate_ts_nodes(stop_ser, G_obj, t0=0, t1=1440, t_step=15):
    stop_dict = stop_ser[['stop_id', 'stop_lat', 'stop_lon']].to_dict()
    nodes_info = []
    times_info = np.arange(t0, t1 + 1, t_step).tolist()
    # add one skeleton node for each t_step minutes
    for t in times_info:
        stop_dict['t'] = int(t)
        nodes_info.append(deepcopy(stop_dict))  # use deepcopy for now
    nodes_info = [(f"{node_info['stop_id']}_{(i * t_step):.0f}", node_info)
                  for i, node_info in enumerate(nodes_info)]
    G_obj.add_skeleton_nodes(stop_dict, times_info)


# add all skeleton nodes from stops.txt dataframe
def add_nodes_all_stops(stops, G_obj, t_step=15):
    stops.apply(generate_ts_nodes, axis=1, G_obj=G_obj, t_step=t_step)


# scanning all trips and add links between nodes
def generate_ts_edges(stop_times, G_obj):
    stop_times['arrive_minute'] = pd.to_timedelta(stop_times['arrival_time']).dt.seconds / 60
    stop_times['departure_minute'] = pd.to_timedelta(stop_times['departure_time']).dt.seconds / 60
    # set time info to whole minute
    stop_times['arrive_minute'] = stop_times['arrive_minute'].astype("float32")
    stop_times['departure_minute'] = stop_times['departure_minute'].astype("float32")
    # ser_1trip_stops: trips stops of one trip_id
    stop_ids = stop_times['stop_id'].tolist()
    arr_ts = stop_times['arrive_minute'].tolist()
    for i in range(len(stop_ids) - 1):
        # stop names and arrival times
        stop_i, stop_j = stop_ids[i], stop_ids[i + 1]
        ti, tj = arr_ts[i], arr_ts[i + 1]
        # node ids
        start_nid = f"{stop_i}_{ti:.0f}"
        end_nid = f"{stop_j}_{tj:.0f}"
        # add augment info
        G_obj.add_edge(stop_i, stop_j,
                       start_nid, end_nid,
                       ti, tj,
                       properties={"tt": tj - ti, "wt": 0,
                                   "mode": "transit"})


# add all edges+nodes from stop_times.txt dataframe
def add_edges_all_stop_times(stop_times, G_obj):
    stop_times.groupby(["trip_id"]).apply(generate_ts_edges, G_obj)


# visualize one stop'fs information over time
def plot_one_stop_over_time(G_subgraph):
    fig, ax = plt.subplots(1, 1, figsize=(40, 4))

    def my_func(e):
        return int(e.split('_')[-1])

    nodes = sorted(list(G_subgraph.nodes()), key=my_func)
    edges = sorted(list(G_subgraph.edges()))
    # print(f"#nodes: {len(nodes)}")
    # print(f"nodes: {nodes}")
    # print(f"#links: {len(edges)}")
    # print(f"links: {edges}")
    pos = {node: (int(node.split('_')[-1]), random.random() - 0.5) for node in nodes}
    nx.draw(G_subgraph, pos=pos, node_size=10, ax=ax)
    plt.axis("on")
    ax.tick_params(left=True, bottom=True, labelleft=False, labelbottom=True)
    ax.set_xlim(-10, 1450)
    ax.set_ylim(-1, 1)
    ax.set_xticks([i * 60 for i in range(24 + 1)])
    ax.set_xticklabels([str(i) for i in range(24 + 1)], fontsize=40)
    ax.set_xlabel("Hour of the day", fontsize=40)
    plt.grid(True)
    plt.show()
