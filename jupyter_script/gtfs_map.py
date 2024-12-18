import os
import sys
import numpy as np
from datetime import datetime

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import itertools

plt.style.use(['science','ieee'])

# import my own modules
sys.path.append("..")
import script.gtfs_controller as gtfs
import script.analysis.geo_analysis as geo_analysis
from script.GTFSGraph import GTFSGraph
from script.gtfs_controller import (
    build_network,
    filter_service_id_by_date,
    filter_service_id_by_date_v2,
)


def get_sel_ids(obj, the_date):
    sel_sids = set()
    try:
        services = obj.dfs["calendar.txt"].copy()
        services = filter_service_id_by_date(
            services=services,
            the_date=the_date
        )
        # selected service ids
        sel_sids.update(services["service_id"].tolist())
        print(f"after 'calendar.txt': {len(sel_sids)}")
    except:
        print("calendar.txt not found or failed to process!")
    
    try:
        services = obj.dfs["calendar_dates.txt"].copy()
        sids_included, sids_excluded = filter_service_id_by_date_v2(
            services=services,
            the_date=the_date
        )
        sel_sids.update(sids_included)
        sel_sids.difference_update(set(sids_excluded))
        print(f"after 'calendar_dates.txt': {len(sel_sids)}")
    except:
        print("calendar_dates.txt not found to extract service ids!")
    return list(sel_sids)


def analyze_od_tt(obj, stops, orig_loc, dest_loc, depart_min, bw_mile, cutoff):
    stop_orig_ids, stop_orig_acc_time = geo_analysis.find_nei_stops_given_coords(
        stops = stops,
        locs = [orig_loc],
        bw_mile = bw_mile,
        return_all_neighbors=True
    )
    stop_dest_ids, stop_dest_acc_time = geo_analysis.find_nei_stops_given_coords(
        stops = stops,
        locs = [dest_loc],
        bw_mile = bw_mile,
        return_all_neighbors=True
    )
    
    all_paths, acc_times = obj.query_od_stops_time(
        stop_orig_ids=stop_orig_ids,
        stop_dest_ids=stop_dest_ids,
        depart_min=depart_min,  # e.g., departure at 10 AM
        acc_orig_times=stop_orig_acc_time,
        acc_dest_times=stop_dest_acc_time,
        cutoff=cutoff,
        return_costs=True
    )
    
    # print("all_paths:", all_paths)
    if len(all_paths) == 1 and all_paths[0] == []:
        return -1, -1, -1, -1
        # raise ValueError("no path found within the cutoff time (loaded wrong GTFS data, wrong calendar?)...")

    travel_ts = []
    wait_ts, walk_ts, total_ts = [], [], []        
    for i, pth in enumerate(all_paths):
        if pth == []:
            continue
        transit_t, wait_t, walk_t = obj.get_travel_time_info_from_pth(
            obj.G, pth,
        )
        acc_time = acc_times[i]
        travel_ts.append(transit_t)
        wait_ts.append(wait_t)
        walk_ts.append(walk_t + acc_time)
        tt = transit_t + wait_t + walk_t + acc_time
        total_ts.append(tt)

    def argmin(lst):
        return lst.index(min(lst))
    path_index = argmin(total_ts)
    
    return (travel_ts[path_index], wait_ts[path_index], 
            walk_ts[path_index], total_ts[path_index])


def graph_query_all_times(
    obj,  # GTFS controller
    stops,
    coords: list[tuple[float, float]], 
    depart_min: float,
    cutoff: float,
    bw_mile: float = 0.5
) -> list[float]:
    times = []
    ODs = list(itertools.permutations(coords, 2))
    ODs = [OD for OD in ODs if OD[0] != OD[1]]
    ttt_lst = []
    tts_moving = []  # either walking or traveling
    for orig_coord, dest_coord in ODs:
        # try:
        tt_travel, tt_wait, tt_walk, ttt = analyze_od_tt(
            obj,
            stops,
            orig_loc = orig_coord,
            dest_loc = dest_coord,
            depart_min = depart_min,
            bw_mile = bw_mile,
            cutoff=cutoff
        )
        ttt_lst.append(ttt)
        tts_moving.append(tt_travel+tt_walk)
        # except:
        #     print(f"path not found: {orig_coord}, {dest_coord}")
        #     ttt_lst.append(-1)
        #     tts_moving.append(-1)
        print(".", end="")
    print()
    return ttt_lst, tts_moving


def plot_performance(ttt_google, ttt_gtfs, ax=None, color="black", label=None):
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(4, 4), dpi=200)

    ax.scatter(ttt_google, ttt_gtfs, label="NY MTC", alpha=0.5, s=10, color=color)
    ax.axline([0, 0], [120, 120], color="black")
    ax.set_title("Google vs. GTFS")
    ax.set_xlabel("Google Travel Time (min)")
    ax.set_ylabel("GTFS Travel Time (min)")
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 120)
    return ax




