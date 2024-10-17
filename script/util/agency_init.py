import os
from glob import glob


def init_agencies():
    global AGENCIES
    AGENCIES = glob(
        os.path.join("GTFS_inputs", "*"),
        recursive=False,
    )
    AGENCIES = [f.split('/')[-1] for f in AGENCIES]
    return AGENCIES
