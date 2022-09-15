import sys
import os
import time

import streamlit as st
import zipfile
from pathlib import Path

sys.path.append("..")
from script.gtfs_controller import GTFSController
import script.utils as ut

# st.set_page_config(layout="wide")
st.write("Step 1. Select GTFS documents or upload your document")
AGENCIES = ut.init_agencies()

# init all session states at the beginning
if 'b1_clicked' not in st.session_state:
    st.session_state.b1_clicked = False
if 'b2_clicked' not in st.session_state:
    st.session_state.b2_clicked = False


def call_back_b1():
    st.session_state.b1_clicked = True


def call_back_b2():
    st.session_state.b2_clicked = True


# step (2). load data
@st.cache(suppress_st_warning=True, show_spinner=False)
def load_gtfs(pth_unzipeed_folder):
    return GTFSController(root_dir=pth_unzipeed_folder)


# @st.cache(suppress_st_warning=True)
def page_1():
    gtfs_obj = None
    col1, col2 = st.columns(2)
    with col1:
        # step (1). Option 1. Choose existed files
        file_option = st.selectbox(
            "Select existed file for analysis 'State_City_Agency'",
            options=AGENCIES)
    with col2:
        # step (1). Option 2. Upload or select your GTFS document for analysis
        uploaded_file = st.file_uploader("Or: upload your GTFS document", type="zip")
        pth_unzipeed_folder = None
        if uploaded_file is not None:
            # To read file as bytes:
            # zipped_data = StringIO(uploaded_file.getvalue())
            # save data
            # with zipfile.ZipFile("../GTFS_inputs/temp.zip", mode="w") as archive:
            #      archive.write(uploaded_file)
            pth = f"GTFS_inputs/"
            pth_file = f"GTFS_inputs/{uploaded_file.name}"
            fn = uploaded_file.name.split('.')[0]
            with open(pth_file, "wb+") as f:
                f.write(uploaded_file.getbuffer())
            # next, unzip file to folder with same name
            pth_unzipeed_folder = f"GTFS_inputs/{fn}"
            Path(pth_unzipeed_folder).mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(pth_file, 'r') as zip_ref:
                zip_ref.extractall(pth_unzipeed_folder)
    with col1:
        if st.button('Confirm & Start Analysis!', on_click=call_back_b1) or st.session_state.b1_clicked:
            FOLDER_PTH = f"GTFS_inputs/{file_option}"
            with st.spinner('Processing GTFS documents...'):
                gtfs_obj = load_gtfs(FOLDER_PTH)  # GTFS_OBJ
            st.success('GTFS successfully loaded!')
    with col2:  # analyze uploaded file
        if st.button('Analyze uploaded zipped file!', on_click=call_back_b2) or st.session_state.b2_clicked:
            FOLDER_PTH = pth_unzipeed_folder
            with st.spinner('Processing GTFS documents...'):
                gtfs_obj = load_gtfs(FOLDER_PTH)  # GTFS_OBJ
            st.success('GTFS successfully loaded!')
    return gtfs_obj


def init_page_1():
    # results are recorded here in the global variable
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    st.session_state["GTFS_OBJ"] = page_1()
    print("step 1. GTFS_OBJ", st.session_state["GTFS_OBJ"])


init_page_1()
