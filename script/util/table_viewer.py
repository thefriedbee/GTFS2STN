"""
Tools to show table information
"""
import streamlit as st

from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

from script.gtfs_controller import GTFSController


def show_stops_table(GTFS_OBJ: GTFSController):
    df, grid_options = GTFS_OBJ.display_table(fn="stops.txt")
    AgGrid(df, gridOptions=grid_options)


def show_static_table_simple(
        GTFS_OBJ: GTFSController,
        table_name: str,
) -> None:
    df = GTFS_OBJ.dfs[table_name]
    st.dataframe(df)


def show_static_table(
        GTFS_OBJ: GTFSController,
        table_name: str,
) -> None:
    df = GTFS_OBJ.dfs[table_name]

    # display configuration
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(
        paginationAutoPageSize=False,
        paginationPageSize=15
    )
    gb.configure_selection(
        selection_mode="disabled",
        use_checkbox=False
    )
    # gridOptions = {'autoSizeColumns': ['allColumns']}
    # gb.configure_grid_options(**gridOptions)
    other_options = {
        'suppressColumnVirtualisation': True,
        'autoSizeColumns': ['allColumns'],
        # 'defaultColDef': {'fontSize': 8}
    }
    gb.configure_grid_options(**other_options)
    grid_options = gb.build()

    # render results in Streamlit
    selected_data = AgGrid(
        df,
        gridOptions=grid_options,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW,
        style={'font-size': '7px'}
    )

