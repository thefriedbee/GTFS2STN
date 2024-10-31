import streamlit as st

import script.util.table_viewer as table_ut
import script.util.map_viewer as map_ut

st.set_page_config(
    layout="wide",
    page_title="GTFS2STN",
    page_icon="🚌"
)


def page_2_init():
    global GTFS_OBJ
    if "GTFS_OBJ" not in st.session_state.keys():
        st.session_state["GTFS_OBJ"] = None
    GTFS_OBJ = st.session_state["GTFS_OBJ"]
    print("step2 GTFS_OBJ:", GTFS_OBJ)


@st.fragment()
def page_2_2():
    st.title("Step 2. Table Viewer")
    # ["agency.txt", "stops.txt", "calendar.txt", "calendar_dates.txt",
    #  "routes.txt", "shapes.txt", "stop_times.txt", "trips.txt"]
    all_tabs = st.tabs(GTFS_OBJ.file_names)  # one tab for each table

    # provide designated visualization for each type of table
    with all_tabs[0]:  # "agency.txt"
        try:
            table_ut.show_static_table(GTFS_OBJ, 'agency.txt')
        except:
            st.subheader("'agency.txt' are not found!!")

    with all_tabs[1]:  # "stops.txt"
        col1, col2 = st.columns(2)
        with col1:
            if st.checkbox("display table", key="stops_table"):
                table_ut.show_stops_table(GTFS_OBJ)
        with col2:
            if st.checkbox("display map", key="stops_map"):
                map_ut.show_stops_map(GTFS_OBJ)

    with all_tabs[2]:  # calendar
        table_ut.show_static_table(GTFS_OBJ, 'calendar.txt')

    with all_tabs[3]:  # calendar dates
        try:
            table_ut.show_static_table(GTFS_OBJ, 'calendar_dates.txt')
        except:
            st.subheader("'calendar_dates.txt' are not found!")

    with all_tabs[4]:  # routes
        try:
            table_ut.show_static_table(GTFS_OBJ, 'routes.txt')
        except:
            st.subheader("'routes.txt' are not found!")

    with all_tabs[5]:  # shapes
        # try:
        col1, col2 = st.columns(2)
        with col1:
            if st.checkbox("display table", key="shapes_table"):
                table_ut.show_static_table(GTFS_OBJ, 'shapes.txt')
        with col2:
            if st.checkbox("display map", key="shapes_map"):
                GTFS_OBJ.display_routes_map()

    with all_tabs[6]:  # stop_times
        try:
            table_ut.show_static_table(GTFS_OBJ, 'stop_times.txt')
        except:
            st.subheader("'stop_times.txt' are not found!")

    with all_tabs[7]:  # trips
        try:
            table_ut.show_static_table(GTFS_OBJ, 'trips.txt')
        except:
            st.subheader("'trip.txt' are not found!")


page_2_init()
page_2_2()

