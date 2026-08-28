'''
=======================================
EValuator: VIEWER GALLERY PAGE
=======================================
Configure the five pipeline stage directories, list the results resolved across them, and browse mid-slice previews of the available tomograms.
'''

# ====================
# Import external dependencies
# ====================
import pandas as pd, streamlit as st
from pathlib import Path

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils.gallery import STAGES, midslice_preview, scan_stage_dirs

# ====================
# Define helper functions
# ====================
def _open_result(index: int) -> None:
    st.session_state.selected_result = st.session_state.result_sets[index]
    st.session_state.selected_labels = set()
    st.session_state.camera = None
    st.session_state.include_flags = {}
    st.session_state.main_view_last_event_id = None
    st.session_state.results_table_last_selection = ()
    st.switch_page('pages/tomogram.py')

# Button column click callback stashes row here
_pending_open = st.session_state.pop('_gallery_open_row', None)
if _pending_open is not None and st.session_state.get('result_sets'):
    _open_result(_pending_open)


# ====================
# PAGE SECTION: title/experiment directories
# ====================
st.title('Gallery')
st.header('Experiment directories')

_stage_dirs = st.session_state.stage_dirs
_dir_df = pd.DataFrame(
    {'Directory': [str(_stage_dirs.get(s)) if _stage_dirs.get(s) else '' for s in STAGES]},
    index=list(STAGES),
)
_edited = st.data_editor(
    _dir_df,
    num_rows='fixed',
    width='stretch',
    key='stage_dir_editor',
    column_config={'Directory': st.column_config.TextColumn('Directory', width='large')},
)
_new_dirs = {
    stage: (Path(value).expanduser() if str(value).strip() else None)
    for stage, value in zip(STAGES, _edited['Directory'])
}
if _new_dirs != _stage_dirs:
    st.session_state.stage_dirs = _new_dirs
    st.session_state.result_sets = None

if st.button('Scan', type='primary', icon=':material/search:'):
    st.session_state.result_sets = scan_stage_dirs(st.session_state.stage_dirs)

result_sets = st.session_state.result_sets
if result_sets is None:
    st.info('Set the stage directories above and click Scan.')
    st.stop()

if not result_sets:
    st.warning('No results found in those directories.')
    st.stop()

# ====================
# PAGE SECTION: available results
# ====================
st.header('Available results')

def _vesicle_cell(rs) -> str:
    if rs.n_reliable is None or not rs.n_vesicles:
        return str(rs.n_vesicles)
    pct = round(100 * rs.n_reliable / rs.n_vesicles)
    return f'{rs.n_vesicles}  ({rs.n_reliable} reliable, {pct}%)'

summary_df = pd.DataFrame([
    {
        'File stem': rs.stem,
        'Identified vesicles': _vesicle_cell(rs),
        'Raw': rs.raw_mrc is not None,
        'Segmentation': rs.binary_mrc is not None,
        'Labelled': rs.labelled_mrc is not None,
        'Model output': rs.fitted_mrc is not None,
        'Analyse output': rs.analyse_csv is not None,
        'Open': 'Open',
    }
    for rs in result_sets
])

def _on_open_click() -> None:
    click = st.session_state.gallery_open
    if click and click.row is not None:
        st.session_state._gallery_open_row = click.row

st.dataframe(
    summary_df,
    hide_index=True,
    width='stretch',
    column_config={
        'Open': st.column_config.ButtonColumn(
            'Open', type='primary', on_click=_on_open_click, key='gallery_open',
        ),
    },
)

# ====================
# PAGE SECTION: tomogram gallery
# ====================
st.divider()
st.header('Tomogram gallery')

_STAGE_ATTR = {
    'Raw': ('raw_mrc', False),
    'Segmentation': ('binary_mrc', True),
    'Labelled': ('labelled_mrc', True),
    'Model': ('fitted_mrc', True),
}
_stage = st.segmented_control(
    'Show', list(_STAGE_ATTR), default='Labelled', key='gallery_stage',
) or 'Labelled'
_attr, _is_label = _STAGE_ATTR[_stage]

@st.cache_data(show_spinner=False)
def _cached_preview(path_str: str, mtime: float, is_label: bool):
    return midslice_preview(Path(path_str), is_label=is_label)

_shown = [(i, rs) for i, rs in enumerate(result_sets) if getattr(rs, _attr) is not None]
if not _shown:
    st.caption(f'No {_stage.lower()} volumes found.')
else:
    _cols = st.columns(4)
    for _slot, (_idx, rs) in enumerate(_shown):
        path = getattr(rs, _attr)
        with _cols[_slot % 4]:
            try:
                st.image(_cached_preview(str(path), path.stat().st_mtime, _is_label), width='stretch')
            except Exception as exc:  # a bad/oddly-shaped MRC shouldn't kill the whole gallery
                st.caption(f'preview failed: {exc}')
            if st.button(rs.stem, key=f'open_{_stage}_{_idx}', width='stretch'):
                st.session_state._gallery_open_row = _idx
                st.rerun()
