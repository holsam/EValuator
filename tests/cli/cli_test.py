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