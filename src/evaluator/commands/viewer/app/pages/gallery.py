'''
=======================================
EValuator: VIEWER GALLERY PAGE
=======================================
Configure the five pipeline stage directories, list the results resolved across them, and browse mid-slice previews of the available tomograms.
'''

# ====================
# Import external dependencies
# ====================
import base64, io, pandas as pd, streamlit as st
from pathlib import Path
from PIL import Image

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils.gallery import STAGES, default_stage_dirs, midslice_preview, scan_stage_dirs

# ====================
# Cached scan: re-run only when a stage dir path or its mtime changes
# ====================
def _stage_sig(stage_dirs: dict) -> tuple:
    out = []
    for _s in STAGES:
        _d = stage_dirs.get(_s)
        try:
            _m = _d.stat().st_mtime if _d else None
        except OSError:
            _m = None
        out.append((_s, str(_d) if _d else None, _m))
    return tuple(out)

@st.cache_data(show_spinner='Scanning stage directories...')
def _scan_cached(sig: tuple, _stage_dirs: dict):
    return scan_stage_dirs(_stage_dirs)

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

# Open tomogram callbacks land here
_row = st.session_state.pop('_gallery_open_row', None)
if _row is not None and st.session_state.get('result_sets'):
    if 0 <= int(_row) < len(st.session_state.result_sets):
        _open_result(int(_row))

# ====================
# PAGE SECTION: title/experiment directories
# ====================
st.title('EValuator Viewer')
st.header('Experiment')

_root_set = st.session_state.get('root_set', False)
_stage_dirs = st.session_state.stage_dirs
_col_dirs, _col_results = st.columns(2)

with _col_dirs:
    st.subheader('Setup')
    # Root box: open until a root is set, then it collapses and Directories opens.
    with st.expander('Root directory', expanded=not _root_set):
        _root_in = st.text_input(
            'Root directory',
            value=str(st.session_state.get('root_dir', Path.cwd())),
            label_visibility='collapsed',
        )
        if st.button('Set root', type='primary', icon=':material/folder_open:', width='stretch'):
            st.session_state.root_dir = Path(_root_in).expanduser()
            st.session_state.stage_dirs = default_stage_dirs(st.session_state.root_dir)
            st.session_state.result_sets = None
            st.session_state.root_set = True
            st.rerun()

    with st.expander('Directories', expanded=_root_set):
        for _stage in STAGES:
            _cur = _stage_dirs.get(_stage)
            _found = _cur is not None and _cur.exists()
            _c_name, _c_val, _c_edit = st.columns([2, 6, 1], vertical_alignment='center')
            _c_name.write(f'**{_stage.capitalize()}**')
            if _cur:
                _c_val.write(str(_cur))
            else:
                _c_val.write('_not found – add manually_' if _root_set else '_set root_')
            if _root_set and not _found and _c_edit.button(
                'Edit', icon=':material/edit:', key=f'edit_dir_{_stage}', type='tertiary',
            ):
                st.session_state._edit_dir = _stage
                st.rerun()

        if st.session_state.get('_edit_dir'):
            _stage = st.session_state._edit_dir
            with st.form('dir_edit'):
                _val = st.text_input(f'{_stage.capitalize()} directory', value=str(_stage_dirs.get(_stage) or ''))
                if st.form_submit_button('Save', type='primary'):
                    _stage_dirs[_stage] = Path(_val).expanduser() if _val.strip() else None
                    st.session_state.result_sets = None
                    del st.session_state._edit_dir
                    st.rerun()
                if st.form_submit_button('Cancel'):
                    del st.session_state._edit_dir
                    st.rerun()

        if st.button('Scan', type='primary', icon=':material/search:'):
            _sd = st.session_state.stage_dirs
            st.session_state.result_sets = _scan_cached(_stage_sig(_sd), _sd)

result_sets = st.session_state.result_sets

def _vesicle_cell(rs) -> str:
    if rs.n_reliable is None or not rs.n_vesicles:
        return str(rs.n_vesicles)
    pct = round(100 * rs.n_reliable / rs.n_vesicles)
    return f'{rs.n_vesicles}  ({rs.n_reliable} reliable, {pct}%)'

def _on_open_click() -> None:
     click = st.session_state.gallery_open
     if click and click.row is not None:
         st.session_state._gallery_open_row = click.row

with _col_results:
    st.subheader('Available results')
    if not result_sets:
        st.info('Set the root directory, confirm stage directories and click Scan.')
    else:
        summary_df = pd.DataFrame([
            {
                'File stem': rs.stem,
                'Identified vesicles': _vesicle_cell(rs),
                'Raw tomogram found': rs.raw_mrc is not None,
                'Segmentation found': rs.binary_mrc is not None,
                'Labelled tomogram found': rs.labelled_mrc is not None,
                'Model output found': rs.fitted_mrc is not None,
                'Analyse output found': rs.analyse_csv is not None,
                'Open': ':material/open_in_new:',
            }
            for rs in result_sets
        ])
        st.dataframe(
            summary_df,
            hide_index=True,
            width='stretch',
            column_config={
                'Open': st.column_config.ButtonColumn(
                    'Open', on_click=_on_open_click, key='gallery_open', type='primary',
                ),
            },
        )

if not result_sets:
    st.stop()

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
_stage = st.segmented_control('Show', list(_STAGE_ATTR), default='Labelled', key='gallery_stage') or 'Labelled'
_attr, _is_label = _STAGE_ATTR[_stage]

@st.cache_data(max_entries=4096, show_spinner=False)
def _card_data_uri(path_str: str, mtime: float, is_label: bool) -> str:
    arr = midslice_preview(Path(path_str), is_label=is_label)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

_shown = [(i, rs) for i, rs in enumerate(result_sets) if getattr(rs, _attr) is not None]
if not _shown:
    st.caption(f'No {_stage.lower()} volumes found.')
else:
    # Paginate: only build previews/CSS for the current page
    _PER_PAGE = 60
    _n_pages = (len(_shown) + _PER_PAGE - 1) // _PER_PAGE
    if _n_pages > 1:
        _page = st.number_input(
            f'Page (of {_n_pages}, {_PER_PAGE} per page)',
            min_value=1, max_value=_n_pages, value=1, step=1, key='gallery_page',
        ) - 1
    else:
        _page = 0
    _page_items = _shown[_page * _PER_PAGE:(_page + 1) * _PER_PAGE]

    _cards, _bg_rules = [], []
    for _idx, rs in _page_items:
        path = getattr(rs, _attr)
        try:
            uri = _card_data_uri(str(path), path.stat().st_mtime, _is_label)
        except Exception as exc:  # a bad MRC shouldn't kill the whole gallery
            _cards.append((_idx, rs, None, str(exc)))
            continue
        _bg_rules.append(f'.st-key-card_{_idx} button{{background-image:url("{uri}")}}')
        _cards.append((_idx, rs, f'card_{_idx}', None))

    st.html(
        '<style>'
        '[class*="st-key-card_"] button{display:flex!important;flex-direction:column!important;align-items:stretch!important;justify-content:flex-start!important;aspect-ratio:1/1!important;height:auto!important;min-height:0!important;padding:0!important;overflow:hidden;border-radius:8px;white-space:normal;color:#fff;background-color:#000!important;background-position:center!important;background-repeat:no-repeat!important;background-size:contain!important}'
        '[class*="st-key-card_"] button p{margin:0;flex:0 0 auto;padding:3px 6px;background:rgba(255,75,75,.5);font-size:.75rem;line-height:1.2;text-align:left}'
        + ''.join(_bg_rules)
        + '</style>'
    )
    _cols = st.columns(4)
    for _slot, (_idx, rs, _key, _err) in enumerate(_cards):
        with _cols[_slot % 4]:
            if _err:
                st.caption(f'preview failed: {_err}')
            elif st.button(rs.stem, key=_key, width='stretch'):
                st.session_state._gallery_open_row = _idx
                st.rerun()
