'''
=======================================
EValuator: VIEWER COLOUR THEMES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import streamlit as st

# ====================
# Define constants
# ====================
# Named themes
THEMES: dict[str, dict] = {
    'Okabe-Ito': {
        'palette': ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7'],
        'highlight': '#FFD400', 'base': '#56B4E9', 'reliable': '#009E73', 'unreliable': '#D55E00', 'points': '#888888',
    },
    'Brewer Set2': {
        'palette': ['#66C2A5', '#FC8D62', '#8DA0CB', '#E78AC3', '#A6D854', '#FFD92F', '#E5C494'],
        'highlight': '#FFD400', 'base': '#8DA0CB', 'reliable': '#66C2A5', 'unreliable': '#FC8D62', 'points': '#888888',
    },
    'Viridis': {
        'palette': ['#440154', '#472D7B', '#3B528B', '#2C728E', '#21918C', '#5EC962', '#FDE725'],
        'highlight': '#FF4B4B', 'base': '#21918C', 'reliable': '#5EC962', 'unreliable': '#FDE725', 'points': '#909090',
    },
    'Grayscale': {
        'palette': ['#111111', '#333333', '#555555', '#777777', '#999999', '#BBBBBB', '#DDDDDD'],
        'highlight': '#FF4B4B', 'base': '#777777', 'reliable': '#111111', 'unreliable': '#BBBBBB', 'points': '#909090',
    },
    'Neon': {
        'palette': ['#FF00A0', '#00E5FF', '#7CFF00', '#FFD000', '#B000FF', '#FF5C00', '#00FF9C'],
        'highlight': '#FFFFFF', 'base': '#00E5FF', 'reliable': '#7CFF00', 'unreliable': '#FF5C00', 'points': '#00FF9C',
    },
}

# Set default theme to Okabe-Ito
DEFAULT_THEME = 'Okabe-Ito'

# Single-colour keys to use
ROLE_KEYS = ('highlight', 'base', 'reliable', 'unreliable', 'points')
UI_KEYS = ('scene_bg', 'paper_bg', 'grid', 'font')

# Session constants
_SESSION_NAME = 'viewer_theme_name'
_SESSION_OVERRIDES = 'viewer_theme_overrides'

# ====================
# Define functions for resolving active theme and Streamlit defaults
# ====================
def _st_defaults() -> dict:
    '''Streamlit default plot background/grid/font'''
    try:
        dark = st.context.theme.type == 'dark'
    except Exception:
        dark = False
    return {
        'scene_bg': '#0E1117' if dark else '#FFFFFF',
        'paper_bg': '#0E1117' if dark else '#FFFFFF',
        'grid': '#31333F' if dark else '#E5E5E5',
        'font': '#FAFAFA' if dark else '#31333F',
    }

def active() -> dict:
    '''
    Resolve theme following hierarchy: named theme -> chrome defaults -> user per-colour overrides
    '''
    name = st.session_state.get(_SESSION_NAME, DEFAULT_THEME)
    src = {**THEMES[DEFAULT_THEME], **THEMES.get(name, {})}  # fall back per-key so an incomplete custom theme still resolves
    theme = {**_st_defaults(), **src, 'palette': list(src['palette'])}
    for key, val in st.session_state.get(_SESSION_OVERRIDES, {}).items():
        if key == 'palette' and val:
            theme['palette'] = list(val)
        elif val:
            theme[key] = val
    return theme