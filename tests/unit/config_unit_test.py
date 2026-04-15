'''
All tests that touch the filesystem redirect userConfigPath() to a temporary
directory via monkeypatch so that the user's real config file is never touched.
'''

# -- Import external dependencies ------
import pytest, tomllib

# -- Import internal dependencies ------
from evaluator.commands.config import (
    config_init,
    config_verify,
    flattenToml,
    internalConfigCheck,
    loadUserConfig,
    writeUserConfig,
)
from evaluator.utils.settings import loadDefaultConfig

# -- Define shared fixture -------------
@pytest.fixture
def config_path(tmp_path, monkeypatch):
    """
    Returns a Path to a non-existent config file in a temp directory and
    patches userConfigPath in both the settings and config command modules
    to return that path.
    """
    path = tmp_path / "evaluator" / "config.toml"
    monkeypatch.setattr("evaluator.commands.config.userConfigPath", lambda: path)
    monkeypatch.setattr("evaluator.utils.settings.userConfigPath",  lambda: path)
    return path

# -- Define flatten TOML test ----------
class TestFlattenToml:
    def test_nested_dict(self):
        flat = flattenToml({"a": {"b": 1, "c": 2}, "d": 3})
        assert flat == {"a.b": 1, "a.c": 2, "d": 3}
    def test_flat_dict_unchanged(self):
        flat = flattenToml({"x": 1, "y": "hello"})
        assert flat == {"x": 1, "y": "hello"}
    def test_deeply_nested(self):
        flat = flattenToml({"a": {"b": {"c": 42}}})
        assert flat == {"a.b.c": 42}
    def test_empty_dict(self):
        assert flattenToml({}) == {}
    def test_mixed_depth(self):
        flat = flattenToml({"top": 1, "nested": {"inner": 2}})
        assert flat == {"top": 1, "nested.inner": 2}

# -- Define write & load user config test
class TestWriteLoadUserConfig:
    def test_write_creates_file(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        writeUserConfig({"global": {"verbose": False}})
        assert config_path.exists()
    def test_write_creates_parent_directory(self, config_path):
        assert not config_path.parent.exists()
        writeUserConfig({"global": {"verbose": False}})
        assert config_path.parent.exists()
    def test_roundtrip_defaults(self, config_path):
        """Writing and reading the full default config must be lossless."""
        defaults = loadDefaultConfig()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        writeUserConfig(defaults)
        result = loadUserConfig()
        assert result == defaults
    def test_load_raises_if_missing(self, config_path):
        with pytest.raises(FileNotFoundError):
            loadUserConfig()
    def test_load_reads_correct_values(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        writeUserConfig({"global": {"verbose": True}})
        result = loadUserConfig()
        assert result["global"]["verbose"] is True

# -- Define internatl config check test
class TestInternalConfigCheck:
    def test_exists_true_when_file_present(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
        assert internalConfigCheck(config_path, exists=True) is True
    def test_exists_false_when_file_absent(self, config_path):
        assert internalConfigCheck(config_path, exists=True) is False
    def test_not_exists_true_when_file_absent(self, config_path):
        assert internalConfigCheck(config_path, exists=False) is True
    def test_not_exists_false_when_file_present(self, config_path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
        assert internalConfigCheck(config_path, exists=False) is False

# -- Define config initialisation test -
class TestConfigInit:
    def test_init_creates_config_file(self, config_path):
        config_init()
        assert config_path.exists()
    def test_init_writes_default_values(self, config_path):
        config_init()
        with config_path.open("rb") as f:
            written = tomllib.load(f)
        assert written == loadDefaultConfig()
    def test_init_does_not_overwrite_existing(self, config_path):
        """If the config file already exists, init must leave it unchanged."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_bytes(b"[global]\nverbose = true\n")
        config_init()
        with config_path.open("rb") as f:
            content = tomllib.load(f)
        assert content["global"]["verbose"] is True

# -- Define config verification test ---
class TestConfigVerify:
    def test_verify_passes_for_valid_config(self, config_path):
        config_init()
        # Should complete without raising SystemExit
        config_verify()
    def test_verify_exits_when_key_missing(self, config_path):
        """A config file missing a required key must cause a non-zero exit."""
        import typer
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Write an incomplete config — missing most keys
        config_path.write_bytes(b"[global]\nverbose = false\n")
        with pytest.raises((typer.Exit, SystemExit)):
            config_verify()