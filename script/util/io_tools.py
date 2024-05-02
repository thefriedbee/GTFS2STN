"""
Tools to process io
"""
from pathlib import Path
import zipfile


def extract_zipped_file(uploaded_file):
    pth_file = f"GTFS_inputs/{uploaded_file.name}"
    fn = uploaded_file.name.split('.')[0]
    with open(pth_file, "wb+") as f:
        f.write(uploaded_file.getbuffer())
    # next, unzip file to folder with same name
    pth_unzipped_folder = f"GTFS_inputs/{fn}"
    Path(pth_unzipped_folder).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pth_file, 'r') as zip_ref:
        zip_ref.extractall(pth_unzipped_folder)
    return pth_unzipped_folder


