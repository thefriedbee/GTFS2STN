"""
Tools to show table information
"""
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder

from script.gtfs_controller import GTFSController


def show_stops_table(GTFS_OBJ: GTFSController):
    df, grid_options = GTFS_OBJ.display_table(fn="stops.txt")
    AgGrid(df, gridOptions=grid_options)


def show_static_table(
        GTFS_OBJ: GTFSController,
        table_name: str,
) -> None:
    df = GTFS_OBJ.dfs[table_name]
    # display configuration
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(
        paginationAutoPageSize=False,
        paginationPageSize=10
    )
    gb.configure_selection(
        selection_mode="disabled",
        use_checkbox=False
    )
    grid_options = gb.build()

    # render results in Streamlit
    selected_data = AgGrid(df, gridOptions=grid_options)

