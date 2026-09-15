'''
=======================================
EValuator: VIEWER SETTINGS PANE
=======================================
'''

# ====================
# Import external dependencies
# ====================
import streamlit as st

# ====================
# Import internal viewer utilities
# ====================
from evaluator.commands.viewer.utils import theme as themeutil

# ====================
# Define constants
# ====================
_NAME = 'viewer_theme_name'
_OVERRIDES = 'viewer_theme_overrides'

# ====================
# Define functions for creating settings pane
# ====================
_CUSTOM = 'Custom'
_EDITABLE = (*themeutil.ROLE_KEYS, *themeutil.UI_KEYS)
_DOWNSAMPLE = '_downsample'  # persisted value, read by gallery and tomogram pages
_DOWNSAMPLE_WIDGET = '_downsample_widget'  # slider's own key, can be dropped by streamlit across page switches

# _sync_downsample: copies the slider's widget state into the persisted key, called on_change
def _sync_downsample() -> None:
    st.session_state[_DOWNSAMPLE] = st.session_state[_DOWNSAMPLE_WIDGET]

# render_downsample: sidebar slider for 3D volume downsample, shared session key so gallery and tomogram pages agree
def render_downsample() -> int:
    st.session_state.setdefault(_DOWNSAMPLE, 2)
    st.sidebar.slider(
        '3D downsample',
        min_value=1,
        max_value=8,
        value=st.session_state[_DOWNSAMPLE],
        key=_DOWNSAMPLE_WIDGET,
        on_change=_sync_downsample,
        help='Downsampling to use for volume rendering. Higher: reduced resolution but increased performance; lower: increased resolution but decreased performance.',
    )
    return st.session_state[_DOWNSAMPLE]

def render() -> None:
    with st.sidebar, st.expander(':material/palette: Customise theme', expanded=False):
        options = [*themeutil.THEMES, _CUSTOM]
        cur_name = st.session_state.get(_NAME, themeutil.DEFAULT_THEME)
        picked = st.selectbox('Default themes', options, index=options.index(cur_name) if cur_name in options else 0)
        if picked != cur_name:
            st.session_state[_NAME] = picked
            if picked == _CUSTOM:
                now = themeutil.active()  # start Custom from whatever is on screen
                st.session_state[_OVERRIDES] = {'palette': list(now['palette']), **{k: now[k] for k in _EDITABLE}}
            else:
                st.session_state[_OVERRIDES] = {}
            st.rerun()

        is_custom = picked == _CUSTOM
        active = themeutil.active()
        overrides = dict(st.session_state.get(_OVERRIDES, {}))
        ns = picked # widget key namespace

        st.caption('Palette')
        pal = list(active['palette'])
        _ROW = 4  # colour pickers per row, avoids swatches overlapping in the narrow sidebar
        for row_start in range(0, len(pal), _ROW):
            row = range(row_start, min(row_start + _ROW, len(pal)))
            for slot, col in zip(row, st.columns(len(row), gap='small')):
                pal[slot] = col.color_picker(str(slot + 1), value=pal[slot].upper(), key=f'pal_{ns}_{slot}', label_visibility='collapsed', disabled=not is_custom)
        if is_custom and [c.upper() for c in pal] != [c.upper() for c in active['palette']]:
            overrides['palette'] = pal

        for key in _EDITABLE:
            _name_col, _pick_col = st.columns([3, 1], vertical_alignment='center')
            _name_col.write(key.replace('_', ' ').title())
            new = _pick_col.color_picker(key, value=str(active[key]).upper(), key=f'c_{ns}_{key}', label_visibility='collapsed', disabled=not is_custom)
            if is_custom and new.upper() != str(active[key]).upper():
                overrides[key] = new

        if is_custom:
            if overrides != st.session_state.get(_OVERRIDES, {}):
                st.session_state[_OVERRIDES] = overrides
                st.rerun()
            if st.button('Reset custom colours', use_container_width=True):
                for k in [k for k in st.session_state if k.startswith(('pal_', 'c_'))]:
                    del st.session_state[k]  # drop picker state so they rehydrate
                st.session_state[_NAME] = themeutil.DEFAULT_THEME
                st.session_state[_OVERRIDES] = {}
                st.rerun()
