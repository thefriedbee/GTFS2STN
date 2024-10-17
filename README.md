# GTFS2STN application

If you use the tool, consider cite the following paper:
- [*GTFS2STN: Analyzing GTFS Transit Data By Generating Spatiotemporal Transit Network*](https://arxiv.org/abs/2405.02760)

Load GTFS transit file and convert it to spatio-temporal network (STN) for shortest path analysis.

For current (beta) version, please visit: https://gtfs2stn.streamlit.app/
- Free-tier Streamlit Cloud is used for servicing this app. So, please wait for several seconds for rebooting.
As a service using a lot of memory, program may collapse if multiple users are using the application at the same time.

# Recent updates
- October, 2024 (version 2.0)
  - use rustworkx to substitute networkx for better running efficiency
  - write pytest code to safeguard core code