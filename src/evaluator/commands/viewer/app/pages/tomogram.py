'''
=======================================
EValuator: VIEWER TOMOGRAM PAGE
=======================================
'''

# ====================
# Import dependencies
# ====================

# Import external dependencies
import pandas as pd, plotly.graph_objects as go, streamlit as st, tempfile
from pathlib import Path

# Import EValuator utilities
from evaluator.utils import io as ioutil
from evaluator.utils import mrc as mrcutil

# Import EValuator viewer utilities
from evaluator.commands.viewer.app.components.plotly_camera_sync import plotly_view
from evaluator.commands.viewer.utils import plots as plotutil
from evaluator.commands.viewer.utils.export import export_filtered_csv
from evaluator.commands.viewer.utils.format import pretty_column
from evaluator.commands.viewer.utils.join import join_analyse_model
from evaluator.commands.viewer.utils.mesh import build_label_mesh_traces, build_point_cloud_trace, dim_trace

# ====================
# Set guard for open result set (if session state is gone eg from hard refresh, send back to the Gallery)
# ====================
result = st.session_state.selected_result
if result is None:
    st.switch_page('pages/gallery.py')

# ====================
# PAGE SECTION: navigation/title
# ====================
if st.button('Gallery', icon=':material/arrow_back:', type='primary'):
    st.switch_page('pages/gallery.py')
st.title(result.stem)
_n_rel = result.n_reliable if result.n_reliable is not None else '—'
st.caption(f'{result.n_vesicles} vesicles · {_n_rel} reliable')
st.divider()

# ====================
# PAGE SECTION: metadata
# ====================
st.header('Metadata')

# Available path fields to fill
_PATH_FIELDS = {
    'Labelled MRC': 'labelled_mrc',
    'Fitted MRC': 'fitted_mrc',
    'Raw tomogram MRC': 'raw_mrc',
    'Binary segmentation MRC': 'binary_mrc',
    'Analyse CSV': 'analyse_csv',
    'Model results': 'model_results_path',
}

# Table showing paths
with st.container():
    for _fname, _fattr in _PATH_FIELDS.items():
        _c_name, _c_val = st.columns([2, 5], vertical_alignment='center')
        _c_name.write(f'**{_fname}**')
        _cur = getattr(result, _fattr)
        if _cur:
            _c_val.write(str(_cur))
        elif _c_val.button('Set', icon=':material/edit:', key=f'edit_{_fattr}'):
            st.session_state._edit_field = (_fname, _fattr)
            st.rerun()

# Inline form for adding entries
if st.session_state.get('_edit_field'):
    _fname, _fattr = st.session_state._edit_field
    with st.form('path_edit'):
        _up = st.file_uploader(
            f'Upload {_fname}',
            type=['mrc'] if _fattr.endswith('_mrc') else None,
            accept_multiple_files=False,
        )
        _save_col, _cancel_col = st.columns(2)
        if _save_col.form_submit_button('Save', type='primary', width='stretch'):
            if _up is not None:
                _dest = Path(tempfile.gettempdir()) / f'evaluator_viewer_{result.stem}_{_up.name}'
                _dest.write_bytes(_up.getbuffer())
                setattr(result, _fattr, _dest)
            del st.session_state._edit_field
            st.rerun()
        if _cancel_col.form_submit_button('Cancel', width='stretch'):
            del st.session_state._edit_field
            st.rerun()

# ====================
# Load volumes & build traces for viewer section
# ====================
DOWNSAMPLE = 2

# Load volumes and build traces (cached per result-set  downsample so drags don't re-run marching_cubes)
@st.cache_data(show_spinner=False)
def _load_traces(labelled_mrc: Path | None, fitted_mrc: Path | None, raw_mrc: Path | None, binary_mrc: Path | None, downsample: int):
    views: dict[str, list[go.Mesh3d | go.Scatter3d]] = {}
    trace_index_to_label: dict[str, dict[int, int]] = {}
    shapes: list[tuple[int, int, int]] = []  # (Z, Y, X) of every loaded volume, for a shared scene box

    if labelled_mrc is not None:
        labelled_data, _ = mrcutil.readMRCFile(labelled_mrc)
        shapes.append(labelled_data.shape)
        labelled_traces = build_label_mesh_traces(labelled_data, downsample=downsample)
        views['labelled'] = list(labelled_traces.values())
        trace_index_to_label['labelled'] = {i: label_id for i, label_id in enumerate(labelled_traces)}

    if fitted_mrc is not None:
        fitted_data, _ = mrcutil.readMRCFile(fitted_mrc)
        shapes.append(fitted_data.shape)
        fitted_traces = build_label_mesh_traces(fitted_data, downsample=downsample)
        views['fitted'] = list(fitted_traces.values())
        trace_index_to_label['fitted'] = {i: label_id for i, label_id in enumerate(fitted_traces)}

    if raw_mrc is not None and raw_mrc.exists():
        raw_data, _ = mrcutil.readMRCFile(raw_mrc)
        shapes.append(raw_data.shape)
        views['raw'] = [build_point_cloud_trace(raw_data, downsample=downsample, percentile=97.5, name='raw tomogram')]

    if binary_mrc is not None and binary_mrc.exists():
        binary_data, _ = mrcutil.readMRCFile(binary_mrc)
        shapes.append(binary_data.shape)
        views['binary'] = [build_point_cloud_trace(binary_data, downsample=downsample, name='binary segmentation')]

     # Common scene bounds in downsampled screen (X,Y,Z) order
    scene_bounds = None
    if shapes:
        zmax = max(s[0] for s in shapes); ymax = max(s[1] for s in shapes); xmax = max(s[2] for s in shapes)
        scene_bounds = (xmax // downsample, ymax // downsample, zmax // downsample)
    return views, trace_index_to_label, scene_bounds

VIEW_LABELS = {'raw': 'Raw tomogram', 'binary': 'Binary segmentation', 'labelled': 'Labelled', 'fitted': 'Fitted'}

# ====================
# Load results tables and cache on source path
# ====================
def _build_results(stem: str, analyse_csv, model_results_path):
    analyse_df = pd.read_csv(analyse_csv) if analyse_csv else None
    model_df = pd.DataFrame(ioutil.read_results(model_results_path)[0]) if model_results_path else None
    joined, _a_names, _m_names = join_analyse_model(analyse_df, model_df, stem)

    # Flatten nested-dict columns (model reliability/sphere_fit/ellipsoid_fit) into real columns
    for col in list(joined.columns):
        vals = joined[col].dropna()
        if not vals.empty and all(isinstance(v, dict) for v in vals):
            exp = pd.json_normalize(joined[col].apply(lambda v: v if isinstance(v, dict) else {}).tolist()).add_prefix(f'{col}.')
            exp.index = joined.index
            joined = pd.concat([joined.drop(columns=[col]), exp], axis=1)

    def origin(c):
        return 'model' if (c in _m_names or c.split('.', 1)[0] in _m_names) else 'analyse'

    a_cols = ['label']  [c for c in joined.columns if c not in ('label', 'include') and origin(c) == 'analyse']
    m_body = [c for c in joined.columns if c not in ('label', 'include', 'label_id', 'source_file') and origin(c) == 'model']
    m_cols = (['label'] if 'label' in joined.columns else [])  m_body  (['source_file'] if 'source_file' in joined.columns else [])

    def _display(cols):  # None when the source is absent (only the `label` key present)
        if len(cols) <= 1:
            return None
        df = joined[cols].fillna('')  # blank, not "None"/"<NA>", for missing cells
        return df, {c: st.column_config.Column(pretty_column(c)) for c in cols}

    return {'joined': joined, 'analyse': _display(a_cols), 'model': _display(m_cols)}

# Positional row indices (shared by both source tables, same row order) for a label set — used to mirror a selection made in the 3D view or one table into the other table.
def _rows_for(labels: set[int]) -> list[int]:
    return [i for i, l in enumerate(joined_df['label'].tolist()) if l in labels]

# ====================
# Display helpers 
# ====================

# Dark-mode-aware plot background, so the 3D views match the app theme instead of always rendering on white
_dark_mode = st.context.theme.type == 'dark'
_SCENE_BG = '#0e1117' if _dark_mode else 'white'
_PAPER_BG = '#0e1117' if _dark_mode else 'white'
_GRID_COLOR = '#31333F' if _dark_mode else '#e5e5e5'

# Highlight helper — funnels both selection directions through one function
def _figure_for(view_name: str, selected_labels: set[int]) -> go.Figure:
    traces = views[view_name]
    fig = go.Figure()
    for trace in traces:
        if view_name in ('labelled', 'fitted') and isinstance(trace, go.Mesh3d) and selected_labels:
            trace = go.Mesh3d(trace)  # copy so recolouring one view doesn't mutate the cached original
            dim_trace(trace, dim=(trace.name not in {str(l) for l in selected_labels}))
        fig.add_trace(trace)
    axis = dict(backgroundcolor=_SCENE_BG, gridcolor=_GRID_COLOR, showbackground=True)
    # Same box for every view/panel so meshes and point clouds are spatially comparable at a glance
    ax = lambda n: {**axis, 'range': [0, scene_bounds[n]]} if scene_bounds else axis
    fig.update_layout(
        showlegend=False,
        paper_bgcolor=_PAPER_BG,
        scene=dict(aspectmode='data', xaxis=axis, yaxis=axis, zaxis=axis, bgcolor=_SCENE_BG),
    )
    scene=dict(aspectmode='data', xaxis=ax(0), yaxis=ax(1), zaxis=ax(2), bgcolor=_SCENE_BG),
    return fig

# ====================
# PAGE SECTION: viewer
# ====================
st.divider()
st.header('Viewer')

# Load data here so nav/title/metadata render immediately with a spinner in their place
with st.spinner('Loading volumes and results...'):
    views, trace_index_to_label, scene_bounds = _load_traces(
        result.labelled_mrc, result.fitted_mrc, result.raw_mrc, result.binary_mrc, DOWNSAMPLE,
    )
    available_views = [v for v in ('raw', 'binary', 'labelled', 'fitted') if v in views]

    _res_key = (result.stem, str(result.analyse_csv), str(result.model_results_path))
    if st.session_state.get('_results_key') != _res_key:
        st.session_state._results_key = _res_key
        st.session_state._results_data = _build_results(result.stem, result.analyse_csv, result.model_results_path)
    _results = st.session_state._results_data
    joined_df = _results['joined']

if not available_views:
    st.warning('No volumes to display for this result. Set a path in Metadata above.')
    st.stop()

_sel_labels = st.session_state.selected_labels
_col_main, _col_side = st.columns([3, 2])

with _col_main:
    active_view = st.segmented_control(
        'Active view', available_views, format_func=lambda v: VIEW_LABELS[v],
        default=available_views[0], key='active_view', label_visibility='collapsed',
    ) or available_views[0]
    main_event = plotly_view(
        _figure_for(active_view, _sel_labels),
        interactive=True,
        camera=st.session_state.camera,
        key='main_view',
    )

with _col_side:
    for _r0 in range(0, len(available_views), 2):
        _chunk = available_views[_r0:_r0  2]
        for _c, _vn in zip(st.columns(len(_chunk)), _chunk):
            with _c:
                st.markdown(f'#### {VIEW_LABELS[_vn]}')
                plotly_view(
                    _figure_for(_vn, _sel_labels),
                    interactive=False,
                    camera=st.session_state.camera,
                    key=f'mini_{_vn}',
                )

# Only act on unseen event_ids so single click/drag doesn't refire forever
if main_event and main_event.get('event_id') != st.session_state.get('main_view_last_event_id'):
    st.session_state.main_view_last_event_id = main_event.get('event_id')
    new_camera = main_event.get('camera')
    # Plotly can echo a relayout event back (gl3d quirk) so give echo new event_id so it passes above check 
    if new_camera and new_camera != st.session_state.camera:
        st.session_state.camera = new_camera
        st.rerun()
    if main_event.get('clicked_curve') is not None and active_view in trace_index_to_label:
        label_id = trace_index_to_label[active_view].get(main_event['clicked_curve'])
        if label_id is not None:
            current = st.session_state.selected_labels
            if main_event.get('shift_key'):
                # Shiftclick adds/removes just this vesicle from the current selection
                current = current ^ {label_id}
            else:
                # A plain click replaces the selection, or clears it if re-clicking the only currently-selected vesicle (the existing deselect-by-reclick behaviour)
                current = set() if current == {label_id} else {label_id}
            st.session_state.selected_labels = current
            _cur_rows = _rows_for(current)
            st.session_state['_pending_table_rows'] = _cur_rows
            st.session_state._last_a_rows = st.session_state._last_m_rows = tuple(_cur_rows)
            st.rerun()

# ====================
# PAGE SECTION: results
# ====================
st.divider()
st.header('Results')
if joined_df.empty:
    st.info('No analyse or model results for this tomogram.')
else:
    if st.session_state.selected_labels:
        st.info(f"Selected vesicles: {', '.join(str(l) for l in sorted(st.session_state.selected_labels))}")
    _has_a = _results['analyse'] is not None
    _has_m = _results['model'] is not None
    def _source_table(display, key: str):
        df, colcfg = display
        return st.dataframe(df, on_select='rerun', selection_mode='multi-row', hide_index=True, width='stretch', key=key, column_config=colcfg)
    # Mirror a pending selection (from the 3D view or the other table) into the rendered tables before they instantiate
    _pending = st.session_state.pop('_pending_table_rows', None)
    if _pending is not None:
        if _has_a:
            st.session_state.analyse_table = {'selection': {'rows': _pending, 'columns': []}}
        if _has_m:
            st.session_state.model_table = {'selection': {'rows': _pending, 'columns': []}}
    a_event = m_event = None
    left, right = st.columns(2)
    with left:
        st.markdown('#### Analyse')
        if _has_a:
            a_event = _source_table(_results['analyse'], 'analyse_table')
        else:
            st.caption('No analyse results.')
    with right:
        st.markdown('#### Model')
        if _has_m:
            m_event = _source_table(_results['model'], 'model_table')
        else:
            st.caption('No model results.')
    _a_rows = tuple(a_event.selection.rows) if a_event is not None else None
    _m_rows = tuple(m_event.selection.rows) if m_event is not None else None
    _rows = None
    if _a_rows is not None and _a_rows != st.session_state.get('_last_a_rows', ()):
        _rows = _a_rows
    elif _m_rows is not None and _m_rows != st.session_state.get('_last_m_rows', ()):
        _rows = _m_rows
    if _rows is not None:
        if _a_rows is not None:
            st.session_state._last_a_rows = _rows
        if _m_rows is not None:
            st.session_state._last_m_rows = _rows
        _picked = {int(joined_df.iloc[i]['label']) for i in _rows}
        if _picked != set(st.session_state.selected_labels):
            st.session_state.selected_labels = _picked
            st.session_state['_pending_table_rows'] = list(_rows)
            st.rerun()

    # results plots
    st.subheader('Plots')
    _sel_now = set(st.session_state.selected_labels)
    _num_cols = plotutil.numeric_columns(joined_df)

    def _plot_cross_filter(event, tag: str):
        picked = plotutil.selected_labels_from_event(event)
        seen_key = f'_last_plot_{tag}'
        if picked and picked != set(st.session_state.selected_labels) and tuple(sorted(picked)) != st.session_state.get(seen_key):
            st.session_state[seen_key] = tuple(sorted(picked))
            st.session_state.selected_labels = picked
            _r = _rows_for(picked)
            st.session_state['_pending_table_rows'] = _r
            st.session_state._last_a_rows = st.session_state._last_m_rows = tuple(_r)
            st.rerun()

    _tab_conc, _tab_reliab, _tab_dist, _tab_scatter = st.tabs(['Concordance', 'Reliability', 'Distribution', 'Feature scatter'])
    with _tab_conc:
        _diam_opts = plotutil.concordance_analyse_options(joined_df)
        _diam_col = st.selectbox('Analyse diameter', _diam_opts, format_func=pretty_column, key='conc_diam') if _diam_opts else None
        _fig = plotutil.concordance(joined_df, _sel_now, _dark_mode, analyse_col=_diam_col)
        if _fig is None:
            st.caption('Needs model fitted radius and an analyse diameter column.')
        else:
            _plot_cross_filter(st.plotly_chart(_fig, key='plot_conc', on_select='rerun'), 'conc')
    with _tab_reliab:
        _fig = plotutil.reliability(joined_df, _sel_now, _dark_mode)
        if _fig is None:
            st.caption('Needs model RMSE and analyse closure/enclosed columns.')
        else:
            _plot_cross_filter(st.plotly_chart(_fig, key='plot_reliab', on_select='rerun'), 'reliab')
    with _tab_dist:
        if not _num_cols:
            st.caption('No numeric columns to plot.')
        else:
            _di = _num_cols.index('equiv_diameter_nm') if 'equiv_diameter_nm' in _num_cols else 0
            _dc1, _dc2 = st.columns([3, 1])
            _f = _dc1.selectbox('Feature', _num_cols, index=_di, format_func=pretty_column, key='dist_feature')
            _bw = _dc2.number_input('Bin width', min_value=0.0, value=25.0, step=5.0, key='dist_bin_width', help='In feature units, anchored at 0: (0, w], (w, 2w], … Set 0 for auto bins.')
            st.plotly_chart(plotutil.distribution(joined_df, _f, _sel_now, _dark_mode, bin_size=_bw or None), key='plot_dist')
    with _tab_scatter:
        if len(_num_cols) < 2:
            st.caption('Need at least two numeric columns.')
        else:
            _cx, _cy = st.columns(2)
            _x = _cx.selectbox('X', _num_cols, index=0, format_func=pretty_column, key='scatter_x')
            _y = _cy.selectbox('Y', _num_cols, index=min(1, len(_num_cols) - 1), format_func=pretty_column, key='scatter_y')
            _plot_cross_filter(
                st.plotly_chart(plotutil.feature_scatter(joined_df, _x, _y, _sel_now, _dark_mode),
                                key='plot_scatter', on_select='rerun'),
                'scatter',
            )

    # results export
    st.subheader('Export')
    _sel = sorted(st.session_state.selected_labels)
    if not _sel:
        st.caption('Select rows in the tables above (or a vesicle in the 3D view) to choose what to export.')
    else:
        st.write(f'Export {len(_sel)} selected vesicle{"" if len(_sel) == 1 else "s"} to CSV')
        _out_df = joined_df[joined_df['label'].isin(_sel)].drop(columns=['include'], errors='ignore')
        st.download_button('Download CSV', data=_out_df.to_csv(index=False), file_name=f'{result.stem}_selected.csv', mime='text/csv')
        if result.analyse_csv and st.button('Export CSV to evaluator/analyse/'):
            _flags = {int(l): (int(l) in set(_sel)) for l in joined_df['label']}
            out_path = export_filtered_csv(joined_df.drop(columns=['include'], errors='ignore'), _flags, result.analyse_csv)
            st.success(f'Wrote {out_path}')
