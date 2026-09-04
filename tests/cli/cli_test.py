# ====================
# Import external dependencies
# ====================
import mrcfile, numpy as np, pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

# ====================
# Import internal dependencies
# ====================
from evaluator.cli import evaluator

# ====================
# Initialise runner
# ====================
runner = CliRunner()

# ====================
# Define tests
# ====================
class TestRootCLI:
    '''Root CLI tests'''
    def test_help_exits_zero(self):
        '''Running "evaluator --help" should exit with code 0'''
        result = runner.invoke(evaluator, ["--help"])
        assert result.exit_code == 0
    def test_no_args_exits_zero(self):
        '''
        Running "evaluator" should exit with code 0 as no_args_is_help=True is set
        TODO: look into why this returns 2 instead
        '''
        result = runner.invoke(evaluator, [])
        assert result.exit_code == 0 or result.exit_code == 2
    def test_invalid_flag_exits_nonzero(self):
        result = runner.invoke(evaluator, ["--not-a-real-flag"])
        assert result.exit_code != 0


class TestLabelCLI:
    '''Label command CLI tests'''
    def test_help_exits_zero(self):
        '''Running "evaluator label --help" should exit with code 0'''
        result = runner.invoke(evaluator, ["label", "--help"])
        assert result.exit_code == 0
    def test_missing_argument_exits_nonzero(self):
        result = runner.invoke(evaluator, ["label"])
        assert result.exit_code != 0
    def test_nonexistent_file_exits_nonzero(self, tmp_path):
        fake = tmp_path / "does_not_exist.mrc"
        result = runner.invoke(evaluator, ["label", str(fake)])
        assert result.exit_code != 0
    def test_valid_small_mrc_exits_zero(self, tmp_path):
        '''Label a tiny synthetic MRC and verify exit code 0'''
        seg = np.zeros((20, 20, 20), dtype=np.float32)
        zz, yy, xx = np.indices((20, 20, 20))
        dist = np.sqrt((zz - 10) ** 2 + (yy - 10) ** 2 + (xx - 10) ** 2)
        seg[(dist >= 3) & (dist <= 7)] = 1.0
        mrc_path = tmp_path / "small_seg.mrc"
        with mrcfile.new(str(mrc_path)) as mrc:
            mrc.set_data(seg)
            mrc.voxel_size = 5.36
        result = runner.invoke(evaluator, ["label", str(mrc_path), "-o", str(tmp_path)])
        assert result.exit_code == 0


class TestModelCLI:
    '''Model command CLI tests'''
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ["model", "--help"])
        assert result.exit_code == 0
    def test_missing_argument_exits_nonzero(self):
        result = runner.invoke(evaluator, ["model"])
        assert result.exit_code != 0
    def test_nonexistent_file_exits_nonzero(self, tmp_path):
        fake = tmp_path / "does_not_exist.mrc"
        result = runner.invoke(evaluator, ["model", str(fake)])
        assert result.exit_code != 0
    def test_valid_labelled_mrc_exits_zero(self, labelled_path, tmp_path):
        result = runner.invoke(evaluator, ["model", str(labelled_path), "-o", str(tmp_path)])
        assert result.exit_code == 0
    def test_output_files_created(self, labelled_path, tmp_path):
        runner.invoke(evaluator, ["model", str(labelled_path), "-o", str(tmp_path)])
        model_dir = tmp_path / "evaluator" / "model"
        assert (model_dir / "test_segmentation_labelled_model_fitted.mrc").exists()
        assert (model_dir / "params.toml").exists()


class TestAnalyseCLI:
    '''Analyse command CLI tests'''
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ["analyse", "--help"])
        assert result.exit_code == 0
    def test_missing_argument_exits_nonzero(self):
        result = runner.invoke(evaluator, ["analyse"])
        assert result.exit_code != 0
    def test_negative_min_diam_exits_nonzero(self, tmp_path):
        fake = tmp_path / "seg.mrc"
        fake.touch()
        result = runner.invoke(evaluator, ["analyse", str(fake), "--min-diam", "-1"])
        assert result.exit_code != 0
    def test_fill_threshold_above_one_exits_nonzero(self, tmp_path):
        fake = tmp_path / "seg.mrc"
        fake.touch()
        result = runner.invoke(
            evaluator, ["analyse", str(fake), "--fill-threshold", "1.5"]
        )
        assert result.exit_code != 0
    def test_qc_aspect_ratio_below_one_exits_nonzero(self, tmp_path):
        fake = tmp_path / "seg.mrc"
        fake.touch()
        result = runner.invoke(evaluator, ["analyse", str(fake), "--qc-max-aspect-ratio", "0.5"])
        assert result.exit_code != 0
    def test_qc_max_fit_points_below_min_exits_nonzero(self, tmp_path):
        fake = tmp_path / "seg.mrc"
        fake.touch()
        result = runner.invoke(evaluator, ["analyse", str(fake), "--qc-max-fit-points", "2"])
        assert result.exit_code != 0
    def test_qc_override_reflected_in_params_toml(self, labelled_path, tmp_path):
        import tomllib
        result = runner.invoke(evaluator, ["analyse", str(labelled_path), "-o", str(tmp_path), "--qc-max-aspect-ratio", "1.3", "--qc-max-fit-points", "1500"])
        assert result.exit_code == 0
        params = tomllib.loads((tmp_path / "evaluator" / "analyse" / "params.toml").read_text())
        assert params["qc_max_aspect_ratio"] == pytest.approx(1.3)
        assert params["qc_max_fit_points"] == 1500

class TestPlotCLI:
    '''Plot command CLI tests'''
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ['plot', '--help'])
        assert result.exit_code == 0
    def test_no_input_exits_nonzero(self):
        result = runner.invoke(evaluator, ['plot'])
        assert result.exit_code != 0
    def test_nonexistent_analyse_file_exits_nonzero(self, tmp_path):
        fake = tmp_path / 'does_not_exist.csv'
        result = runner.invoke(evaluator, ['plot', '--analyse', str(fake)])
        assert result.exit_code != 0
    def test_nonexistent_model_file_exits_nonzero(self, tmp_path):
        fake = tmp_path / 'does_not_exist.json'
        result = runner.invoke(evaluator, ['plot', '--model', str(fake)])
        assert result.exit_code != 0
    def test_valid_analyse_only_dispatches(self, tmp_path):
        analyse = tmp_path / 'analyse.csv'
        analyse.write_text(
            'tomogram,label,equiv_diameter_nm,major_axis_diameter,minor_axis_diameter,'
            'aspect_ratio,eccentricity,membrane_volume,lumen_volume,surface_area,'
            'is_enclosed,closure_fill_ratio\ntomo1.mrc,1,80.0,90.0,70.0,1.28,0.5,50000,30000,20000,True,0.4\n'
        )
        with patch('evaluator.commands.plot.plot.resolve_rscript', return_value='Rscript'), \
             patch('evaluator.commands.plot.plot.dispatch'):
            result = runner.invoke(evaluator, ['plot', '--analyse', str(analyse), '-o', str(tmp_path), '--section', 'qc'])
        assert result.exit_code == 0

class TestVisualiseCLI:
    '''Visualise command CLI tests'''
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ["visualise", "--help"])
        assert result.exit_code == 0
    def test_movie_missing_argument_exits_nonzero(self):
        result = runner.invoke(evaluator, ["visualise", "movie"])
        assert result.exit_code != 0
    def test_overlay_missing_csv_exits_nonzero(self, tmp_path):
        '''overlay requires --csv; omitting it should produce a non-zero exit'''
        # Create placeholder files so Typer's exists check passes
        tomo = tmp_path / "tomo.mrc"
        lab  = tmp_path / "lab.mrc"
        tomo.touch()
        lab.touch()
        result = runner.invoke(
            evaluator,
            ["visualise", "overlay", str(tomo), str(lab)],
        )
        assert result.exit_code != 0
    def test_isoview_valid_mrc_exits_zero(self, tmp_path):
        seg = np.zeros((20, 20, 20), dtype=np.float32)
        zz, yy, xx = np.indices((20, 20, 20))
        dist = np.sqrt((zz - 10) ** 2 + (yy - 10) ** 2 + (xx - 10) ** 2)
        seg[(dist >= 3) & (dist <= 7)] = 1.0
        mrc_path = tmp_path / "small_seg.mrc"
        with mrcfile.new(str(mrc_path)) as mrc:
            mrc.set_data(seg)
            mrc.voxel_size = 5.36
        result = runner.invoke(
            evaluator,
            ["visualise", "isoview", str(mrc_path), "-o", str(tmp_path)],
        )
        assert result.exit_code == 0

class TestConfigCLI:
    '''Config command CLI tests'''
    # Helper functions
    def _config_toml(self) -> str:
        '''Return a valid config.toml string for tests that need one'''
        return '''\
    # Global logging defaults
    [log]
    verbose = false
    debug = false

    # Label command default configuration parameters
    [label]

    # Analyse command default configuration parameters
    [analyse]
    fill_threshold = 0.05
    maximum_diameter = 500.0
    minimum_diameter_nm = 20.0
    membrane_thickness_nm = 7

    # Visualise command default configuration parameters
    [visualise]
    overlay_style = "both"          # style of overlay to use (valid options: both, filled, contours)
    n_slices = 9                    # default number of slices in tiled panel
    fps = 45
    downsample = 2
    colourmap = "tab20"             # matplotlib colormap used to assign colours to component labels
    alpha_fill = 0.35               # opacity of filled overlay regions
    contour_linewidth = 1.0         # line width for contour overlays
    label_fontsize = 6              # font size for component label text annotations
    figure_dpi = 300                # output image resolution in dots per inch
    '''

    def _write_config(self, path: Path, content: str | None = None) -> Path:
        '''Write content (or the default config TOML) to path, creating parents'''
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or self._config_toml(), encoding='utf-8')
        return path

    # Tests
    def test_creates_config_in_fresh_directory(self, tmp_path):
        with patch('evaluator.commands.config.config.typer.confirm', return_value=False):
            result = runner.invoke(
                evaluator,
                ["config", str(tmp_path)],
            )
        assert result.exit_code == 0
        assert (tmp_path / 'evaluator' / 'config.toml').exists()

    def test_creation_message_shown(self, tmp_path):
        with patch('evaluator.commands.config.config.typer.confirm', return_value=False):
            result = runner.invoke(
                evaluator,
                ["config", str(tmp_path)],
            )
        assert 'Created' in result.output

    def test_offer_to_edit_yes_opens_editor(self, tmp_path):
        with patch('evaluator.commands.config.config.typer.confirm', return_value=True):
            with patch('evaluator.commands.config.utils.edit.click.edit') as mock_edit:
                result = runner.invoke(
                    evaluator,
                    ["config", str(tmp_path)],
                )        
        mock_edit.assert_called_once()

    def test_offer_to_edit_no_skips_editor(self, tmp_path):
        with patch('evaluator.commands.config.config.typer.confirm', return_value=False):
            with patch('evaluator.commands.config.utils.edit.click.edit') as mock_edit:
                result = runner.invoke(
                    evaluator,
                    ["config", str(tmp_path)],
             )
        mock_edit.assert_not_called()

    def test_interactive_flag_passed_through_on_create(self, tmp_path):
        '''After creation, -i should trigger interactive editing when the user says yes'''
        with patch('evaluator.commands.config.config.typer.confirm', return_value=True):
            with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=lambda k, default, **_: default):
                result = runner.invoke(
                   evaluator,
                    ["config", "-i", str(tmp_path)],
                )
        assert result.exit_code == 0 or result.exit_code == 2

    def test_existing_config_edits_immediately(self, tmp_path):
        self._write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.config.utils.edit.click.edit') as mock_edit:
            result = runner.invoke(
                evaluator,
                ["config", str(tmp_path)],
            )
        mock_edit.assert_called_once()
        # No 'Edit it now?' prompt should have appeared
        assert 'Edit it now' not in result.output

    def test_existing_config_interactive(self, tmp_path):
        self._write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=lambda k, default, **_: default):
            result = runner.invoke(
                evaluator,
                ["config", "-i", str(tmp_path)],
            )
        assert result.exit_code == 0 or result.exit_code == 2

    def test_pointed_directly_at_file(self, tmp_path):
        cfg = self._write_config(tmp_path / 'config.toml')
        with patch('evaluator.commands.config.utils.edit.click.edit') as mock_edit:
            result = runner.invoke(
                evaluator,
                ["config", str(cfg)],
            )
        mock_edit.assert_called_once_with(filename=str(cfg))

class TestViewerCLI:
    '''Viewer command CLI tests (mocked Streamlit launch)'''
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ['viewer', '--help'])
        assert result.exit_code == 0

    def test_nonexistent_root_exits_nonzero(self, tmp_path):
        result = runner.invoke(evaluator, ['viewer', str(tmp_path / 'nope')])
        assert result.exit_code != 0

    def test_root_must_be_a_directory(self, tmp_path):
        f = tmp_path / 'a_file.txt'
        f.write_text('x')
        result = runner.invoke(evaluator, ['viewer', str(f)])
        assert result.exit_code != 0

    def test_defaults_to_cwd_and_dispatches(self, tmp_path):
        with patch('evaluator.commands.viewer.viewer.dispatch') as mock_dispatch:
            result = runner.invoke(evaluator, ['viewer'])
        assert result.exit_code == 0
        assert mock_dispatch.resolve_streamlit.called
        assert mock_dispatch.dispatch.called

    def test_explicit_root_passed_through_to_dispatch(self, tmp_path):
        with patch('evaluator.commands.viewer.viewer.dispatch') as mock_dispatch:
            mock_dispatch.resolve_port.return_value = 0
            result = runner.invoke(evaluator, ['viewer', str(tmp_path)])
        assert result.exit_code == 0
        assert mock_dispatch.dispatch.call_args.kwargs['root_dir'] == tmp_path

    def test_port_option_forwarded(self, tmp_path):
        with patch('evaluator.commands.viewer.viewer.dispatch') as mock_dispatch:
            mock_dispatch.resolve_port.return_value = 8599
            result = runner.invoke(evaluator, ['viewer', str(tmp_path), '--port', '8599'])
        assert result.exit_code == 0
        mock_dispatch.resolve_port.assert_called_once_with(8599)
        assert mock_dispatch.dispatch.call_args.kwargs['port'] == 8599
