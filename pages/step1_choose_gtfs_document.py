import streamlit as st

from script.gtfs_controller import GTFSController
import script.util.agency_init as agency_ut
import script.util.io_tools as io_tools

st.set_page_config(
    layout="wide",
    page_title="GTFS2STN",
    page_icon="🚌"
)
st.title("Step 1. Select GTFS documents or upload your document")
AGENCIES = agency_ut.init_agencies()

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
@st.cache_data
def load_gtfs(pth_unzipeed_folder):
    return GTFSController(root_dir=pth_unzipeed_folder)


# @st.cache_data()
def page_1():
    gtfs_obj = None
    col1, col2 = st.columns(2)
    with col1:
        # step (1). Option 1. Choose existed files
        file_option = st.selectbox(
            "Option 1: Select existed file for analysis",
            options=AGENCIES
        )
        if st.button('Confirm & Start Analysis!', on_click=call_back_b1) or st.session_state.b1_clicked:
            FOLDER_PTH = f"GTFS_inputs/{file_option}"
            with st.spinner('Processing GTFS documents...'):
                gtfs_obj = load_gtfs(FOLDER_PTH)
            st.success('GTFS successfully loaded!')
    with col2:
        # step (1). Option 2. Upload or select your GTFS document for analysis
        uploaded_file = st.file_uploader("Option 2: upload your GTFS document", type="zip")
        if uploaded_file is not None:
            io_tools.extract_zipped_file(uploaded_file)
            if st.button(
                    'Analyze uploaded zipped file!', on_click=call_back_b2
            ) or st.session_state.b2_clicked:
                try:
                    FOLDER_PTH = f"GTFS_inputs/{uploaded_file.name}"
                except Exception:
                    st.warning("Please upload zipped file in the first place.")

                with st.spinner('Processing GTFS documents...'):
                    try:
                        gtfs_obj = load_gtfs(FOLDER_PTH)
                        st.success('GTFS successfully loaded!')
                    except Exception:
                        st.warning(
                            "Cannot process uploaded file, please check if data formats & file names are correct")
        return gtfs_obj


def run_step_1():
    # results are recorded here in the global variable
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    st.session_state["GTFS_OBJ"] = page_1()
    print("step 1. GTFS_OBJ", st.session_state["GTFS_OBJ"])


run_step_1()
