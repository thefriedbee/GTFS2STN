"""
A rustworkx version of GTFS graph (better efficiency compared with networkx...)
"""
import copy
from enum import Enum
from dataclasses import dataclass

import numpy as np
import pandas as pd
import rustworkx as rx
from sortedcontainers import SortedSet


@dataclass
class GTFSNode:
    stop_id: str
    tod: int  # time of the day
    name: str

    def __init__(self, stop_id: str, tod=-1, name=None):
        self.stop_id = stop_id
        self.tod = int(tod)  # -1 is the placeholder for destination node...
        self.name = f"{self.stop_id}_{self.tod:.0f}"
        if name is not None:
            self.name = name

    def __repr__(self):
        return f"<{self.stop_id},{self.tod},{self.name}>"


class EdgeMode(Enum):
    WAIT = 1
    WALK = 2
    TRIP = 3
    ARRIVED = 4


@dataclass
class GTFSEdge:
    start_node: int
    end_node: int
    trip_t: float  # transit time
    wait_t: float  # waiting time
    walk_t: float  # walking time
    total_t: float  # total travel time
    mode: EdgeMode

    def __init__(
            self, start_node: int, end_node: int,
            trip_t: float, wait_t: float, walk_t: float, mode: EdgeMode
    ):
        self.start_node = start_node
        self.end_node = end_node
        self.trip_t = trip_t
        self.wait_t = wait_t
        self.walk_t = walk_t
        self.total_t = self.trip_t + self.wait_t + self.walk_t
        self.mode = mode  # edge mode, including "walk", "stop", etc.

    def __repr__(self):
        return f"<{self.start_node}-{self.end_node}, ({self.trip_t},{self.wait_t},{self.walk_t}), {self.mode}>"


class GTFSGraph:
    def __init__(self):
        self.G: rx.PyDiGraph = rx.PyDiGraph()  # spatiotemporal graph
        # mapping from node string name to its index...
        self.nodes_name_map: dict = {}
        # augmented data structure to gather all nodes for each stop_id
        # e.g., {"S1": [10, 20, 30]} means the "S1" stop has three time nodes...
        self.nodes_time_map: dict = {}

    def query_node_or_create(self, stop_id: str, tod: float) -> int:
        tod = int(tod)
        node_name = f"{stop_id}_{tod:.0f}"
        # if a node is in the network, just return the node id...
        if node_name in self.nodes_name_map:
            return self.nodes_name_map[node_name]

        # otherwise, create the new node...
        node_id = self.G.add_node(GTFSNode(stop_id, tod))
        self.nodes_name_map[node_name] = node_id

        if stop_id in self.nodes_time_map:
            self.nodes_time_map[stop_id].add(tod)
        else:
            self.nodes_time_map[stop_id] = SortedSet([tod])
        return node_id

    def add_skeleton_nodes(
            self,
            stop_dict: dict,  # dictionary of one stop id
            times_info: list[int],  # a list of time integers (minute of the day...)
    ) -> None:
        stop_id = stop_dict["stop_id"]
        nodes = [
            GTFSNode(stop_id, tod)
            for i, tod in enumerate(times_info)
        ]
        node_ids = self.G.add_nodes_from(nodes)

        for n, nid in zip(nodes, node_ids):
            self.nodes_name_map[n.name] = nid
        # record information for the stop id...
        self.nodes_time_map[stop_id] = SortedSet(times_info)

    def add_edge(
            self,
            node_a: int, node_b: int,  # e.g., 10235 (node id in the graph)
            properties: None | GTFSEdge = None,
    ) -> None:
        """
            If t1=0, t2=0, then in fact two new nodes are not recorded in self.nodes_time_map
            Strategy for now: only nodes with transit arrived are recorded in self.nodes_time_map
        """
        # don't care anything about creating/maintaining nodes here...
        # assume both end nodes are created before...
        if properties is None:
            properties = {}
        self.G.add_edge(node_a, node_b, properties)

    def add_edges_within_same_stops(self):
        for stop_id in self.nodes_time_map:
            ts = self.nodes_time_map[stop_id]
            for i in range(len(ts) - 1):
                t1, t2 = ts[i], ts[i + 1]
                node_a_id = self.query_node_or_create(stop_id=stop_id, tod=t1)
                node_b_id = self.query_node_or_create(stop_id=stop_id, tod=t2)
                # waiting at the same station, so waiting time equals travel time
                self.add_edge(
                    node_a=node_a_id, node_b=node_b_id,
                    properties=GTFSEdge(
                        start_node=node_a_id, end_node=node_b_id,
                        trip_t=0, wait_t=t2 - t1, walk_t=0,
                        mode=EdgeMode.WAIT
                    )
                )

    def add_hyper_nodes(self):
        """
            Add source node and destination node
        """
        stops = self.nodes_time_map.keys()
        # for each stop, add destination hyper nodes
        dest_nodes = [
            GTFSNode(stop_id=stop_id, name=f"{stop_id}_D")
            for stop_id in stops
        ]
        # create graph's destination nodes
        dest_node_ids = self.G.add_nodes_from(dest_nodes)
        for n, nid in zip(dest_nodes, dest_node_ids):
            self.nodes_name_map[n.name] = nid

        # connect all stops nodes over the day to the destination node of the stop...
        for dest_node_id, stop_id in zip(dest_node_ids, stops):
            ts = self.nodes_time_map[stop_id]
            for ori_stop_id in [f"{stop_id}_{t:.0f}" for t in ts]:
                ori_node_id = self.nodes_name_map[ori_stop_id]
                # edge to destinations are not tracked in self.nodes_time_map
                self.add_edge(
                    node_a=ori_node_id, node_b=dest_node_id,
                    properties=GTFSEdge(
                        start_node=ori_node_id, end_node=dest_node_id,
                        trip_t=0, wait_t=0, walk_t=0,
                        mode=EdgeMode.ARRIVED
                    )
                )

    def add_edges_walkable_stops(
            self,
            stops_b: pd.DataFrame,  # index of neighbors?
            walk_speed: float = 1  # unit is mph
    ) -> None:
        # connect between neighboring end nodes (only at skeleton times)
        stop_ids = copy.deepcopy(list(self.nodes_time_map.keys()))
        stop_ids_ts = copy.deepcopy([self.nodes_time_map[stop_id] for stop_id in stop_ids])

        for stop_id, ts in zip(stop_ids, stop_ids_ts):
            # check neighbors in stops_b
            nei_ids = stops_b.loc[stops_b["stop_id"] == stop_id, 'neighbors'].iloc[0]
            nei_IDs = stops_b.iloc[nei_ids]["stop_id"]
            # retrieve distance (in miles)
            dists = stops_b.loc[stops_b["stop_id"] == stop_id]['dists'].iloc[0]
            # compute walking time (in minutes) (for each distance)
            walk_ts = (dists / walk_speed) * 60

            # IDEA: a fan of edges to the neighboring stops at transit's drop-off locations
            for i in range(len(ts)):
                t0 = ts[i]
                t_ends = t0 + walk_ts
                origin_node_index = self.query_node_or_create(stop_id=stop_id, tod=t0)

                # add edge for each neighbor
                for j, nei_id in enumerate(nei_IDs):
                    t_end = t_ends[j]
                    dest_node_index = self.query_node_or_create(stop_id=nei_id, tod=t_end)
                    if nei_id != stop_id:  # walking edge
                        self.add_edge(
                            node_a=origin_node_index, node_b=dest_node_index,
                            properties=GTFSEdge(
                                start_node=origin_node_index, end_node=dest_node_index,
                                trip_t=0, wait_t=0, walk_t=walk_ts[j],
                                mode=EdgeMode.WALK
                            )
                        )

    # query the shortest path given origin stop_id and departure time (in minutes)
    # strategy: create a new source node pointing at nearest point
    def query_origin_stop_time(
            self,
            stops_df: pd.DataFrame,
            stop_id: str,
            depart_min: float,
            # cutoff: float,
            walk_speed: float = 1
    ) -> tuple[dict, dict]:
        # fetch neighbor information
        stops_df["stop_id"] = stops_df["stop_id"].astype('string')
        one_stop_df = stops_df.loc[stops_df["stop_id"] == stop_id, :].iloc[0]
        nei_idxs = one_stop_df["neighbors"]  # all neighbors index
        nei_dists = one_stop_df["dists"]  # distance in miles
        nei_stop_ids = stops_df["stop_id"].iloc[nei_idxs].to_list()
        # print("nei_stop_ids", nei_stop_ids)
        nei_wts = np.array(nei_dists) / walk_speed * 60  # walking time (in minutes)
        depart_mins = depart_min + nei_wts
        # print("depart_mins:", depart_mins)

        # from stop to next arrived vehicle
        next_mins = np.array([
            self.find_closest_next_time(nei_stop_id, int(depart_mins[i]))
            for i, nei_stop_id in enumerate(nei_stop_ids)
        ])
        # print("next_mins:", next_mins)

        # nodes connected to the "major" skeleton network (node c is in the network)
        nodes_b_ids = [
            self.query_node_or_create(stop_id=nei_stop_id, tod=int(next_mins[i]))
            for i, nei_stop_id in enumerate(nei_stop_ids)
        ]

        # process source info (add source node if it doesn't exist...)
        one_node_id = f"{stop_id}_{depart_min:.0f}"
        the_origin_nid = self.query_node_or_create(stop_id=stop_id, tod=int(depart_min))
        # print(f"source node: {one_node_id}------{the_origin_nid}")
        # print("node info: ", self.G.get_node_data(the_origin_nid))

        # add all edges to neighboring nodes...
        # print("the stop id:", stop_id, the_origin_nid)
        journey_mins = next_mins - depart_mins
        for i, node_b_id in enumerate(nodes_b_ids):
            sid = nei_stop_ids[i]
            # print("sid:", sid, node_b_id)
            journey_t = int(journey_mins[i])
            if stop_id != sid:
                self.add_edge(
                    node_a=the_origin_nid, node_b=node_b_id,
                    properties=GTFSEdge(
                        start_node=the_origin_nid, end_node=node_b_id,
                        trip_t=0, wait_t=0, walk_t=journey_t,
                        mode=EdgeMode.WALK
                    )
                )
            else:
                self.add_edge(
                    node_a=the_origin_nid, node_b=node_b_id,
                    properties=GTFSEdge(
                        start_node=the_origin_nid, end_node=node_b_id,
                        trip_t=0, wait_t=journey_t, walk_t=0,
                        mode=EdgeMode.WAIT
                    )
                )

        # print("incident edges:")
        # print(self.G.incident_edge_index_map(the_origin_nid))

        # target can only be node with "_D" ends...
        res_paths = rx.dijkstra_shortest_paths(
            self.G,
            source=the_origin_nid,
            weight_fn=lambda x: x.total_t,
            default_weight=0.01
        )

        res_dists = rx.dijkstra_shortest_path_lengths(
            self.G,
            node=the_origin_nid,
            edge_cost_fn=lambda x: x.total_t
        )
        return res_paths, res_dists

    def find_closest_next_time(self, stop_id: str, time_min: float) -> float:
        idx = self.nodes_time_map[stop_id].bisect_left(time_min)
        return self.nodes_time_map[stop_id][idx]  # return the next time

    def find_closest_prev_time(self, stop_id: str, time_min: float) -> float:
        idx = self.nodes_time_map[stop_id].bisect_left(time_min)
        return self.nodes_time_map[stop_id][idx - 1]  # return the next time

    def _create_linkage_to_graph(
            self,
            stop_orig_id: str,
            stop_dest_id: str,
            depart_min: int,
    ):
        next_min = self.find_closest_next_time(stop_orig_id, depart_min)
        orig_node_id = self.query_node_or_create(stop_id=stop_orig_id, tod=int(depart_min))
        next_node_id = self.query_node_or_create(stop_id=stop_orig_id, tod=int(next_min))
        journey_t = next_min - depart_min

        # create "self" link
        self.add_edge(
            node_a=orig_node_id, node_b=next_node_id,
            properties=GTFSEdge(
                start_node=orig_node_id, end_node=next_node_id,
                trip_t=0, wait_t=journey_t, walk_t=0,
                mode=EdgeMode.WAIT
            )
        )

        # create destination link
        node_id_dest = self.nodes_name_map[f"{stop_dest_id}_D"]
        return orig_node_id, node_id_dest

    def query_od_stops_time(
            self,
            stop_orig_id: str,
            stop_dest_id: str,
            depart_min: int,
    ) -> dict:
        orig_node_id, node_id_dest = self._create_linkage_to_graph(
            stop_orig_id=stop_orig_id,
            stop_dest_id=stop_dest_id,
            depart_min=depart_min
        )

        return rx.dijkstra_shortest_paths(
            self.G,
            source=orig_node_id,
            target=node_id_dest,
            weight_fn=lambda x: x.total_t
        )

    # get travel time/waiting time given path (a list of nodes)
    def get_travel_time_info_from_pth(
            self,
            G: rx.PyDiGraph,
            path_nodes: rx.PathMapping,
    ) -> tuple[float, float, float]:
        first_node = list(path_nodes.keys())[0]
        path_nodes = path_nodes[first_node]
        n0 = path_nodes[0]

        transit_time, wait_time, walk_time = 0, 0, 0
        for i, n1 in enumerate(path_nodes):
            if i == 0:
                continue
            index_map = G.edge_indices_from_endpoints(n0, n1)[0]
            dat = G.get_edge_data_by_index(index_map)

            the_mode = dat.mode
            if the_mode == EdgeMode.TRIP:
                transit_time += dat.trip_t
            if the_mode == EdgeMode.WAIT:
                wait_time += dat.wait_t
            if the_mode == EdgeMode.WALK:
                walk_time += dat.walk_t
            n0 = n1

        transit_time = round(transit_time, 2)
        wait_time = round(wait_time, 2)
        walk_time = round(walk_time, 2)
        return transit_time, wait_time, walk_time

    def query_od_stops_time_multiple_orig(
            self,
            stop_orig_ids: list[str],
            stop_dest_id: str,
            depart_min: int,
    ):
        paths = []
        for stop_orig_id in stop_orig_ids:
            paths.append(self.query_od_stops_time(
                stop_orig_id=stop_orig_id,
                stop_dest_id=stop_dest_id,
                depart_min=depart_min
            ))
        return paths

    def query_od_stops_time_multiple_dest(
            self,
            stop_orig_id: str,
            stop_dest_ids: list[str],
            depart_min: int,
    ):
        paths = []
        print("paths in dest func: ", stop_dest_ids)
        for stop_dest_id in stop_dest_ids:
            paths.append(self.query_od_stops_time(
                stop_orig_id=stop_orig_id,
                stop_dest_id=stop_dest_id,
                depart_min=depart_min,
            ))
        return paths

    def query_od_stops_time_multiple_ods(
            self,
            stop_orig_ids: list[str],
            stop_dest_ids: list[str],
            depart_min: int,
    ):
        paths = []
        print("paths in dest func: ", stop_dest_ids)
        for stop_dest_id in stop_dest_ids:
            for stop_orig_id in stop_orig_ids:
                paths.append(self.query_od_stops_time(
                    stop_orig_id=stop_orig_id,
                    stop_dest_id=stop_dest_id,
                    depart_min=depart_min,
                ))
        return paths