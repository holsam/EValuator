# -- Import external dependencies ------
import pytest, tomllib, typer

# -- Import internal dependencies ------
from evaluator.commands.config import (
    config_exists,
    config_init,
    config_list,
    config_reset,
    config_verify,
)
from evaluator.utils.settings import loadDefaultConfig

# -- Define shared fixture -------------
@pytest.fixture
def patched_config(tmp_path, monkeypatch):
    """
    Patches userConfigPath in commands/config to point at a temp file,
    and returns that Path. The file does not exist initially.
    """
    config_path = tmp_path / "evaluator" / "config.toml"
    monkeypatch.setattr("evaluator.commands.config.userConfigPath", lambda: config_path)
    return config_path

# -- Define config init test -----------
class TestConfigInitIntegration:
    def test_creates_config_file(self, patched_config):
        config_init()
        assert patched_config.exists()
    def test_written_config_matches_defaults(self, patched_config):
        config_init()
        with patched_config.open("rb") as f:
            written = tomllib.load(f)
        assert written == loadDefaultConfig()
    def test_does_not_overwrite_existing_file(self, patched_config):
        """init must refuse to overwrite a file that already exists."""
        patched_config.parent.mkdir(parents=True, exist_ok=True)
        patched_config.write_bytes(b"[global]\nverbose = true\n")
        config_init()   # must not overwrite
        with patched_config.open("rb") as f:
            content = tomllib.load(f)
        assert content["global"]["verbose"] is True

# -- Define config exists test ---------
class TestConfigExistsIntegration:
    def test_exits_non_zero_when_no_file(self, patched_config):
        with pytest.raises((typer.Exit, SystemExit)):
            config_exists()
    def test_passes_when_file_exists(self, patched_config):
        config_init()
        config_exists()   # must not raise

# -- Define config reset test ----------
class TestConfigResetIntegration:
    def test_reset_restores_defaults(self, patched_config):
        """After a modified config is written, reset must restore all defaults."""
        config_init()
        # Mutate the config on disk
        patched_config.write_bytes(
            b"[global]\nverbose = true\n"
            b"[filter]\nclosure_fill_threshold = 0.99\n"
            b"max_diameter_nm = 100.0\nmin_diameter_nm = 10.0\n"
            b"membrane_thickness_nm = 5\n"
            b"[label]\noverlay_style = \"filled\"\nn_slices = 3\n"
            b"[mplstyle]\ncolourmap = \"viridis\"\nalpha_fill = 0.9\n"
            b"contour_linewidth = 3.0\nlabel_fontsize = 12\nfigure_dpi = 72\n"
            b"[visualisation]\nfps = 10\ndownsample = 4\n"
        )
        config_reset(force=True)
        with patched_config.open("rb") as f:
            restored = tomllib.load(f)
        assert restored == loadDefaultConfig()
    def test_force_flag_skips_confirmation(self, patched_config):
        """Passing force=True must not raise and must complete without prompting."""
        config_init()
        config_reset(force=True)   # must not raise
        assert patched_config.exists()

# -- Define config verify test ---------
class TestConfigVerifyIntegration:
    def test_verify_passes_for_default_config(self, patched_config):
        config_init()
        config_verify()   # must not raise
    def test_verify_exits_for_incomplete_config(self, patched_config):
        patched_config.parent.mkdir(parents=True, exist_ok=True)
        # Write a deliberately incomplete TOML
        patched_config.write_bytes(b"[global]\nverbose = false\n")
        with pytest.raises((typer.Exit, SystemExit)):
            config_verify()

# -- Define config list test -----------
class TestConfigListIntegration:
    def test_list_runs_without_error_with_user_config(self, patched_config, capsys):
        config_init()
        config_list()   # must not raise
    def test_list_runs_without_error_without_user_config(self, patched_config, capsys):
        """Without a user config, config_list must fall back to defaults silently."""
        config_list()   # must not raise