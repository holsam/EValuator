'''
Unit tests for EValuator configuration management.
'''
# ====================
# Import external dependencies
# ====================
import pytest, tomlkit, tomllib
from click.testing import CliRunner
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import MagicMock, patch

# ====================
# Import internal config functions
# ====================
from evaluator.utils.config import (
    Config,
    ConfigError,
    ConfigNotFoundError,
    create_default_config,
    AnalyseConfig,
    load_config,
    read_config,
    resolve_config,
    ResolvedConfig,
    write_params,
)
from evaluator.commands.config.utils.edit import edit_config
from evaluator.commands.config.cli import evaluatorConfig

# ====================
# Define helper functions
# ====================
def _config_toml() -> str:
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
maximum_diameter_nm = 500.0
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

def _write_config(path: Path, content: str | None = None) -> Path:
    '''Write content (or the default config TOML) to path, creating parents'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or _config_toml(), encoding='utf-8')
    return path

# ====================
# Define tests
# ====================
class TestSchema:
    '''The Pydantic Config model and the packaged default are in lockstep'''
    def test_packaged_default_validates(self):
        '''The packaged config.toml must validate against Config'''
        from importlib.resources import files
        text = (files('evaluator') / 'config.toml').read_text(
            encoding='utf-8'
        )
        data = tomllib.loads(text)
        # Should not raise
        Config.model_validate(data)
    
    def test_all_schema_sections_in_default(self):
        '''Every top-level section in Config has a matching table in the default file'''
        from importlib.resources import files
        text = (files('evaluator') / 'config.toml').read_text(
            encoding='utf-8'
        )
        data = tomllib.loads(text)
        schema_fields = set(Config.model_fields.keys())
        assert schema_fields.issubset(set(data.keys())), (
            f'Sections present in schema but missing from default: '
            f'{schema_fields - set(data.keys())}'
        )

    def test_unknown_key_raises(self):
        '''extra='forbid' means an unrecognised key in any section raises'''
        data = tomllib.loads(_config_toml())
        data['label']['unknown_key'] = 99
        with pytest.raises(ValidationError):
            Config.model_validate(data)

    def test_missing_required_field_raises(self):
        '''Omitting a required field raises ValidationError'''
        data = tomllib.loads(_config_toml())
        del data['analyse']['minimum_diameter_nm']
        with pytest.raises(ValidationError):
            Config.model_validate(data)

    def test_label_config_type_coercion(self):
        '''Pydantic coerces an int fill_threshold to float without error'''
        data = tomllib.loads(_config_toml())
        data['analyse']['fill_threshold'] = 1  # int supplied, float expected
        config = Config.model_validate(data)
        assert isinstance(config.analyse.fill_threshold, float)


class TestResolveConfig:
    '''resolve_config path handling tests'''
    def test_returns_resolved_config_dataclass(self, tmp_path):
        result = resolve_config(tmp_path)
        assert isinstance(result, ResolvedConfig)

    def test_tilde_expansion(self, tmp_path, monkeypatch):
        '''Paths starting with ~ are expanded correctly'''
        monkeypatch.setenv('HOME', str(tmp_path))
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        result = resolve_config(Path('~/'))
        assert result.existed is True

    def test_resolver_does_not_mutate_filesystem(self, tmp_path):
        '''Every non-existed path leaves the filesystem unchanged'''
        before = set(tmp_path.rglob('*'))
        resolve_config(tmp_path / 'new_project')
        after = set(tmp_path.rglob('*'))
        assert before == after


class TestResolveConfigPrecedence:
    '''resolve_config follows precedence'''
    # Rule 1: existing file
    def test_rule1_existing_file(self, tmp_path):
        cfg = _write_config(tmp_path / 'myconfig.toml')
        result = resolve_config(cfg)
        assert result.config_path == cfg
        assert result.evaluator_dir == tmp_path
        assert result.existed is True

    def test_rule1_file_with_arbitrary_name(self, tmp_path):
        cfg = _write_config(tmp_path / 'special.toml')
        result = resolve_config(cfg)
        assert result.config_path == cfg
        assert result.existed is True

    # Rule 2: evaluator directory
    def test_rule2_directory_contains_config_toml_directly(self, tmp_path):
        cfg = _write_config(tmp_path / 'config.toml')
        result = resolve_config(tmp_path)
        assert result.config_path == cfg
        assert result.evaluator_dir == tmp_path
        assert result.existed is True

    def test_rule2_beats_rule3_when_both_present(self, tmp_path):
        '''A directory holding both config.toml and evaluator/config.toml uses rule 2'''
        _write_config(tmp_path / 'config.toml')
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        result = resolve_config(tmp_path)
        assert result.config_path == tmp_path / 'config.toml'

    # Rule 3: directory containing evaluator/config.toml
    def test_rule3_directory_contains_evaluator_subdir(self, tmp_path):
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        result = resolve_config(tmp_path)
        assert result.config_path == cfg
        assert result.evaluator_dir == tmp_path / 'evaluator'
        assert result.existed is True

    # Rule 4: non-existent .toml path
    def test_rule4_nonexistent_toml_path(self, tmp_path):
        toml_path = tmp_path / 'nonexistent.toml'
        result = resolve_config(toml_path)
        assert result.config_path == toml_path
        assert result.evaluator_dir == tmp_path
        assert result.existed is False
        assert not toml_path.exists()

    # Rule 5: non-existent non-toml path
    def test_rule5_nonexistent_directory_path(self, tmp_path):
        ghost = tmp_path / 'ghost_dir'
        result = resolve_config(ghost)
        assert result.config_path == ghost / 'evaluator' / 'config.toml'
        assert result.existed is False
        assert not result.config_path.exists()


class TestCreateDefaultConfig:
    '''create_default_config copies the packaged default verbatim'''
    def test_creates_file_and_parents(self, tmp_path):
        target = tmp_path / 'project' / 'evaluator' / 'config.toml'
        create_default_config(target)
        assert target.exists()

    def test_content_matches_packaged_default(self, tmp_path):
        from importlib.resources import files
        target = tmp_path / 'evaluator' / 'config.toml'
        create_default_config(target)
        expected = (files('evaluator') / 'config.toml').read_text(
            encoding='utf-8'
        )
        assert target.read_text(encoding='utf-8') == expected

    def test_idempotent_overwrite(self, tmp_path):
        '''Calling create twice overwrites silently without raising'''
        target = tmp_path / 'evaluator' / 'config.toml'
        create_default_config(target)
        create_default_config(target)
        assert target.exists()

    def test_comments_preserved(self, tmp_path):
        '''The created file contains at least one comment line'''
        target = tmp_path / 'evaluator' / 'config.toml'
        create_default_config(target)
        lines = target.read_text(encoding='utf-8').splitlines()
        assert any(line.strip().startswith('#') for line in lines), ('Written config.toml contains no comment lines')


class TestReadConfig:
    '''read_config validates and returns a Config, or raises ConfigError'''
    def test_valid_file_returns_config(self, tmp_path):
        cfg = _write_config(tmp_path / 'config.toml')
        result = read_config(cfg)
        assert isinstance(result, Config)

    def test_invalid_toml_raises_config_error(self, tmp_path):
        cfg = tmp_path / 'config.toml'
        cfg.write_text('[[not valid toml', encoding='utf-8')
        with pytest.raises(ConfigError, match='not valid TOML'):
            read_config(cfg)

    def test_schema_invalid_content_raises_config_error(self, tmp_path):
        '''A valid TOML file that fails schema validation raises ConfigError'''
        data = tomllib.loads(_config_toml())
        data['label']['minimum_diameter_nm'] = 'not_a_number'
        bad_toml = tomlkit.dumps(data)
        cfg = tmp_path / 'config.toml'
        cfg.write_text(bad_toml, encoding='utf-8')
        with pytest.raises(ConfigError, match='failed validation'):
            read_config(cfg)

    def test_unknown_key_raises_config_error(self, tmp_path):
        content = _config_toml() + '\n[label]\nextra_key = true\n'
        cfg = tmp_path / 'config.toml'
        cfg.write_text(content, encoding='utf-8')
        with pytest.raises(ConfigError):
            read_config(cfg)

    def test_raises_config_error_not_bare_pydantic(self, tmp_path):
        '''The caller should see a ConfigError not a raw ValidationError'''
        data = tomllib.loads(_config_toml())
        data['label']['minimum_diameter_nm'] = 'bad'
        cfg = tmp_path / 'config.toml'
        cfg.write_text(tomlkit.dumps(data), encoding='utf-8')
        with pytest.raises(ConfigError):
            read_config(cfg)
        # Confirm it is not the raw Pydantic type leaking through
        try:
            read_config(cfg)
        except ConfigError:
            pass
        except ValidationError:
            pytest.fail('read_config leaked a raw ValidationError')


class TestLoadConfig:
    '''Test the load_config entry point used by every pipeline command'''
    def test_autocreates_when_absent(self, tmp_path):
        config, evaluator_dir = load_config(tmp_path)
        assert isinstance(config, Config)
        assert (evaluator_dir / 'config.toml').exists()

    def test_returns_evaluator_dir(self, tmp_path):
        _, evaluator_dir = load_config(tmp_path)
        assert evaluator_dir == tmp_path / 'evaluator'

    def test_reuses_existing_config(self, tmp_path):
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        config, _ = load_config(tmp_path)
        assert isinstance(config, Config)

    def test_autocreate_false_raises_when_absent(self, tmp_path):
        with pytest.raises(ConfigNotFoundError):
            load_config(tmp_path, autocreate=False)

    def test_autocreate_false_succeeds_when_present(self, tmp_path):
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        config, _ = load_config(tmp_path, autocreate=False)
        assert isinstance(config, Config)

    def test_autocreated_file_is_valid(self, tmp_path):
        '''The autocreated file validates on a second load call'''
        load_config(tmp_path)
        config, _ = load_config(tmp_path, autocreate=False)
        assert isinstance(config, Config)

    def test_no_editor_opens_on_autocreate(self, tmp_path):
        '''Autocreation during a pipeline run is silent'''
        with patch('click.edit') as mock_edit:
            load_config(tmp_path)
        mock_edit.assert_not_called()


class TestWriteParams:
    '''Test write_params serialisation'''
    def _analyse_params(self) -> AnalyseConfig:
        return AnalyseConfig(
            minimum_diameter_nm=30.0,
            maximum_diameter_nm=300.0,
            fill_threshold=0.7,
            membrane_thickness_nm=7,
        )

    def test_creates_params_toml(self, tmp_path):
        params = self._analyse_params()
        out = write_params(params, tmp_path)
        assert out == tmp_path / 'params.toml'
        assert out.exists()

    def test_custom_filename(self, tmp_path):
        params = self._analyse_params()
        out = write_params(params, tmp_path, filename='label_params.toml')
        assert out.name == 'label_params.toml'

    def test_output_is_valid_toml(self, tmp_path):
        params = self._analyse_params()
        write_params(params, tmp_path)
        text = (tmp_path / 'params.toml').read_text(encoding='utf-8')
        parsed = tomllib.loads(text)
        assert isinstance(parsed, dict)

    def test_values_match_params(self, tmp_path):
        params = self._analyse_params()
        write_params(params, tmp_path)
        text = (tmp_path / 'params.toml').read_text(encoding='utf-8')
        parsed = tomllib.loads(text)
        assert parsed['minimum_diameter_nm'] == pytest.approx(30.0)
        assert parsed['maximum_diameter_nm'] == pytest.approx(300.0)
        assert parsed['fill_threshold'] == pytest.approx(0.7)

    def test_cli_override_is_captured(self, tmp_path):
        '''An override applied via model_copy shows up in the written file'''
        params = self._analyse_params()
        params = params.model_copy(update={'minimum_diameter_nm': 50.0})
        write_params(params, tmp_path)
        text = (tmp_path / 'params.toml').read_text(encoding='utf-8')
        parsed = tomllib.loads(text)
        assert parsed['minimum_diameter_nm'] == pytest.approx(50.0)

    def test_creates_output_dir_if_absent(self, tmp_path):
        out_dir = tmp_path / 'evaluator' / 'label'
        assert not out_dir.exists()
        write_params(self._analyse_params(), out_dir)
        assert out_dir.exists()

    def test_overwrites_on_second_call(self, tmp_path):
        '''A second run overwrites the previous params.toml cleanly'''
        write_params(self._analyse_params(), tmp_path)
        params2 = self._analyse_params().model_copy(update={'minimum_diameter_nm': 99.0})
        write_params(params2, tmp_path)
        text = (tmp_path / 'params.toml').read_text(encoding='utf-8')
        parsed = tomllib.loads(text)
        assert parsed['minimum_diameter_nm'] == pytest.approx(99.0)


class TestEditConfigEditor:
    '''Test edit_config with interactive=False opens $EDITOR via click.edit'''
    def test_calls_click_edit_with_file_path(self, tmp_path):
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.config.utils.edit.click.edit') as mock_edit:
            edit_config(cfg, stepwise=False)
        mock_edit.assert_called_once_with(filename=str(cfg))

    def test_warns_but_does_not_raise_on_invalid_result(self, tmp_path, capsys):
        '''If the editor produces invalid TOML, a warning is printed but no exception raised'''
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        def corrupt_then_open(filename):
            Path(filename).write_text('[[broken', encoding='utf-8')
        with patch('evaluator.commands.config.utils.edit.click.edit', side_effect=corrupt_then_open):
            edit_config(cfg, stepwise=False)  # must not raise
        captured = capsys.readouterr()
        assert 'Warning' in captured.err or 'warning' in captured.err.lower()

    def test_no_warning_on_valid_result(self, tmp_path, capsys):
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.config.utils.edit.click.edit'):
            edit_config(cfg, stepwise=False)
        captured = capsys.readouterr()
        assert captured.err == ''

class TestEditConfigStepwise:
    '''Test edit_config with stepwise=True prompts for each scalar value'''
    def test_unchanged_values_preserve_comments(self, tmp_path):
        '''Accepting all defaults via stepwise mode leaves comments intact.'''
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        original = cfg.read_text(encoding='utf-8')
        # typer.prompt returns the default when the user presses Enter
        with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=lambda k, default, **_: default):
            edit_config(cfg, stepwise=True)
        result = cfg.read_text(encoding='utf-8')
        assert any(line.strip().startswith('#') for line in result.splitlines()), 'Comments were stripped during interactive editing'

    def test_changed_scalar_is_written(self, tmp_path):
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        def prompt_side_effect(key, default, **kwargs):
            if 'minimum_diameter_nm' in key:
                return 99.0
            return default
        with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=prompt_side_effect):
            edit_config(cfg, stepwise=True)
        text = cfg.read_text(encoding='utf-8')
        parsed = tomllib.loads(text)
        assert parsed['analyse']['minimum_diameter_nm'] == pytest.approx(99.0)

    def test_other_values_unchanged_when_one_edited(self, tmp_path):
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        original = tomllib.loads(cfg.read_text(encoding='utf-8'))
        def prompt_side_effect(key, default, **kwargs):
            if 'minimum_diameter_nm' in key:
                return 99.0
            return default
        with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=prompt_side_effect):
            edit_config(cfg, stepwise=True)
        result = tomllib.loads(cfg.read_text(encoding='utf-8'))
        assert result['analyse']['maximum_diameter_nm'] == pytest.approx(original['analyse']['maximum_diameter_nm'])

    def test_invalid_value_aborts_without_writing(self, tmp_path):
        '''A schema-invalid response must leave the original file unchanged'''
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        original_text = cfg.read_text(encoding='utf-8')
        def bad_prompt(key, default, **kwargs):
            if 'minimum_diameter_nm' in key:
                return 'not_a_number'
            return default
        with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=bad_prompt):
            with pytest.raises(Exception):
                edit_config(cfg, stepwise=True)
        assert cfg.read_text(encoding='utf-8') == original_text

    def test_no_candidate_file_left_on_abort(self, tmp_path):
        '''The .toml.candidate temporary file is cleaned up on validation failure'''
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        candidate = cfg.with_suffix('.toml.candidate')
        def bad_prompt(key, default, **kwargs):
            if 'minimum_diameter_nm' in key:
                return 'bad'
            return default
        with patch('evaluator.commands.config.utils.edit.click.prompt', side_effect=bad_prompt):
            with pytest.raises(Exception):
                edit_config(cfg, stepwise=True)
        assert not candidate.exists()
