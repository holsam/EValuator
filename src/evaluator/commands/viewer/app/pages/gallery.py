'''
=======================================
EValuator: VIEWER GALLERY PAGE
=======================================
Scan a directory for evaluator/ output and let the user pick a tomogram to open.
'''

# ====================
# Import external dependencies
# ====================
import pandas as pd, streamlit as st
from pathlib import Path

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils.gallery import scan_result_root

# ====================
# Render page
# ====================
st.title('Gallery')

root_input = st.text_input('Result root directory', value=str(st.session_state.root_dir))
if st.button('Scan'):
    st.session_state.root_dir = Path(root_input)
    st.session_state.result_sets = scan_result_root(st.session_state.root_dir)

result_sets = st.session_state.result_sets
if not result_sets:
    st.info('Enter a directory containing evaluator/{label,model,analyse} output and click Scan.')
    st.stop()

summary_df = pd.DataFrame([
    {
        'stem': rs.stem,
        'vesicles': rs.n_vesicles,
        'reliable': rs.n_reliable if rs.n_reliable is not None else '—',
        'has model output': rs.fitted_mrc is not None,
        'has analyse csv': rs.analyse_csv is not None,
    }
    for rs in result_sets
])

_table_key = f"gallery_table_{st.session_state.get('gallery_table_nonce', 0)}"
event = st.dataframe(summary_df, on_select='rerun', selection_mode='single-row', key=_table_key, width='stretch')
selected_rows = tuple(event.selection.rows) if event and event.selection else ()
if selected_rows:
    st.session_state.gallery_table_nonce = st.session_state.get('gallery_table_nonce', 0) + 1
    st.session_state.selected_result = result_sets[selected_rows[0]]
    st.session_state.selected_labels = set()
    st.session_state.camera = None
    st.session_state.include_flags = {}
    st.session_state.main_view_last_event_id = None
    st.session_state.results_table_last_selection = ()
    st.switch_page('pages/tomogram.py')
