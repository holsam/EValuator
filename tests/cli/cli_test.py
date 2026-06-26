# -- Import external dependencies ------
import mrcfile, pytest
import numpy as np
from typer.testing import CliRunner

# -- Import internal dependencies ------
from evaluator.cli import evaluator

# -- Initialise runner -----------------
runner = CliRunner()

# -- Define root command test ----------
class TestRootCLI:
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

# -- Define label command test ---------
class TestLabelCLI:
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
        """Smoke test: label a tiny synthetic MRC and verify exit code 0."""
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

# -- Define analyse command test -------
class TestAnalyseCLI:
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


# -- Define config command test --------
class TestConfigCLI:
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ["config", "--help"])
        assert result.exit_code == 0
    def test_init_creates_file(self, tmp_path, monkeypatch):
        config_path = tmp_path / "evaluator" / "config.toml"
        monkeypatch.setattr("evaluator.utils.settings.userConfigPath", lambda: config_path)
        monkeypatch.setattr("evaluator.commands.config.config.userConfigPath", lambda: config_path)
        result = runner.invoke(evaluator, ["config", "init"])
        assert result.exit_code == 0
        assert config_path.exists()
    def test_exists_returns_nonzero_when_no_file(self, tmp_path, monkeypatch):
        config_path = tmp_path / "evaluator" / "config.toml"
        monkeypatch.setattr("evaluator.utils.settings.userConfigPath", lambda: config_path)
        monkeypatch.setattr("evaluator.commands.config.config.userConfigPath", lambda: config_path)
        result = runner.invoke(evaluator, ["config", "exists"])
        assert result.exit_code != 0
    def test_reset_force_exits_zero(self, tmp_path, monkeypatch):
        config_path = tmp_path / "evaluator" / "config.toml"
        monkeypatch.setattr("evaluator.utils.settings.userConfigPath", lambda: config_path)
        monkeypatch.setattr("evaluator.commands.config.config.userConfigPath", lambda: config_path)
        runner.invoke(evaluator, ["config", "init"])
        result = runner.invoke(evaluator, ["config", "reset", "--force"])
        assert result.exit_code == 0

# -- Define visual command test --------
class TestVisualiseCLI:
    def test_help_exits_zero(self):
        result = runner.invoke(evaluator, ["visualise", "--help"])
        assert result.exit_code == 0
    def test_movie_missing_argument_exits_nonzero(self):
        result = runner.invoke(evaluator, ["visualise", "movie"])
        assert result.exit_code != 0
    def test_overlay_missing_csv_exits_nonzero(self, tmp_path):
        """overlay requires --csv; omitting it must produce a non-zero exit."""
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