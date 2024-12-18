"""
Test to safeguard the graph behaviors...
"""
import pandas as pd
import numpy as np

from script.GTFSGraph import GTFSGraph, GTFSEdge, EdgeMode


def test_query_node_or_create():
    g = GTFSGraph()
    g.query_node_or_create(stop_id="A", tod=100)
    g.query_node_or_create(stop_id="A", tod=100)
    g.query_node_or_create(stop_id="B", tod=200)
    g.query_node_or_create(stop_id="C", tod=100.4)
    g.query_node_or_create(stop_id="C", tod=100.4)
    g.query_node_or_create(stop_id="B", tod=200)
    assert str(g.nodes_name_map) == "{'A_100': 0, 'B_200': 1, 'C_100': 2}"
    assert str(g.G.nodes()) == "[<A,100,A_100>, <B,200,B_200>, <C,100,C_100>]"


def test_add_skeleton_nodes():
    g = GTFSGraph()
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "R101"},
        times_info=[10, 20, 30, 45, 60]
    )

    # print nodes info
    print("nodes name map:")
    print(g.nodes_name_map)
    assert str(g.nodes_name_map) == "{'R101_10': 0, 'R101_20': 1, 'R101_30': 2, 'R101_45': 3, 'R101_60': 4}"

    print("nodes time map:")
    print(g.nodes_time_map)
    assert str(g.nodes_time_map) == "{'R101': SortedSet([10, 20, 30, 45, 60])}"


def test_add_edge():
    g = GTFSGraph()
    node_a_id = g.query_node_or_create(stop_id="A", tod=100)
    node_b_id = g.query_node_or_create(stop_id="B", tod=200)
    node_c_id = g.query_node_or_create(stop_id="C", tod=100.4)
    # add edge directly without creating nodes?
    g.add_edge(
        node_a=node_a_id, node_b=node_b_id,
        properties=GTFSEdge(
            start_node=node_a_id, end_node=node_b_id,
            trip_t=100, wait_t=0, walk_t=0,
            mode=EdgeMode.TRIP
        )
    )
    g.add_edge(
        node_a=node_b_id, node_b=node_c_id,
        properties=GTFSEdge(
            start_node=node_b_id, end_node=node_c_id,
            trip_t=0, wait_t=0, walk_t=0,
            mode=EdgeMode.TRIP
        )
    )
    assert str(g.G.edges()) == "[<0-1, (100,0,0), EdgeMode.TRIP>, <1-2, (0,0,0), EdgeMode.TRIP>]"

    # print nodes info (make sure they are not changed...)
    print("nodes name map:")
    print(g.nodes_name_map)
    assert str(g.nodes_name_map) == "{'A_100': 0, 'B_200': 1, 'C_100': 2}"

    print("nodes time map:")
    print(g.nodes_time_map)
    assert str(g.nodes_time_map) == "{'A': SortedSet([100]), 'B': SortedSet([200]), 'C': SortedSet([100])}"


def test_add_edges_within_same_stops():
    g = GTFSGraph()
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "R101"},
        times_info=[10, 20, 40]
    )
    g.add_edges_within_same_stops()

    print("all edges payloads...")
    assert str(g.G.edges()) == "[<0-1, (0,10,0), EdgeMode.WAIT>, <1-2, (0,20,0), EdgeMode.WAIT>]"
    edge_indices = g.G.edge_indices()
    print("edge indices...")
    print(str(edge_indices) == "EdgeIndices[0, 1, 2]")


def test_add_hyper_nodes1():
    g = GTFSGraph()
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "R101"},
        times_info=[10, 20]
    )
    # g.add_edges_within_same_stops()
    g.add_hyper_nodes()
    print(g.G.nodes())
    assert str(g.G.nodes()) == "[<R101,10,R101_10>, <R101,20,R101_20>, <R101,-1,R101_D>]"
    assert str(g.G.edges()) == "[<0-2, (0,0.1,0), EdgeMode.ARRIVED>, <1-2, (0,0.1,0), EdgeMode.ARRIVED>]"
    print(g.G.edge_index_map())


def test_add_hyper_nodes2():
    g = GTFSGraph()
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "R101"},
        times_info=[10, 20]
    )
    g.add_edges_within_same_stops()
    g.add_hyper_nodes()
    print(g.G.nodes())
    print(g.G.edges())
    assert str(g.G.edges()) == "[<0-1, (0,10,0), EdgeMode.WAIT>, <0-2, (0,0.1,0), EdgeMode.ARRIVED>, <1-2, (0,0.1,0), EdgeMode.ARRIVED>]"
    assert str(g.G.nodes()) == "[<R101,10,R101_10>, <R101,20,R101_20>, <R101,-1,R101_D>]"
    print(g.G.edge_index_map())


def test_add_edges_walkable_stops():
    g = GTFSGraph()
    # add nodes to graph...
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "A"},
        times_info=[10, 20]
    )
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "B"},
        times_info=[10, 20]
    )

    # add walking links...
    df = pd.DataFrame([
        # stop_id, neighbors, walking distance
        ["A", np.array([0, 1]), np.array([0, 0.1])],
        ["B", np.array([0, 1]), np.array([0.1, 0])]
    ])
    df.columns = ["stop_id", "neighbors", "dists"]
    print(df)

    # add edges to graph...
    g.add_edges_walkable_stops(stops_b=df, walk_speed=1)
    g.add_edges_within_same_stops()
    g.add_hyper_nodes()
    print(g.G.nodes())
    print(g.G.edges())
    print("num. of edges: ", len(g.G.edges()))
    assert str(g.G.nodes()) == "[<A,10,A_10>, <A,20,A_20>, <B,10,B_10>, <B,20,B_20>, <B,16,B_16>, <B,26,B_26>, <A,16,A_16>, <A,26,A_26>, <A,-1,A_D>, <B,-1,B_D>]"


def test_query_origin_stop_time():
    g = GTFSGraph()
    # add nodes to graph...
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "A"},
        times_info=[10, 20]
    )
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "B"},
        times_info=[10, 20]
    )
    # add walking links...
    df = pd.DataFrame([
        # stop_id, neighbors, walking distance
        ["A", np.array([0, 1]), np.array([0, 0.1])],
        ["B", np.array([0, 1]), np.array([0.1, 0])]
    ])
    df.columns = ["stop_id", "neighbors", "dists"]

    # add walking links...
    df = pd.DataFrame([
        # stop_id, neighbors, walking distance
        ["A", np.array([0, 1]), np.array([0, 0.1])],
        ["B", np.array([0, 1]), np.array([0.1, 0])]
    ])
    df.columns = ["stop_id", "neighbors", "dists"]

    # add edges to graph...
    g.add_edges_walkable_stops(stops_b=df, walk_speed=1)
    g.add_edges_within_same_stops()
    g.add_hyper_nodes()

    res_paths, res_dists = g.query_origin_stop_time(
        stops_df=df,
        stop_id="A",
        depart_min=9,
        walk_speed=1,
        cutoff=1000
    )
    print()
    print("all nodes:", g.G.nodes())
    print("all edges:", g.G.edges())
    print("res paths:", res_paths)
    print("res dists:", res_dists)
    print("res paths len:", len(res_paths))
    assert 1 == 1


def test_query_od_stops_time():
    g = GTFSGraph()
    # add nodes to graph...
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "A"},
        times_info=[10, 20]
    )
    g.add_skeleton_nodes(
        stop_dict={"stop_id": "B"},
        times_info=[10, 20]
    )
    # add walking links...
    df = pd.DataFrame([
        # stop_id, neighbors, walking distance
        ["A", np.array([0, 1]), np.array([0, 0.1])],
        ["B", np.array([0, 1]), np.array([0.1, 0])]
    ])
    df.columns = ["stop_id", "neighbors", "dists"]

    # add walking links...
    df = pd.DataFrame([
        # stop_id, neighbors, walking distance
        ["A", np.array([0, 1]), np.array([0, 0.1])],
        ["B", np.array([0, 1]), np.array([0.1, 0])]
    ])
    df.columns = ["stop_id", "neighbors", "dists"]

    # add edges to graph...
    g.add_edges_walkable_stops(stops_b=df, walk_speed=1)
    g.add_edges_within_same_stops()
    g.add_hyper_nodes()

    pth = g.query_od_stops_time(
        stop_orig_ids=["A"],
        stop_dest_ids=["B"],
        depart_min=9,
        cutoff=1000
    )
    print("all nodes:", g.G.nodes())
    print("all edges:", g.G.edges())
    print(pth)
    assert pth == [10, 0, 4, 9]


