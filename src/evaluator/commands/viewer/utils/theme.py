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
# Import shared theme constants
# ====================
from evaluator.utils.figures.theme import THEMES, DEFAULT_THEME, ROLE_KEYS, UI_KEYS

# ====================
# Define constants
# ====================
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