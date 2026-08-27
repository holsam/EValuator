'''
=======================================
EValuator: VIEWER TOMOGRAM PAGE
=======================================
Main interactive pane (drag/orbit, click-to-select-vesicle) + a non-interactive
4-panel overview row mirroring its current orientation, a results table cross-filtered
with the 3D selection, and an include/export workflow for visual QC.
'''

# ====================
# Import external dependencies
# ====================
from pathlib import Path

import pandas as pd
import streamlit as st

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import io as ioutil
from evaluator.utils import mrc as mrcutil

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.app.components.plotly_camera_sync import plotly_view
from evaluator.commands.viewer.utils.export import export_filtered_csv
from evaluator.commands.viewer.utils.join import join_analyse_model
from evaluator.commands.viewer.utils.mesh import HIGHLIGHT_COLOR, build_label_mesh_traces, build_point_cloud_trace, dim_trace

import plotly.graph_objects as go

# ====================
# Guard: a result set must be open
# ====================
result = st.session_state.selected_result
if result is None:
    st.info('No tomogram open — pick one from the Gallery page.')
    st.stop()

st.title(f'Viewer — {result.stem}')

# ====================
# Optional manual file pickers for the 2 volumes with no output-tree home
# ====================
with st.expander('Add raw tomogram / binary segmentation (optional, not stored by the pipeline)'):
    raw_path_input = st.text_input('Raw tomogram MRC path', value=str(result.raw_mrc) if result.raw_mrc else '')
    binary_path_input = st.text_input('Binary segmentation MRC path', value=str(result.binary_mrc) if result.binary_mrc else '')
    if raw_path_input:
        result.raw_mrc = Path(raw_path_input)
    if binary_path_input:
        result.binary_mrc = Path(binary_path_input)

# ====================
# Load volumes and build traces (cached per result-set + downsample so drags don't re-run marching_cubes)
# ====================
DOWNSAMPLE = 2

@st.cache_data(show_spinner='Building meshes...')
def _load_traces(labelled_mrc: Path, fitted_mrc: Path | None, raw_mrc: Path | None, binary_mrc: Path | None, downsample: int):
    views: dict[str, list[go.Mesh3d | go.Scatter3d]] = {}
    trace_index_to_label: dict[str, dict[int, int]] = {}

    labelled_data, _ = mrcutil.readMRCFile(labelled_mrc)
    labelled_traces = build_label_mesh_traces(labelled_data, downsample=downsample)
    views['labelled'] = list(labelled_traces.values())
    trace_index_to_label['labelled'] = {i: label_id for i, label_id in enumerate(labelled_traces)}

    if fitted_mrc is not None:
        fitted_data, _ = mrcutil.readMRCFile(fitted_mrc)
        fitted_traces = build_label_mesh_traces(fitted_data, downsample=downsample)
        views['fitted'] = list(fitted_traces.values())
        trace_index_to_label['fitted'] = {i: label_id for i, label_id in enumerate(fitted_traces)}

    if raw_mrc is not None and raw_mrc.exists():
        raw_data, _ = mrcutil.readMRCFile(raw_mrc)
        views['raw'] = [build_point_cloud_trace(raw_data, downsample=downsample, percentile=97.5, name='raw tomogram')]

    if binary_mrc is not None and binary_mrc.exists():
        binary_data, _ = mrcutil.readMRCFile(binary_mrc)
        views['binary'] = [build_point_cloud_trace(binary_data, downsample=downsample, name='binary segmentation')]

    return views, trace_index_to_label

views, trace_index_to_label = _load_traces(result.labelled_mrc, result.fitted_mrc, result.raw_mrc, result.binary_mrc, DOWNSAMPLE)

VIEW_LABELS = {'raw': 'Raw tomogram', 'binary': 'Binary segmentation', 'labelled': 'Labelled', 'fitted': 'Fitted'}
available_views = [v for v in ('raw', 'binary', 'labelled', 'fitted') if v in views]

# ====================
# Load and join results table
# ====================
analyse_df = pd.read_csv(result.analyse_csv) if result.analyse_csv else None
model_df = (
    pd.DataFrame(ioutil.read_results(result.model_results_path)[0])
    if result.model_results_path else None
)
joined_df = join_analyse_model(analyse_df, model_df, result.stem)

# ====================
# Flatten nested-dict columns (e.g. model's reliability/sphere_fit/ellipsoid_fit) so the
# results table shows real columns instead of a raw dict repr in one cell
# ====================
for _col in list(joined_df.columns):
    _values = joined_df[_col].dropna()
    if not _values.empty and all(isinstance(v, dict) for v in _values):
        _expanded = pd.json_normalize(joined_df[_col].apply(lambda v: v if isinstance(v, dict) else {}).tolist()).add_prefix(f'{_col}.')
        _expanded.index = joined_df.index
        joined_df = pd.concat([joined_df.drop(columns=[_col]), _expanded], axis=1)

# label first, everything else after, in whatever order they came in
_column_order = ['label'] + [c for c in joined_df.columns if c != 'label']

# ====================
# Dark-mode-aware plot background, so the 3D views match the app theme instead of always
# rendering on white
# ====================
_dark_mode = st.context.theme.type == 'dark'
_SCENE_BG = '#0e1117' if _dark_mode else 'white'
_PAPER_BG = '#0e1117' if _dark_mode else 'white'
_GRID_COLOR = '#31333F' if _dark_mode else '#e5e5e5'

# ====================
# Highlight helper — funnels both selection directions through one function
# ====================
def _figure_for(view_name: str, selected_labels: set[int]) -> go.Figure:
    traces = views[view_name]
    fig = go.Figure()
    for trace in traces:
        if view_name in ('labelled', 'fitted') and isinstance(trace, go.Mesh3d):
            trace = go.Mesh3d(trace)  # copy so dimming one view doesn't mutate the cached original
            dim_trace(trace, dim=(bool(selected_labels) and trace.name not in {str(l) for l in selected_labels}))
        fig.add_trace(trace)
    axis = dict(backgroundcolor=_SCENE_BG, gridcolor=_GRID_COLOR, showbackground=True)
    fig.update_layout(
        showlegend=False,
        paper_bgcolor=_PAPER_BG,
        scene=dict(aspectmode='data', xaxis=axis, yaxis=axis, zaxis=axis, bgcolor=_SCENE_BG),
    )
    return fig

# ====================
# Main interactive pane
# ====================
active_view = st.radio('Active view', available_views, format_func=lambda v: VIEW_LABELS[v], horizontal=True, key='active_view')

main_event = plotly_view(
    _figure_for(active_view, st.session_state.selected_labels),
    interactive=True,
    camera=st.session_state.camera,
    key='main_view',
)
# Streamlit replays the component's last return value on every rerun, even ones
# triggered by unrelated widgets — only act on an event_id we haven't seen yet,
# otherwise a single click/drag re-fires forever (permanent rerun spinner, and
# selected_labels flip-flopping so the mini panels never see a stable selection).
if main_event and main_event.get('event_id') != st.session_state.get('main_view_last_event_id'):
    st.session_state.main_view_last_event_id = main_event.get('event_id')
    new_camera = main_event.get('camera')
    # Plotly can echo a relayout event back after we push a camera update into it
    # programmatically (gl3d quirk) — that echo gets its own fresh event_id, so it
    # passes the check above even though nothing changed; comparing the value itself
    # is what actually breaks the loop.
    if new_camera and new_camera != st.session_state.camera:
        st.session_state.camera = new_camera
        st.rerun()
    if main_event.get('clicked_curve') is not None and active_view in trace_index_to_label:
        label_id = trace_index_to_label[active_view].get(main_event['clicked_curve'])
        if label_id is not None:
            current = st.session_state.selected_labels
            if main_event.get('shift_key'):
                # Shift+click adds/removes just this vesicle from the current selection
                current = current ^ {label_id}
            else:
                # A plain click replaces the selection, or clears it if re-clicking the
                # only currently-selected vesicle (the existing deselect-by-reclick behaviour)
                current = set() if current == {label_id} else {label_id}
            st.session_state.selected_labels = current
            st.rerun()

# ====================
# Non-interactive 4-panel overview row, mirroring the main pane's current camera
# ====================
st.caption('Overview (all available views, current orientation)')
cols = st.columns(len(available_views))
for col, view_name in zip(cols, available_views):
    with col:
        st.caption(VIEW_LABELS[view_name])
        plotly_view(
            _figure_for(view_name, st.session_state.selected_labels),
            interactive=False,
            camera=st.session_state.camera,
            key=f'mini_{view_name}',
        )

# ====================
# Results table: cross-filter + include checkboxes
# ====================
st.subheader('Results')
if joined_df.empty:
    st.info('No analyse/model results found for this tomogram yet.')
else:
    if st.session_state.selected_labels:
        st.info(f"Selected vesicles: {', '.join(str(l) for l in sorted(st.session_state.selected_labels))}")

    def _highlight_selected(row):
        is_selected = row['label'] in st.session_state.selected_labels
        return [f'background-color: {HIGHLIGHT_COLOR}66' if is_selected else '' for _ in row]  # ~40% alpha over the theme's own bg/text

    for label_id, flag in st.session_state.include_flags.items():
        if label_id in joined_df['label'].values:
            joined_df.loc[joined_df['label'] == label_id, 'include'] = flag

    edited_df = st.data_editor(
        joined_df.style.apply(_highlight_selected, axis=1) if hasattr(joined_df, 'style') else joined_df,
        column_config={'include': st.column_config.CheckboxColumn(default=True)},
        disabled=[c for c in joined_df.columns if c != 'include'],
        column_order=_column_order,
        hide_index=True,
        key='include_editor',
        width='stretch',
    )
    for _, row in edited_df.iterrows():
        st.session_state.include_flags[int(row['label'])] = bool(row['include'])

    # st.data_editor has no on_select in this Streamlit version, so row-click selection needs
    # a second, selectable st.dataframe — tucked into a collapsed expander so it reads as a
    # deliberate "click here to select" control rather than a mysterious stray table.
    with st.expander('Select a vesicle by clicking a row (or click one in the 3D view above)'):
        table_event = st.dataframe(
            joined_df, on_select='rerun', selection_mode='single-row', key='results_table_shadow',
            column_order=_column_order, hide_index=True, width='stretch',
        )
    selected_rows = tuple(table_event.selection.rows) if table_event and table_event.selection else ()
    # This selection persists across every rerun (native widget state), not just the one
    # it caused — same trap as the camera event above. Only act when it actually changed
    # from what we last processed, otherwise it re-fires st.rerun() forever and stomps
    # whatever row the user just clicked back to the stale one.
    if selected_rows and selected_rows != st.session_state.get('results_table_last_selection'):
        st.session_state.results_table_last_selection = selected_rows
        clicked_label = int(joined_df.iloc[selected_rows[0]]['label'])
        st.session_state.selected_labels = set() if st.session_state.selected_labels == {clicked_label} else {clicked_label}
        st.rerun()

    st.download_button(
        'Download filtered CSV',
        data=joined_df[joined_df['label'].map(st.session_state.include_flags).fillna(True)].to_csv(index=False),
        file_name=f'{result.stem}_filtered.csv',
        mime='text/csv',
    )
    if result.analyse_csv and st.button('Export filtered CSV to evaluator/analyse/'):
        out_path = export_filtered_csv(joined_df, st.session_state.include_flags, result.analyse_csv)
        st.success(f'Wrote {out_path}')