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
def _pick(container, label: str, current: str, key: str, overrides: dict, name: str) -> None:
    new = container.color_picker(label, value=str(current).upper(), key=key)
    if new.upper() != str(current).upper():
        overrides[name] = new

def render() -> None:
    with st.bottom:
        with st.popover(':material/palette: Theme', use_container_width=False):
            names = list(themeutil.THEMES)
            cur_name = st.session_state.get(_NAME, themeutil.DEFAULT_THEME)
            picked = st.selectbox('Theme', names, index=names.index(cur_name) if cur_name in names else 0)
            if picked != cur_name:
                st.session_state[_NAME] = picked
                st.session_state[_OVERRIDES] = {}
                st.rerun()

            active = themeutil.active()
            overrides = dict(st.session_state.get(_OVERRIDES, {}))
            # widget keys carry the theme name so switching theme instantiates fresh pickers (no stale state)
            ns = picked

            st.caption('Series palette')
            pal = list(active['palette'])
            for slot, col in zip(range(len(pal)), st.columns(len(pal))):
                pal[slot] = col.color_picker(f'{slot + 1}', value=pal[slot].upper(), key=f'pal_{ns}_{slot}', label_visibility='collapsed')
            if [c.upper() for c in pal] != [c.upper() for c in active['palette']]:
                overrides['palette'] = pal

            st.caption('Roles')
            role_cols = st.columns(2)
            for i, key in enumerate(themeutil.ROLE_KEYS):
                _pick(role_cols[i % 2], key.title(), active[key], f'role_{ns}_{key}', overrides, key)

            st.caption('Chrome')
            chrome_cols = st.columns(2)
            for i, key in enumerate(themeutil.CHROME_KEYS):
                _pick(chrome_cols[i % 2], key.replace('_', ' ').title(), active[key], f'chrome_{ns}_{key}', overrides, key)

            if overrides != st.session_state.get(_OVERRIDES, {}):
                st.session_state[_OVERRIDES] = overrides
                st.rerun()
            if st.session_state.get(_OVERRIDES) and st.button('Reset overrides', use_container_width=True):
                for k in [k for k in st.session_state if k.startswith(('pal_', 'role_', 'chrome_'))]:
                    del st.session_state[k]  # drop picker state
                st.session_state[_OVERRIDES] = {}
                st.rerun()
