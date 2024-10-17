"""
Helper method to create transit network...
"""
import numpy as np
import pandas as pd

from script.GTFSGraph import GTFSGraph, GTFSEdge, EdgeMode


# generate skeleton nodes over time-space for one stop
def generate_ts_nodes(
        stop_ser: pd.Series,  # one bus stop
        G_obj: GTFSGraph,
        t0: int = 0, t1: int = 1440, t_step: int = 15
) -> None:
    stop_dict = stop_ser[['stop_id', 'stop_lat', 'stop_lon']].to_dict()
    times_info = np.arange(t0, t1 + 1, t_step).tolist()
    G_obj.add_skeleton_nodes(stop_dict, times_info)


# add all skeleton nodes from stops.txt dataframe
def add_nodes_all_stops(
        stops: pd.DataFrame,
        G_obj: GTFSGraph,
        t_step: int = 15
) -> None:
    print("total number of stops:", stops.shape)
    stops.apply(generate_ts_nodes, axis=1, G_obj=G_obj, t_step=t_step)


# scanning all transit trips and add links between nodes
def generate_ts_edges(
        stop_times: pd.DataFrame,
        G_obj: GTFSGraph
) -> None:
    stop_times['arrive_minute'] = pd.to_timedelta(stop_times['arrival_time']).dt.total_seconds() / 60
    stop_times['departure_minute'] = pd.to_timedelta(stop_times['departure_time']).dt.total_seconds() / 60
    # set time info to whole minute
    stop_times['arrive_minute'] = stop_times['arrive_minute'].astype("float32")
    stop_times['departure_minute'] = stop_times['departure_minute'].astype("float32")

    stop_times = stop_times[~stop_times['arrive_minute'].isna()]
    stop_times = stop_times[~stop_times['departure_minute'].isna()]

    # ser_1trip_stops: trips stops of one trip_id
    stop_ids = stop_times['stop_id'].tolist()
    arr_ts = stop_times['arrive_minute'].tolist()

    for i in range(len(stop_ids) - 1):
        # stop names and arrival times
        stop_i, stop_j = stop_ids[i], stop_ids[i + 1]
        ti, tj = arr_ts[i], arr_ts[i + 1]
        # node ids
        start_nid = G_obj.query_node_or_create(stop_id=stop_i, tod=ti)
        end_nid = G_obj.query_node_or_create(stop_id=stop_j, tod=tj)

        travel_time = tj - ti
        # only add edge if travel time is positive...
        if travel_time >= 0:
            G_obj.add_edge(
                node_a=start_nid, node_b=end_nid,
                properties=GTFSEdge(
                    start_node=start_nid, end_node=end_nid,
                    trip_t=travel_time, wait_t=0, walk_t=0,
                    mode=EdgeMode.TRIP
                )
            )


# add all edges+nodes from stop_times.txt dataframe
def add_edges_all_stop_times(
        stop_times: pd.DataFrame,
        G_obj: GTFSGraph
):
    stop_times.groupby(["trip_id"]).apply(generate_ts_edges, G_obj)


# # visualize one stop'fs information over time
# def plot_one_stop_over_time(G_subgraph):
#     fig, ax = plt.subplots(1, 1, figsize=(40, 4))
#
#     def my_func(e):
#         return int(e.split('_')[-1])
#
#     nodes = sorted(list(G_subgraph.nodes()), key=my_func)
#     edges = sorted(list(G_subgraph.edges()))
#     pos = {node: (int(node.split('_')[-1]), random.random() - 0.5) for node in nodes}
#     nx.draw(G_subgraph, pos=pos, node_size=10, ax=ax)
#     plt.axis("on")
#     ax.tick_params(left=True, bottom=True, labelleft=False, labelbottom=True)
#     ax.set_xlim(-10, 1450)
#     ax.set_ylim(-1, 1)
#     ax.set_xticks([i * 60 for i in range(24 + 1)])
#     ax.set_xticklabels([str(i) for i in range(24 + 1)], fontsize=40)
#     ax.set_xlabel("Hour of the day", fontsize=40)
#     plt.grid(True)
#     return ax
