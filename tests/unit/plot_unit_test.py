'''
Unit tests for `evaluator plot`
'''

# ====================
# Import external dependencies
# ====================
import pytest, subprocess, tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

# ====================
# Import evaluator plot functions
# ====================
from evaluator.commands.plot.plot import run_plot
from evaluator.commands.plot.utils.dispatch import (
    resolve_rscript,
    dispatch,
    RscriptNotFoundError,
    RscriptError,
)
from evaluator.commands.plot.utils.input import (
    PlotRun,
    resolve_plot_inputs,
    available_sections,
)

# ====================
# Define helpers
# ====================
def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path

def _sheet(path: Path, rows: list[dict]) -> Path:
    header = ['sample_id', 'path', 'group', 'replicate']
    lines = ['\t'.join(header)]
    for row in rows:
        lines.append('\t'.join(str(row.get(col, '')) for col in header))
    return _write(path, '\n'.join(lines) + '\n')

def _make_analyse_csv(tmp_path):
    path = tmp_path / 'analyse.csv'
    path.write_text(
        'tomogram,label,equiv_diameter_nm,major_axis_diameter,minor_axis_diameter,'
        'aspect_ratio,eccentricity,membrane_volume,lumen_volume,surface_area,'
        'is_enclosed,closure_fill_ratio\n'
        'tomo1.mrc,1,80.0,90.0,70.0,1.28,0.5,50000,30000,20000,True,0.4\n'
    )
    return path

# ====================
# Define tests for plot/utils/input.py
# ====================
class TestPlotUtilsInput:
    # == Define tests for resolve_plot_inputs with single file (no sample sheet) ==
    def test_analyse_only(self, tmp_path):
        analyse = _write(tmp_path / 'analyse.csv', 'tomogram,label\n')
        runs, multi_run, sheet_path = resolve_plot_inputs(analyse, None)
        assert multi_run is False
        assert sheet_path is None
        assert runs == [PlotRun(sample_id='sample', analyse_path=analyse, model_path=None)]

    def test_model_only(self, tmp_path):
        model = _write(tmp_path / 'model.json', '{}')
        runs, multi_run, sheet_path = resolve_plot_inputs(None, model)
        assert multi_run is False
        assert runs == [PlotRun(sample_id='sample', analyse_path=None, model_path=model)]

    def test_both_present(self, tmp_path):
        analyse = _write(tmp_path / 'analyse.csv', 'tomogram,label\n')
        model = _write(tmp_path / 'model.json', '{}')
        runs, multi_run, sheet_path = resolve_plot_inputs(analyse, model)
        assert multi_run is False
        assert runs == [PlotRun(sample_id='sample', analyse_path=analyse, model_path=model)]

    def test_csv_suffix_never_treated_as_sheet(self, tmp_path):
        '''A .csv with a sample_id-like header must not be sniffed as a sheet (only .tsv/.txt are)'''
        analyse = _write(tmp_path / 'analyse.csv', 'sample_id\tpath\n')
        runs, multi_run, sheet_path = resolve_plot_inputs(analyse, None)
        assert multi_run is False

    # == Define tests for resolve_plot_inputs with a sample sheet (from analyse or model) ==
    def test_analyse_sheet_only(self, tmp_path):
        a1 = _write(tmp_path / 'a1.csv', 'tomogram,label\n')
        a2 = _write(tmp_path / 'a2.csv', 'tomogram,label\n')
        sheet = _sheet(tmp_path / 'sheet.tsv', [
            {'sample_id': 's1', 'path': a1, 'group': 'control'},
            {'sample_id': 's2', 'path': a2, 'group': 'treated'},
        ])
        runs, multi_run, sheet_path = resolve_plot_inputs(sheet, None)
        assert multi_run is True
        assert sheet_path == sheet
        assert {r.sample_id for r in runs} == {'s1', 's2'}
        assert {r.group for r in runs} == {'control', 'treated'}

    def test_model_sheet_only(self, tmp_path):
        m1 = _write(tmp_path / 'm1.json', '{}')
        sheet = _sheet(tmp_path / 'sheet.tsv', [{'sample_id': 's1', 'path': m1, 'group': 'g'}])
        runs, multi_run, sheet_path = resolve_plot_inputs(None, sheet)
        assert multi_run is True
        assert runs[0].model_path == m1
        assert runs[0].analyse_path is None

    def test_both_sheets_joined_on_sample_id(self, tmp_path):
        a1 = _write(tmp_path / 'a1.csv', 'tomogram,label\n')
        m1 = _write(tmp_path / 'm1.json', '{}')
        analyse_sheet = _sheet(tmp_path / 'analyse_sheet.tsv', [{'sample_id': 's1', 'path': a1, 'group': 'g'}])
        model_sheet = _sheet(tmp_path / 'model_sheet.tsv', [{'sample_id': 's1', 'path': m1, 'group': 'g'}])
        runs, multi_run, sheet_path = resolve_plot_inputs(analyse_sheet, model_sheet)
        assert multi_run is True
        # analyse sheet is preferred as the returned sheet_path when both sides are sheets
        assert sheet_path == analyse_sheet
        assert len(runs) == 1
        assert runs[0].analyse_path == a1
        assert runs[0].model_path == m1

    def test_replicate_parsed_as_int(self, tmp_path):
        a1 = _write(tmp_path / 'a1.csv', 'tomogram,label\n')
        sheet = _sheet(tmp_path / 'sheet.tsv', [{'sample_id': 's1', 'path': a1, 'group': 'g', 'replicate': 2}])
        runs, _, _ = resolve_plot_inputs(sheet, None)
        assert runs[0].replicate == 2

    def test_missing_sample_id_column_raises(self, tmp_path):
        bad = _write(tmp_path / 'sheet.tsv', 'path\tgroup\n/x.csv\tg\n')
        with pytest.raises(ValueError):
            resolve_plot_inputs(bad, None)

    # == Define tests for available_sections ==
    def test_analyse_only_gives_core_sections(self):
        runs = [PlotRun(sample_id='s', analyse_path=Path('a.csv'), model_path=None)]
        assert available_sections(runs, False) == ['distributions', 'qc', 'scatter']

    def test_model_only_gives_no_sections(self):
        '''No section currently runs on model output alone'''
        runs = [PlotRun(sample_id='s', analyse_path=None, model_path=Path('m.json'))]
        assert available_sections(runs, False) == []

    def test_analyse_and_model_adds_concordance(self):
        runs = [PlotRun(sample_id='s', analyse_path=Path('a.csv'), model_path=Path('m.json'))]
        sections = available_sections(runs, False)
        assert 'concordance' in sections

    def test_single_group_excludes_compare(self):
        runs = [
            PlotRun(sample_id='s1', analyse_path=Path('a1.csv'), model_path=None, group='g'),
            PlotRun(sample_id='s2', analyse_path=Path('a2.csv'), model_path=None, group='g'),
        ]
        assert 'compare' not in available_sections(runs, True)

    def test_multiple_groups_adds_compare(self):
        runs = [
            PlotRun(sample_id='s1', analyse_path=Path('a1.csv'), model_path=None, group='control'),
            PlotRun(sample_id='s2', analyse_path=Path('a2.csv'), model_path=None, group='treated'),
        ]
        assert 'compare' in available_sections(runs, True)

    def test_single_run_mode_never_adds_compare(self):
        '''compare requires multi_run even if (somehow) groups differ'''
        runs = [PlotRun(sample_id='s', analyse_path=Path('a.csv'), model_path=None, group='g')]
        assert 'compare' not in available_sections(runs, False)
    
# ====================
# Define tests for plot/utils/dispatch.py
# ====================
class TestPlotUtilsDispatch:
    # == Define tests for resolve_rscript ==
    def test_explicit_path_that_exists(self, tmp_path):
        fake_bin = tmp_path / 'Rscript'
        fake_bin.touch()
        assert resolve_rscript(fake_bin) == fake_bin

    def test_explicit_path_missing_raises(self, tmp_path):
        missing = tmp_path / 'does_not_exist'
        with pytest.raises(RscriptNotFoundError):
            resolve_rscript(missing)

    def test_falls_back_to_path_lookup(self, monkeypatch):
        monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/Rscript')
        assert resolve_rscript(None) == Path('/usr/bin/Rscript')

    def test_not_on_path_raises(self, monkeypatch):
        monkeypatch.setattr('shutil.which', lambda name: None)
        with pytest.raises(RscriptNotFoundError):
            resolve_rscript(None)

    # == Define tests for dispatch ==
    def test_builds_expected_command(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            dispatch(Path('/usr/bin/Rscript'), 'qc.R', ['/out', '/analyse.csv', 'single', 0.05])
        cmd = mock_run.call_args.args[0]
        assert cmd[0] == '/usr/bin/Rscript'
        assert cmd[1].endswith('r/qc.R')
        assert cmd[2:] == ['/out', '/analyse.csv', 'single', '0.05']

    def test_nonzero_exit_raises_rscript_error_with_stderr(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='boom')
            with pytest.raises(RscriptError, match='boom'):
                dispatch(Path('/usr/bin/Rscript'), 'qc.R', [])

    def test_zero_exit_does_not_raise(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            dispatch(Path('/usr/bin/Rscript'), 'qc.R', [])

# ====================
# Define tests for plot/plot.py
# ====================
class TestPlot:
    # == Define tests for run_plot section gating ==
    def test_requested_but_unrunnable_section_is_skipped(self, tmp_path):
        '''--section concordance with only --analyse given is not runnable and should be skipped'''
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch') as mock_dispatch:
            run_plot(analyse, None, tmp_path, sections=['concordance'], all_sections=False, overwrite=False, rscript=None)
        mock_dispatch.assert_not_called()

    def test_all_sections_runs_every_runnable_section(self, tmp_path):
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch') as mock_dispatch:
            run_plot(analyse, None, tmp_path, sections=None, all_sections=True, overwrite=False, rscript=None)
        called_scripts = {call.args[1] for call in mock_dispatch.call_args_list}
        assert called_scripts == {'distributions.R', 'qc.R', 'scatter.R'}

    def test_qc_passes_fill_ratio_threshold_as_fourth_arg(self, tmp_path):
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch') as mock_dispatch:
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=False, rscript=None)
        args = mock_dispatch.call_args.args[2]
        assert args[3] == 0.05  # PlotConfig default fill_ratio_flag_threshold

    def test_section_failure_is_not_fatal(self, tmp_path):
        '''One section raising RscriptError must not prevent other sections from running'''
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch', side_effect=RscriptError('boom')):
            run_plot(analyse, None, tmp_path, sections=['distributions', 'qc'], all_sections=False, overwrite=False, rscript=None)  # must not raise

    # == Define tests for --overwrite option ==
    def test_existing_section_dir_skipped_without_overwrite(self, tmp_path):
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch') as mock_dispatch:
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=False, rscript=None)
            mock_dispatch.reset_mock()
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=False, rscript=None)
        mock_dispatch.assert_not_called()

    def test_overwrite_reruns_existing_section(self, tmp_path):
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch') as mock_dispatch:
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=False, rscript=None)
            mock_dispatch.reset_mock()
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=True, rscript=None)
        mock_dispatch.assert_called_once()

    # == Define tests for _write_index ==
    def test_index_md_lists_completed_sections(self, tmp_path):
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch'):
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=False, rscript=None)
        index = (tmp_path / 'evaluator' / 'plot' / 'index.md').read_text()
        assert 'qc/' in index

    def test_params_toml_written(self, tmp_path):
        analyse = _make_analyse_csv(tmp_path)
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch'):
            run_plot(analyse, None, tmp_path, sections=['qc'], all_sections=False, overwrite=False, rscript=None)
        params = tomllib.loads((tmp_path / 'evaluator' / 'plot' / 'params.toml').read_text())
        assert params['fill_ratio_flag_threshold'] == 0.05
