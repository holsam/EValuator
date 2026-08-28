'''
=======================================
EValuator: VIEWER GALLERY PAGE
=======================================
Configure the five pipeline stage directories, list the results resolved across them, and browse mid-slice previews of the available tomograms.
'''

# ====================
# Import external dependencies
# ====================
import base64, html, io, pandas as pd, streamlit as st
from pathlib import Path
from PIL import Image

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils.gallery import STAGES, default_stage_dirs, midslice_preview, scan_stage_dirs

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
_qp_open = st.query_params.get('open')
if _qp_open is not None:
    st.query_params.clear()
    _pending_open = _qp_open
if _pending_open is not None and st.session_state.get('result_sets'):
    try:
        _open_result(int(_pending_open))
    except (ValueError, IndexError):
        pass


# ====================
# PAGE SECTION: title/experiment directories
# ====================
st.title('EValuator Viewer')
st.header('Experiment')

# Root: derives every stage directory from common subfolder names in one go
_rc_in, _rc_btn = st.columns([5, 1], vertical_alignment='bottom')
_root_in = _rc_in.text_input('Root directory', value=str(st.session_state.get('root_dir', Path.cwd())))
if _rc_btn.button('Set root', type='primary', icon=':material/folder_open:', width='stretch'):
    st.session_state.root_dir = Path(_root_in).expanduser()
    st.session_state.stage_dirs = default_stage_dirs(st.session_state.root_dir)
    st.session_state.result_sets = None
    st.rerun()

_stage_dirs = st.session_state.stage_dirs
_col_dirs, _col_results = st.columns(2)

with _col_dirs:
    st.subheader('Directories')
    for _stage in STAGES:
        _cur = _stage_dirs.get(_stage)
        _found = _cur is not None and _cur.exists()
        _c_name, _c_val, _c_edit = st.columns([2, 6, 1], vertical_alignment='center')
        _c_name.write(f'**{_stage.capitalize()}**')
        _c_val.write(str(_cur) if _cur else '_not found – add manually_')
        if not _found and _c_edit.button('Edit', icon=':material/edit:', key=f'edit_dir_{_stage}', type='tertiary'):
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
        st.session_state.result_sets = scan_stage_dirs(st.session_state.stage_dirs)

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
        st.info('Set the stage directories and click Scan.')
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
                    'Open', on_click=_on_open_click, key='gallery_open',
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

def _card_data_uri(path_str: str, mtime: float, is_label: bool) -> str:
    arr = midslice_preview(Path(path_str), is_label=is_label)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

_shown = [(i, rs) for i, rs in enumerate(result_sets) if getattr(rs, _attr) is not None]
if not _shown:
    st.caption(f'No {_stage.lower()} volumes found.')
else:
    st.markdown(
        '<style>'
        '.tomo-card{position:relative;display:block;margin-bottom:12px;border-radius:8px;'
        'overflow:hidden;line-height:0;cursor:pointer}'
        '.tomo-card img{width:100%;height:auto;display:block}'
        '.tomo-card .tomo-name{position:absolute;left:0;right:0;bottom:0;padding:4px 8px;'
        'background:rgba(0,0,0,.55);color:#fff;font-size:.8rem;line-height:1.2}'
        '</style>',
        unsafe_allow_html=True,
    )
    _cols = st.columns(4)
    for _slot, (_idx, rs) in enumerate(_shown):
        path = getattr(rs, _attr)
        with _cols[_slot % 4]:
            try:
                uri = _card_data_uri(str(path), path.stat().st_mtime, _is_label)
                st.markdown(
                    f'<a class="tomo-card" href="?open={_idx}" target="_self">'
                    f'<img src="{uri}"/><span class="tomo-name">{html.escape(rs.stem)}</span></a>',
                    unsafe_allow_html=True,
                )
            except Exception as exc:  # a bad/oddly-shaped MRC shouldn't kill the whole gallery
                st.caption(f'preview failed: {exc}')
