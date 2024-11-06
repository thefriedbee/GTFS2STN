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


def form1():
    FOLDER_PTH = None
    with st.form(key="existing_form"):
        # step (1). Option 1. Choose existed files
        file_option = st.selectbox(
            "Option 1: Select existed file for analysis",
            options=AGENCIES
        )
        b1_submit_button = st.form_submit_button('Confirm & Start Analysis!', on_click=call_back_b1)
        if b1_submit_button or st.session_state.b1_clicked:
            FOLDER_PTH = f"GTFS_inputs/{file_option}"
    return FOLDER_PTH


def form2():
    FOLDER_PTH = None
    with st.form(key="upload_form"):
        uploaded_file = st.file_uploader("Option 2: upload your GTFS document", type="zip")
        b2_submit_button = st.form_submit_button('Analyze uploaded zipped file!', on_click=call_back_b2)
        # logic to unzip submitted file
        if b2_submit_button or st.session_state.b2_clicked:
            io_tools.extract_zipped_file(uploaded_file)
            FOLDER_PTH = f"GTFS_inputs/{uploaded_file.name}"
    return FOLDER_PTH


def upload_data(FOLDER_PTH: str):
    confirm_message = st.empty()
    print("FOLDER_PTH", FOLDER_PTH)
    # with st.spinner('Processing GTFS documents...'):
    #     try:
    #         load_gtfs(FOLDER_PTH)
    #         confirm_message.success('GTFS successfully loaded!')
    #     except Exception:
    #         confirm_message.warning(
    #             "Cannot process uploaded file, please check if data formats & file names are correct")
    if FOLDER_PTH is None:
        confirm_message.error('folder path is None')
    else:
        FOLDER_PTH = FOLDER_PTH.split('.')[0]
        load_gtfs(FOLDER_PTH)
        confirm_message.success('GTFS successfully loaded!')


# step (2). load data
# @st.cache_data
def load_gtfs(pth_unzipeed_folder):
    gtfs_obj = GTFSController(root_dir=pth_unzipeed_folder)
    st.session_state["GTFS_OBJ"] = gtfs_obj


def page_1():
    FOLDER_PTH1, FOLDER_PTH2 = None, None
    col1, col2 = st.columns(2)
    with col1:
        FOLDER_PTH1 = form1()
    with col2:
        FOLDER_PTH2 = form2()
    
    # process data if either form is clicked
    if st.session_state.b1_clicked:
        print("existing form clicked (left)")
        upload_data(FOLDER_PTH1)
    if st.session_state.b2_clicked:
        print("upload form clicked (right)")
        upload_data(FOLDER_PTH2)
    print("FOLDER_PTH1", FOLDER_PTH1)
    print("FOLDER_PTH2", FOLDER_PTH2)


@st.fragment()
def run_step_1():
    # results are recorded here in the global variable
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    if "GRAPH_OBJ" not in st.session_state.keys():
        st.session_state["GRAPH_OBJ"] = None
    page_1()
    print("step 1. GTFS_OBJ", st.session_state["GTFS_OBJ"])


run_step_1()
