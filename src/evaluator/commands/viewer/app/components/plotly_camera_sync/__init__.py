'''
=======================================
EValuator: PLOTLY CAMERA SYNC CUSTOM COMPONENT
=======================================
Custom component to bridge Plotly's camera-drag (relayout) and mesh-click events with Streamlit app
'''

# ====================
# Import external dependencies
# ====================
from pathlib import Path

import plotly.graph_objects as go
import streamlit.components.v1 as components

# ====================
# Declare the static component
# ====================
_component = components.declare_component(
    'plotly_camera_sync',
    path=str(Path(__file__).parent / 'static'),
)

# ====================
# Define Python-side wrapper
# ====================
def plotly_view(fig: go.Figure, interactive: bool, camera: dict | None, key: str) -> dict | None:
    '''
    Renders fig using the custom component, returning {"clicked_curve": int|None, "camera": dict|None} after a click or drag; returns None before any interaction has happened
    '''
    return _component(
        figure=fig.to_json(),
        interactive=interactive,
        camera=camera,
        key=key,
        default=None,
    )
