'''
=======================================
EValuator: VIEWER STREAMLIT ENTRY POINT
=======================================
'''

# ====================
# Import external dependencies
# ====================
import streamlit as st, sys
from pathlib import Path

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils.gallery import default_stage_dirs

# ====================
# Configure page
# ====================
st.set_page_config(page_title='EValuator Viewer', layout='wide')

# ====================
# Initialise session state
# ====================
if 'root_dir' not in st.session_state:
    st.session_state.root_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
if 'stage_dirs' not in st.session_state:
    st.session_state.stage_dirs = default_stage_dirs(st.session_state.root_dir)
if 'root_set' not in st.session_state:
    st.session_state.root_set = False
if 'result_sets' not in st.session_state:
    st.session_state.result_sets = None
if 'selected_result' not in st.session_state:
    st.session_state.selected_result = None
if 'selected_labels' not in st.session_state:
    st.session_state.selected_labels = set()
if 'camera' not in st.session_state:
    st.session_state.camera = None
if 'include_flags' not in st.session_state:
    st.session_state.include_flags = {}

# ====================
# Register pages and run
# ====================
gallery_page = st.Page('pages/gallery.py', title='Gallery', icon=':material/grid_view:')
tomogram_page = st.Page('pages/tomogram.py', title='Tomogram', icon=':material/image:')

nav = st.navigation([gallery_page, tomogram_page], position='hidden')
nav.run()
