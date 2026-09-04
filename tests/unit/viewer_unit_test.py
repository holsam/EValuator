'''
Unit tests for `evaluator viewer`
'''

# ====================
# Import external dependencies
# ====================
import socket, types
from pathlib import Path

import mrcfile, numpy as np, pandas as pd, pytest

# ====================
# Import evaluator viewer helpers
# ====================
from evaluator.commands.viewer.utils import dispatch as dispatchutil
from evaluator.commands.viewer.utils import gallery as galleryutil
from evaluator.commands.viewer.utils import mesh as meshutil
from evaluator.commands.viewer.utils import plots as plotsutil
from evaluator.commands.viewer.utils import stems as stemutil
from evaluator.commands.viewer.utils import theme as themeutil
from evaluator.commands.viewer.utils.export import export_filtered_csv
from evaluator.commands.viewer.utils.format import pretty_column
from evaluator.commands.viewer.utils.join import join_analyse_model

# ====================
# Define helpers
# ====================
def _write_mrc(path, data, voxel_size_a=5.36):
    with mrcfile.new(str(path), overwrite=True) as m:
        m.set_data(data)
        m.voxel_size = voxel_size_a
    return path

def _hollow_sphere(shape=(24, 24, 24), centre=(12, 12, 12), r_outer=8, r_inner=4):
    zz, yy, xx = np.indices(shape)
    cz, cy, cx = centre
    dist = np.sqrt((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2)
    return ((dist >= r_inner) & (dist <= r_outer))

def _demo_joined_df():
    return pd.DataFrame({
        'label': [1, 2, 3, 4],
        'equiv_diameter_nm': [30.0, 40.0, 50.0, np.nan],
        'lumen_volume': [1.0, 2.0, 3.0, 4.0],
        'radius': [16.0, 21.0, 24.0, 10.0],
        'major_axis_diameter': [31.0, 42.0, 48.0, 12.0],
        'reliability.rmse_nm': [1.0, 2.0, 5.0, 1.0],
        'closure_fill_ratio': [0.9, 0.8, 0.2, 0.95],
        'reliability.is_reliable': [True, True, False, True],
        'ev_count': [2, 3, 1, 4],
        'include': [True, True, True, True],
    })

@pytest.fixture
def fake_streamlit(monkeypatch):
    '''Patch st in theme.py'''
    class _State(dict):
        __getattr__ = dict.get
    fake = types.SimpleNamespace(
        session_state=_State(),
        context=types.SimpleNamespace(theme=types.SimpleNamespace(type='light')),
    )
    monkeypatch.setattr(themeutil, 'st', fake)
    return fake

# ====================
# Define tests for viewer/utils/format.py
# ====================
class TestPrettyColumn:
    def test_unit_suffix_becomes_parenthesised(self):
        '''A trailing `_nm` token is rendered as a `(nm)` unit suffix'''
        assert pretty_column('equiv_diameter_nm') == 'Equiv diameter (nm)'

    def test_acronyms_kept_uppercase(self):
        '''BIC / RMSE acronyms are uppercase'''
        assert pretty_column('bic_sphere') == 'BIC sphere'
        assert pretty_column('rmse_nm') == 'RMSE (nm)'

    def test_dotted_path_flattened(self):
        '''`a.b_c` splits on both `.` and `_`'''
        assert pretty_column('reliability.relative_rmse') == 'Reliability relative RMSE'

    def test_only_first_alpha_char_capitalised(self):
        assert pretty_column('major_axis_diameter') == 'Major axis diameter'

    def test_single_token(self):
        assert pretty_column('label') == 'Label'

    def test_no_alpha_returns_input_joined(self):
        '''A name with no alphabetic characters is returned unchanged'''
        assert pretty_column('123_456') == '123 456'

# ====================
# Define tests for viewer/utils/join.py
# ====================
class TestJoinAnalyseModel:
    def _analyse(self):
        return pd.DataFrame({
            'tomogram': ['t1_labelled.mrc', 't1_labelled.mrc', 't2_labelled.mrc'],
            'label': [1, 2, 1],
            'equiv_diameter_nm': [30.0, 40.0, 55.0],
        })

    def _model(self):
        return pd.DataFrame({
            'source_file': ['t1_labelled.mrc', 't1_labelled.mrc'],
            'label_id': [1, 2],
            'radius': [16.0, 21.0],
        })

    def test_stem_filter_selects_only_matching_rows(self):
        '''Only rows whose tomogram/source_file stem (minus `_labelled`) matches are kept'''
        joined, _, _ = join_analyse_model(self._analyse(), self._model(), 't1')
        assert len(joined) == 2
        assert set(joined['label']) == {1, 2}

    def test_outer_merge_on_label(self):
        '''analyse.label joins model.label_id'''
        joined, analyse_names, model_names = join_analyse_model(self._analyse(), self._model(), 't1')
        row = joined[joined['label'] == 1].iloc[0]
        assert row['equiv_diameter_nm'] == 30.0
        assert row['radius'] == 16.0
        assert 'equiv_diameter_nm' in analyse_names
        assert 'radius' in model_names

    def test_include_column_added_true(self):
        joined, _, _ = join_analyse_model(self._analyse(), self._model(), 't1')
        assert joined['include'].all()

    def test_include_seeded_from_is_vesicle_like(self):
        analyse = self._analyse()
        analyse['is_vesicle_like'] = [True, False, True]
        joined, _, _ = join_analyse_model(analyse, self._model(), 't1')
        by_label = dict(zip(joined['label'], joined['include']))
        assert by_label[1] is True or by_label[1] == True
        assert by_label[2] == False

    def test_analyse_only(self):
        joined, analyse_names, model_names = join_analyse_model(self._analyse(), None, 't2')
        assert len(joined) == 1 and joined.iloc[0]['equiv_diameter_nm'] == 55.0
        assert 'label' in analyse_names and 'label' in model_names

    def test_model_only_renames_label_id_to_label(self):
        joined, _, model_names = join_analyse_model(None, self._model(), 't1')
        assert 'label' in joined.columns and 'label_id' not in joined.columns
        assert set(joined['label']) == {1, 2}

    def test_no_match_returns_empty_frame(self):
        joined, _, _ = join_analyse_model(self._analyse(), self._model(), 'nope')
        assert joined.empty

# ====================
# Define tests for viewer/utils/theme.py
# ====================
class TestTheme:
    def test_default_theme_when_unset(self, fake_streamlit):
        '''With nothing in session_state, active() resolves the Okabe-Ito default'''
        t = themeutil.active()
        assert t['palette'] == themeutil.THEMES['Okabe-Ito']['palette']
        assert t['base'] == '#56B4E9'

    def test_light_chrome_defaults(self, fake_streamlit):
        t = themeutil.active()
        assert t['scene_bg'] == '#FFFFFF' and t['font'] == '#31333F'

    def test_dark_chrome_defaults(self, fake_streamlit):
        fake_streamlit.context.theme.type = 'dark'
        t = themeutil.active()
        assert t['scene_bg'] == '#0E1117' and t['font'] == '#FAFAFA'

    def test_named_theme_selected(self, fake_streamlit):
        fake_streamlit.session_state[themeutil._SESSION_NAME] = 'Neon'
        assert themeutil.active()['highlight'] == '#FFFFFF'

    def test_per_colour_override_wins(self, fake_streamlit):
        fake_streamlit.session_state[themeutil._SESSION_NAME] = 'Neon'
        fake_streamlit.session_state[themeutil._SESSION_OVERRIDES] = {'base': '#123456', 'palette': ['#000000']}
        t = themeutil.active()
        assert t['base'] == '#123456' and t['palette'] == ['#000000']
        assert t['highlight'] == '#FFFFFF'  # untouched Neon key still resolves

    def test_unknown_theme_falls_back_per_key(self, fake_streamlit):
        '''An unrecognised theme name resolves entirely from the default's keys'''
        fake_streamlit.session_state[themeutil._SESSION_NAME] = 'does-not-exist'
        assert themeutil.active()['palette'] == themeutil.THEMES['Okabe-Ito']['palette']

    def test_empty_override_value_ignored(self, fake_streamlit):
        fake_streamlit.session_state[themeutil._SESSION_OVERRIDES] = {'base': '', 'palette': []}
        assert themeutil.active()['base'] == '#56B4E9'

# ====================
# Define tests for viewer/utils/plots.py
# ====================
class TestPlotHelpers:
    def test_find_col_first_substring_match(self):
        df = _demo_joined_df()
        assert plotsutil.find_col(df, 'is_reliable') == 'reliability.is_reliable'
        assert plotsutil.find_col(df, 'nonesuch') is None

    def test_numeric_columns_excludes_ids_and_flags(self):
        cols = plotsutil.numeric_columns(_demo_joined_df())
        assert 'equiv_diameter_nm' in cols
        assert 'label' not in cols and 'include' not in cols

    def test_axis_kwargs_ratio_locks_unit_range(self):
        assert plotsutil._axis_kwargs(_demo_joined_df()['closure_fill_ratio']) == {'range': [0, 1], 'dtick': 0.2}

    def test_axis_kwargs_small_integer_span(self):
        assert plotsutil._axis_kwargs(_demo_joined_df()['ev_count']) == {'tickformat': 'd', 'dtick': 1}

    def test_axis_kwargs_wide_integer_span(self):
        assert plotsutil._axis_kwargs(pd.Series([0, 100, 300, 600]))['dtick'] == 100

    def test_axis_kwargs_constant_series_is_empty(self):
        assert plotsutil._axis_kwargs(pd.Series([5.0, 5.0, 5.0])) == {}

    def test_axis_kwargs_float_span_untouched(self):
        assert 'range' not in plotsutil._axis_kwargs(_demo_joined_df()['equiv_diameter_nm'])

    def test_selected_labels_from_dict_event(self):
        event = {'selection': {'points': [{'customdata': [3]}, {'customdata': [1]}]}}
        assert plotsutil.selected_labels_from_event(event) == {1, 3}

    def test_selected_labels_from_none(self):
        assert plotsutil.selected_labels_from_event(None) == set()

    def test_selected_labels_ignores_nan_customdata(self):
        event = {'selection': {'points': [{'customdata': [float('nan')]}, {'customdata': [2]}]}}
        assert plotsutil.selected_labels_from_event(event) == {2}


class TestPlotBuilders:
    def test_feature_scatter_highlights_selection(self):
        fig = plotsutil.feature_scatter(_demo_joined_df(), 'equiv_diameter_nm', 'lumen_volume', {2})
        assert plotsutil.ACTIVE['highlight'] in list(fig.data[0].marker.color)

    def test_distribution_fixed_bin_size_anchored_at_zero(self):
        fig = plotsutil.distribution(_demo_joined_df(), 'equiv_diameter_nm', {1, 3}, bin_size=25)
        assert fig.data[0].xbins.size == 25 and fig.data[0].xbins.start == 0

    def test_distribution_auto_bins_when_size_omitted(self):
        fig = plotsutil.distribution(_demo_joined_df(), 'equiv_diameter_nm', set())
        assert fig.data[0].nbinsx == 30

    def test_concordance_returns_figure_when_columns_present(self):
        assert plotsutil.concordance(_demo_joined_df(), {1}) is not None

    def test_concordance_none_without_radius(self):
        df = _demo_joined_df().drop(columns=['radius'])
        assert plotsutil.concordance(df, set()) is None

    def test_concordance_analyse_column_choice_sets_x_title(self):
        fig = plotsutil.concordance(_demo_joined_df(), set(), analyse_col='major_axis_diameter')
        assert fig.layout.xaxis.title.text == 'Major axis diameter'

    def test_concordance_analyse_options(self):
        assert set(plotsutil.concordance_analyse_options(_demo_joined_df())) == {'equiv_diameter_nm', 'major_axis_diameter'}

    def test_reliability_colours_by_is_reliable(self):
        fig = plotsutil.reliability(_demo_joined_df(), set())
        colours = set(fig.data[0].marker.color)
        assert plotsutil.ACTIVE['reliable'] in colours and plotsutil.ACTIVE['unreliable'] in colours

    def test_reliability_none_without_rmse_column(self):
        df = _demo_joined_df().drop(columns=['reliability.rmse_nm'])
        assert plotsutil.reliability(df, set()) is None

    def test_use_theme_swaps_active_colours(self):
        try:
            plotsutil.use_theme({'highlight': '#ABCDEF', 'paper_bg': '#222222'})
            fig = plotsutil.feature_scatter(_demo_joined_df(), 'equiv_diameter_nm', 'lumen_volume', {2})
            assert '#ABCDEF' in list(fig.data[0].marker.color)
            assert fig.layout.paper_bgcolor == '#222222'
        finally:
            plotsutil.use_theme({'highlight': '#FFD400', 'paper_bg': '#FFFFFF'})

# ====================
# Define tests for viewer/utils/mesh.py
# ====================
class TestMesh:
    def test_point_cloud_trace_uses_nonzero_voxels(self):
        vol = np.zeros((10, 10, 10), dtype=np.float32)
        vol[2, 3, 4] = 1.0
        vol[5, 5, 5] = 1.0
        trace = meshutil.build_point_cloud_trace(vol)
        assert len(trace.x) == 2

    def test_point_cloud_trace_downsamples_before_count(self):
        vol = np.ones((10, 10, 10), dtype=np.float32)
        trace = meshutil.build_point_cloud_trace(vol, downsample=5)
        assert len(trace.x) == 8  # 2x2x2 after ::5

    def test_point_cloud_trace_caps_at_max_points(self, monkeypatch):
        monkeypatch.setattr(meshutil, 'MAX_SCATTER_POINTS', 100)
        vol = np.ones((20, 20, 20), dtype=np.float32)
        trace = meshutil.build_point_cloud_trace(vol)
        assert len(trace.x) == 100

    def test_label_mesh_traces_one_per_label(self):
        vol = np.zeros((24, 24, 24), dtype=np.uint16)
        vol[_hollow_sphere(vol.shape, (8, 8, 8), 6, 3)] = 1
        vol[_hollow_sphere(vol.shape, (17, 17, 17), 6, 3)] = 2
        traces = meshutil.build_label_mesh_traces(vol)
        assert set(traces) == {1, 2}

    def test_label_mesh_skips_tiny_components(self):
        vol = np.zeros((24, 24, 24), dtype=np.uint16)
        vol[_hollow_sphere(vol.shape, (12, 12, 12), 8, 4)] = 1
        vol[0, 0, 0] = 2  # single voxel, below MIN_LABEL_VOXELS
        traces = meshutil.build_label_mesh_traces(vol)
        assert set(traces) == {1}

    def test_label_mesh_vertices_in_xyz_order(self):
        vol = np.zeros((30, 20, 10), dtype=np.uint16)
        vol[_hollow_sphere(vol.shape, (15, 10, 5), 4, 2)] = 1
        trace = meshutil.build_label_mesh_traces(vol)[1]
        assert trace.x.max() <= 10 and trace.z.max() <= 30

    def test_dim_trace_recolours_only_when_highlighted(self):
        trace = types.SimpleNamespace(color='#123456')
        meshutil.dim_trace(trace, dim=True)
        assert trace.color == '#123456'
        meshutil.dim_trace(trace, dim=False)
        assert trace.color == meshutil.HIGHLIGHT_COLOR

# ====================
# Define tests for viewer/utils/stems.py
# ====================
class TestCanonicalStem:
    @pytest.mark.parametrize('name, expected', [
        ('t1_denoised.mrc', 't1'),
        ('t1.denoised.mrc', 't1'),
        ('t1_labelled.mrc', 't1'),
        ('t1_seg.mrc', 't1'),
        ('t1_labelled_model_fitted.mrc', 't1'),
        ('t1_labelled_model_results.json', 't1'),
        ('TS_01_binned_denoised.mrc', 'TS_01'),
        ('/data/runs/TS_01_labelled.mrc', 'TS_01'),
        ('plain.mrc', 'plain'),
    ])
    def test_tomo_stem_strips_known_suffix_runs(self, name, expected):
        assert stemutil.tomo_stem(name) == expected


# ====================
# Define tests for viewer/utils/gallery.py
# ====================
class TestGalleryScan:
    def _make_tree(self, root):
        (root / 'labelled').mkdir()
        (root / 'model').mkdir()
        (root / 'analyse').mkdir()
        labelled = np.zeros((16, 16, 16), dtype=np.int16)
        labelled[_hollow_sphere(labelled.shape, (8, 8, 8), 6, 3)] = 1
        _write_mrc(root / 'labelled' / 't1_labelled.mrc', labelled)
        _write_mrc(root / 'model' / 't1_labelled_model_fitted.mrc', labelled.astype(np.uint16))
        (root / 'model' / 't1_labelled_model_results.json').write_text(
            '{"parameters": {"n_vesicles_fitted": 1}, "results": ['
            '{"source_file": "t1_labelled.mrc", "label_id": 1, "radius": 6.0, '
            '"reliability": {"is_reliable": true}}]}'
        )
        (root / 'analyse' / 'evaluator-analyse_results.csv').write_text('tomogram,label\nt1_labelled.mrc,1\n')
        return root

    def test_default_stage_dirs_finds_common_names(self, tmp_path):
        (tmp_path / 'label').mkdir()
        (tmp_path / 'evaluator' / 'model').mkdir(parents=True)
        dirs = galleryutil.default_stage_dirs(tmp_path)
        assert dirs['labelled'] == tmp_path / 'label'
        assert dirs['model'] == tmp_path / 'evaluator' / 'model'
        assert dirs['raw'] is None

    def test_scan_returns_one_result_set_per_stem(self, tmp_path):
        root = self._make_tree(tmp_path)
        dirs = galleryutil.default_stage_dirs(root)
        results = galleryutil.scan_stage_dirs(dirs)
        assert [r.stem for r in results] == ['t1']

    def test_scan_populates_paths_and_counts(self, tmp_path):
        root = self._make_tree(tmp_path)
        rs = galleryutil.scan_stage_dirs(galleryutil.default_stage_dirs(root))[0]
        assert rs.labelled_mrc and rs.labelled_mrc.name == 't1_labelled.mrc'
        assert rs.fitted_mrc and rs.model_results_path
        assert rs.analyse_csv is not None
        assert rs.n_vesicles == 1 and rs.n_reliable == 1

    def test_scan_counts_labels_when_no_model(self, tmp_path):
        (tmp_path / 'labelled').mkdir()
        vol = np.zeros((16, 16, 16), dtype=np.int16)
        vol[_hollow_sphere(vol.shape, (5, 5, 5), 3, 1)] = 1
        vol[_hollow_sphere(vol.shape, (12, 12, 12), 3, 1)] = 2
        _write_mrc(tmp_path / 'labelled' / 't9_labelled.mrc', vol)
        rs = galleryutil.scan_stage_dirs(galleryutil.default_stage_dirs(tmp_path))[0]
        assert rs.n_vesicles == 2 and rs.n_reliable is None
        assert rs.fitted_mrc is None and rs.model_results_path is None

    def test_scan_empty_root_returns_nothing(self, tmp_path):
        assert galleryutil.scan_stage_dirs(galleryutil.default_stage_dirs(tmp_path)) == []

    def test_scan_denoised_raw_attaches_to_same_stem(self, tmp_path):
        (tmp_path / 'raw').mkdir()
        (tmp_path / 'labelled').mkdir()
        vol = np.zeros((16, 16, 16), dtype=np.int16)
        vol[_hollow_sphere(vol.shape, (8, 8, 8), 6, 3)] = 1
        _write_mrc(tmp_path / 'raw' / 't1_denoised.mrc', vol.astype(np.float32))
        _write_mrc(tmp_path / 'labelled' / 't1_labelled.mrc', vol)
        results = galleryutil.scan_stage_dirs(galleryutil.default_stage_dirs(tmp_path))
        assert [r.stem for r in results] == ['t1']
        rs = results[0]
        assert rs.raw_mrc and rs.raw_mrc.name == 't1_denoised.mrc'
        assert rs.labelled_mrc and rs.labelled_mrc.name == 't1_labelled.mrc'

    def test_midslice_preview_is_uint8_2d(self, tmp_path):
        vol = np.random.default_rng(0).random((12, 20, 24)).astype(np.float32)
        path = _write_mrc(tmp_path / 'raw.mrc', vol)
        img = galleryutil.midslice_preview(path)
        assert img.dtype == np.uint8 and img.shape == (20, 24)
        assert img.min() >= 0 and img.max() <= 255

    def test_midslice_preview_label_mode_normalises_by_max(self, tmp_path):
        vol = np.zeros((6, 8, 8), dtype=np.float32)
        vol[3] = 4.0  # centre slice all label id 4
        path = _write_mrc(tmp_path / 'lab.mrc', vol)
        img = galleryutil.midslice_preview(path, is_label=True)
        assert img.max() == 255

# ====================
# Define tests for viewer/utils/export.py
# ====================
class TestExportFilteredCSV:
    def test_writes_only_included_rows(self, tmp_path):
        src = tmp_path / 'joined.csv'
        src.write_text('placeholder\n')
        df = _demo_joined_df()
        out = export_filtered_csv(df, {1: True, 2: False, 3: True, 4: False}, src)
        written = pd.read_csv(out)
        assert set(written['label']) == {1, 3}

    def test_missing_flag_defaults_to_included(self, tmp_path):
        src = tmp_path / 'joined.csv'
        src.write_text('placeholder\n')
        out = export_filtered_csv(_demo_joined_df(), {2: False}, src)
        assert set(pd.read_csv(out)['label']) == {1, 3, 4}

    def test_output_name_follows_viewer_pattern(self, tmp_path):
        src = tmp_path / 'my_results.csv'
        src.write_text('placeholder\n')
        out = export_filtered_csv(_demo_joined_df(), {}, src)
        assert out.name == 'my_results_filtered.csv'
        assert out.parent == tmp_path

    def test_second_export_increments_suffix(self, tmp_path):
        src = tmp_path / 'r.csv'
        src.write_text('placeholder\n')
        first = export_filtered_csv(_demo_joined_df(), {}, src)
        second = export_filtered_csv(_demo_joined_df(), {}, src)
        assert first.name == 'r_filtered.csv' and second.name == 'r_filtered-1.csv'

# ====================
# Define tests for viewer/utils/dispatch.py
# ====================
class TestResolveStreamlit:
    def test_explicit_path_that_exists(self, tmp_path):
        fake = tmp_path / 'streamlit'
        fake.touch()
        assert dispatchutil.resolve_streamlit(fake) == fake

    def test_explicit_path_missing_raises(self, tmp_path):
        with pytest.raises(dispatchutil.StreamlitNotFoundError):
            dispatchutil.resolve_streamlit(tmp_path / 'nope')

    def test_falls_back_to_path_lookup(self, monkeypatch):
        monkeypatch.setattr(dispatchutil.shutil, 'which', lambda name: '/usr/bin/streamlit')
        assert dispatchutil.resolve_streamlit(None) == Path('/usr/bin/streamlit')

    def test_not_on_path_raises(self, monkeypatch):
        monkeypatch.setattr(dispatchutil.shutil, 'which', lambda name: None)
        with pytest.raises(dispatchutil.StreamlitNotFoundError):
            dispatchutil.resolve_streamlit(None)

    def test_app_path_points_at_packaged_entrypoint(self):
        p = dispatchutil._app_path()
        assert p.name == 'viewer.py' and p.parent.name == 'app' and p.exists()


class TestResolvePort:
    def test_zero_passes_through_without_probe(self):
        assert dispatchutil.resolve_port(0) == 0

    def test_in_use_port_falls_back_to_zero(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('localhost', 0))
        listener.listen(1)
        try:
            in_use = listener.getsockname()[1]
            assert dispatchutil.resolve_port(in_use) == 0
        finally:
            listener.close()

    def test_free_port_passes_through(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        free = s.getsockname()[1]
        s.close()  # closed before probe -> nothing listening
        assert dispatchutil.resolve_port(free) == free
