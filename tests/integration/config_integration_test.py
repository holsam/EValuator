# ====================
# Import external dependencies
# ====================
import pytest, tomllib
from pathlib import Path
from unittest.mock import patch

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
class TestPipelineCommandIntegration:
    '''Pipeline commands resolve config, autocreate if needed, and route outputs (patching internal processing so no MRC needed)'''
    def test_label_autocreates_config_on_first_run(self, tmp_path, seg_path):
        from evaluator.commands.label.label import label_components
        with patch('evaluator.commands.label.label.label_components'):
            label_components(seg_path, tmp_path)
        assert (tmp_path / 'evaluator' / 'config.toml').exists()
    
    def test_label_writes_to_correct_output_dir(self, tmp_path, seg_path):
        from evaluator.commands.label.label import label_components
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.label.label.label_components'):
            label_components(seg_path, tmp_path)
        assert (tmp_path / 'evaluator' / 'label').is_dir()

    def test_label_params_toml_written(self, tmp_path, seg_path):
        from evaluator.commands.label.label import label_components
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.label.label.label_components'):
            label_components(seg_path, tmp_path)
        assert (tmp_path / 'evaluator' / 'label' / 'params.toml').exists()

    def test_cli_override_reflected_in_params_toml(self, tmp_path, labelled_path):
        '''A --minimum-diameter override must appear in the written params.toml'''
        from evaluator.commands.analyse.analyse import analyse
        _write_config(tmp_path / 'evaluator' / 'config.toml')
        with patch('evaluator.commands.analyse.analyse.analyse'):
            analyse(labelled_path, tmp_path, minimum_diameter_nm=55.0)
        params = tomllib.loads(
            (tmp_path / 'evaluator' / 'analyse' / 'params.toml').read_text(encoding='utf-8')
        )
        assert params['minimum_diameter_nm'] == pytest.approx(55.0)

    def test_config_file_unchanged_after_cli_override(self, tmp_path, labelled_path):
        '''An override must not mutate config.toml on disk'''
        from evaluator.commands.analyse.analyse import analyse
        cfg = _write_config(tmp_path / 'evaluator' / 'config.toml')
        original_text = cfg.read_text(encoding='utf-8')
        with patch('evaluator.commands.analyse.analyse.analyse'):
            analyse(labelled_path, tmp_path, minimum_diameter_nm=55.0)
        assert cfg.read_text(encoding='utf-8') == original_text

    def test_explicit_output_flag_respected(self, tmp_path, seg_path):
        '''--output some/dir writes to some/dir/evaluator/label/'''
        from evaluator.commands.label.label import label_components
        project_dir = tmp_path / 'my_project'
        with patch('evaluator.commands.label.label.label_components'):
            label_components(seg_path, project_dir)
        assert (project_dir / 'evaluator' / 'config.toml').exists()
        assert (project_dir / 'evaluator' / 'label').is_dir()

    def test_reuses_existing_config_on_second_run(self, tmp_path, seg_path):
        '''A second run must not overwrite a manually edited config.toml'''
        from evaluator.commands.label.label import label_components
        # First run to create default
        with patch('evaluator.commands.label.label.label_components'):
            label_components(seg_path, tmp_path)
        cfg = tmp_path / 'evaluator' / 'config.toml'
        # Simulate a user edit
        text = cfg.read_text(encoding='utf-8')
        edited = text.replace('minimum_diameter_nm = 20.0', 'minimum_diameter_nm = 42.0')
        cfg.write_text(edited, encoding='utf-8')
        # Second run must not recreate default
        with patch('evaluator.commands.label.label.label_components'):
            label_components(seg_path, tmp_path)
        result = tomllib.loads(cfg.read_text(encoding='utf-8'))
        assert result['analyse']['minimum_diameter_nm'] == pytest.approx(42.0)

    def test_no_editor_opens_during_pipeline_run(self, tmp_path, seg_path):
        '''Pipeline commands must never open an editor regardless of context'''
        from evaluator.commands.label.label import label_components
        with patch('click.edit') as mock_edit:
            with patch('evaluator.commands.label.label.label_components'):
                label_components(seg_path, tmp_path)
        mock_edit.assert_not_called()