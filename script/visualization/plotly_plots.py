"""
For plotly.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from PIL import Image as PImage
import plotly.graph_objects as go
from plotly import tools
import plotly.offline

import plotly.express as px
import plotly.graph_objects as go
import contextily as cx
import xyzservices.providers as xyz


def get_lines_from_edges_df(edges_df):
    x_lines = {"transit": list(), "walk": list(), "wait": list()}
    y_lines = {"transit": list(), "walk": list(), "wait": list()}
    z_lines = {"transit": list(), "walk": list(), "wait": list()}

    # create the coordinate list for the lines
    for i, row in edges_df.iterrows():
        m = row["mode"]
        x_lines[m].append(row["lon0"])
        y_lines[m].append(row["lat0"])
        z_lines[m].append(row["time0"])
        x_lines[m].append(row["lon1"])
        y_lines[m].append(row["lat1"])
        z_lines[m].append(row["time1"])
        x_lines[m].append(None)
        y_lines[m].append(None)
        z_lines[m].append(None)
    return x_lines, y_lines, z_lines


def get_node_borders(
        nodes_df: pd.DataFrame
):
    bds_minx = nodes_df['lon'].min()
    bds_maxx = nodes_df['lon'].max()
    bds_miny = nodes_df['lat'].min()
    bds_maxy = nodes_df['lat'].max()
    print("map bounds:", bds_minx, bds_maxx, bds_miny, bds_maxy)
    return bds_minx, bds_maxx, bds_miny, bds_maxy


def get_background_map(
        nodes_df: pd.DataFrame
) -> plt.Axes:
    bds_minx, bds_maxx, bds_miny, bds_maxy = get_node_borders(nodes_df)

    ghent_img, ghent_ext = cx.bounds2img(
        bds_minx,  # west
        bds_miny,  # south
        bds_maxx,  # east
        bds_maxy,  # north
        ll=True,
        source=cx.providers.OpenStreetMap.Mapnik
    )
    print(ghent_img.shape)
    print(ghent_ext)

    fig, ax = plt.subplots(1, 1, figsize=(5, 5), dpi=100)
    plt.imshow(ghent_img, extent=ghent_ext)
    plt.axis('off')
    return ghent_img


def create_rgb_surface(
        rgb_img,
        Z,
        bds_minx, bds_maxx, bds_miny, bds_maxy,
        **kwargs
):
    N_lat, N_lon = rgb_img.shape[0], rgb_img.shape[1]
    print("rgb_img shape:", rgb_img.shape)
    rgb_img = rgb_img[::-1, :, :]
    # rgb_img = rgb_img.swapaxes(0, 1)[:, ::-1, :]
    print("rgb_img shape:", rgb_img.shape)

    eight_bit_img = PImage.fromarray(rgb_img).convert('P', palette='WEB', dither=None)
    idx_to_color = np.array(eight_bit_img.getpalette()).reshape((-1, 3))
    # print("idx_to_color:", idx_to_color.shape)
    # print(idx_to_color)
    colorscale = [[i / 255.0, "rgb({}, {}, {})".format(*rgb)] for i, rgb in enumerate(idx_to_color)]
    return go.Surface(
        x=np.linspace(bds_minx, bds_maxx, N_lon),  # lon
        y=np.linspace(bds_miny, bds_maxy, N_lat),  # lat
        z=np.full(rgb_img.shape[:2], Z),
        surfacecolor=np.array(eight_bit_img),
        cmin=0,
        cmax=255,
        colorscale=colorscale,
        showscale=False,
        **kwargs
    )


def generate_3d_plotly(
        edges_df,
        nodes_df,
        Z=1000,
):
    edges_coords = get_lines_from_edges_df(edges_df)
    bds_minx, bds_maxx, bds_miny, bds_maxy = get_node_borders(nodes_df)
    # the background image
    ghent_img = get_background_map(nodes_df)

    surf = create_rgb_surface(
        ghent_img,
        Z=Z,
        bds_minx=bds_minx,
        bds_maxx=bds_maxx,
        bds_miny=bds_miny,
        bds_maxy=bds_maxy,
    )
    fig = go.Figure([
        go.Scatter3d(
            x=edges_coords[0]["walk"], y=edges_coords[1]["walk"], z=edges_coords[2]["walk"],
            opacity=0.8,
            line={'color': 'grey'},
            mode="lines", name='walking edges'
        ),
        go.Scatter3d(
            x=edges_coords[0]["wait"], y=edges_coords[1]["wait"], z=edges_coords[2]["wait"],
            opacity=0.8,
            line={'color': 'black'},
            mode="lines", name='waiting edges'
        ),
        go.Scatter3d(
            x=edges_coords[0]["transit"], y=edges_coords[1]["transit"], z=edges_coords[2]["transit"],
            opacity=0.8,
            line={'color': 'red'},
            mode="lines", name='transit edges'
        ),

        go.Scatter3d(
            x=nodes_df['lon'], y=nodes_df['lat'],
            z=nodes_df['time'],
            line={'color': 'green'},
            opacity=0.2,
            mode="markers", name='Spatiotemporal nodes'
        ),
    ])

    fig.update_traces(line_width=5)
    fig.update_layout(
        title='3d network viz',
        scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Time of the day (min)'
        ),
        width=1000, height=1000,
        margin=dict(t=40, r=0, l=20, b=20),
        showlegend=True,
        legend=dict(
            yanchor="top", y=0.80,
            xanchor="left", x=0.10
        ))
    fig.add_trace(surf)
    fig.update_scenes(camera_projection_type='orthographic')
    return fig
