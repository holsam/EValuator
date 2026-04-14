# -- Import external dependencies ------
import pytest
import numpy as np
from pathlib import Path

# -- Import internal dependencies ------
from evaluator.commands.label import label_components
from evaluator.utils.mrc import readMRCFile

# -- Define constants ------
N_EVS = 4   # expected number of EVs

# -- Define label components output test
class TestLabelComponentsOutput:
    def test_output_file_created(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        outputs = list(out_dir.glob("*.mrc"))
        assert len(outputs) == 1, "Expected exactly one labelled MRC output"
    def test_output_directory_created(self, seg_path, tmp_path):
        expected = tmp_path / "evaluator" / "results" / "label"
        assert not expected.exists()
        label_components(seg_path, tmp_path)
        assert expected.is_dir()
    def test_output_filename_contains_stem(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        assert seg_path.stem in out_file.name
    def test_output_shape_matches_input(self, seg_path, tmp_path):
        input_data, _ = readMRCFile(seg_path)
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        out_data, _ = readMRCFile(out_file)
        assert out_data.shape == input_data.shape
    def test_output_voxel_size_preserved(self, seg_path, tmp_path):
        _, input_vox = readMRCFile(seg_path)
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        _, out_vox = readMRCFile(out_file)
        assert np.isclose(out_vox, input_vox, rtol=1e-3)

# -- Define labelling correctness test -
class TestLabelComponentsLabels:
    def test_output_has_more_than_two_unique_values(self, seg_path, tmp_path):
        """Background + N components → at least N+1 unique values."""
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert len(np.unique(data)) > 2
    def test_n_components_matches_generator(self, seg_path, tmp_path):
        """
        With seed=42 and N_EVS=4 the generator places exactly 4 non-overlapping
        spherical shells. All must be labelled as separate components.
        """
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert int(data.max()) == N_EVS
    def test_background_is_zero(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert 0 in np.unique(data)

# -- Define labelling name conflict handling test
class TestLabelComponentsNamingConflict:
    def test_second_run_appends_numeric_suffix(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "results" / "label"
        outputs = sorted(out_dir.glob("*.mrc"), reverse=True)
        assert len(outputs) == 2
        # The suffixed file must contain a dash-number pattern
        assert "-1" in outputs[1].name