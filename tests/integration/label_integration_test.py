# -- Import external dependencies ------
import mrcfile, numpy as np, pytest
from pathlib import Path

# -- Import internal dependencies ------
from evaluator.commands.label.label import label_components
from evaluator.utils.mrc import readMRCFile

# -- Define constants ------
N_EVS = 4   # expected number of EVs

# -- Define label components output test
class TestLabelComponentsOutput:
    def test_output_file_created(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        outputs = list(out_dir.glob("*.mrc"))
        assert len(outputs) == 1, "Expected exactly one labelled MRC output"
    def test_output_directory_created(self, seg_path, tmp_path):
        expected = tmp_path / "evaluator" / "label"
        assert not expected.exists()
        label_components(seg_path, tmp_path)
        assert expected.is_dir()
    def test_output_filename_contains_stem(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        assert seg_path.stem in out_file.name
    def test_output_shape_matches_input(self, seg_path, tmp_path):
        input_data, _ = readMRCFile(seg_path)
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        out_data, _ = readMRCFile(out_file)
        assert out_data.shape == input_data.shape
    def test_output_voxel_size_preserved(self, seg_path, tmp_path):
        _, input_vox = readMRCFile(seg_path)
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        _, out_vox = readMRCFile(out_file)
        assert np.isclose(out_vox, input_vox, rtol=1e-3)

# -- Define labelling correctness test -
class TestLabelComponentsLabels:
    def test_output_has_more_than_two_unique_values(self, seg_path, tmp_path):
        """Background + N components → at least N+1 unique values."""
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert len(np.unique(data)) > 2
    def test_n_components_matches_generator(self, seg_path, tmp_path):
        """
        With seed=42 and N_EVS=4 the generator places exactly 4 non-overlapping
        spherical shells. All must be labelled as separate components.
        """
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert int(data.max()) == N_EVS
    def test_background_is_zero(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert 0 in np.unique(data)

# -- Define labelling name conflict handling test
class TestLabelComponentsNamingConflict:
    def test_second_run_appends_numeric_suffix(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        outputs = sorted(out_dir.glob("*.mrc"), reverse=True)
        assert len(outputs) == 2
        # The suffixed file must contain a dash-number pattern
        assert "-1" in outputs[1].name

# -- Define arc-coverage/size filter override test
class TestLabelComponentsFilterOverrides:
    def test_high_min_arc_coverage_excludes_all(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path, min_arc_coverage=1.01)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert int(data.max()) == 0
    def test_exclusion_tally_reports_size_floor_breakdown(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path, min_arc_coverage=1.01)
        out_dir = tmp_path / "evaluator" / "label"
        tally_file = next(out_dir.glob("*_exclusions.txt"))
        tally = tally_file.read_text()
        assert "too small to reach threshold" not in tally
    def test_tight_diameter_range_excludes_all(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path, minimum_diameter_nm=1e6, maximum_diameter_nm=1e6 + 1)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert int(data.max()) == 0
    def test_default_thresholds_retain_all_evs(self, seg_path, tmp_path):
        label_components(seg_path, tmp_path)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        assert int(data.max()) == N_EVS

# -- Define merging relabelling tests
class TestLabelComponentsMergeSurvivesToOutput:
    @pytest.fixture
    def split_shell_seg_path(self, tmp_path):
        # Create a hollow sphere and simulate missing wedge
        shape = (80, 80, 80)
        centre = np.array([40.0, 40.0, 40.0])
        r_outer, r_inner = 20, 12
        zz, yy, xx = np.indices(shape)
        dist = np.sqrt((zz - centre[0]) ** 2 + (yy - centre[1]) ** 2 + (xx - centre[2]) ** 2)
        shell = (dist >= r_inner) & (dist <= r_outer)
        # Remove the equatorial band to break 6-connectivity
        band = np.abs(zz - centre[0]) <= 4
        split = shell & ~band
        assert split.sum() > 0
        seg_path = tmp_path / "split_shell_segmentation.mrc"
        with mrcfile.new(str(seg_path), overwrite=True) as mrc:
            mrc.set_data(split.astype(np.float32))
            mrc.voxel_size = 5.36
        return seg_path
    def test_split_vesicle_written_as_single_label(self, split_shell_seg_path, tmp_path):
        label_components(split_shell_seg_path, tmp_path, min_arc_coverage=0.0, minimum_diameter_nm=0.0)
        out_dir = tmp_path / "evaluator" / "label"
        out_file = next(out_dir.glob("*.mrc"))
        data, _ = readMRCFile(out_file)
        from scipy import ndimage
        struc = ndimage.generate_binary_structure(3, 1)
        raw_data, _ = readMRCFile(split_shell_seg_path)
        _, n_raw_components = ndimage.label(raw_data.astype(bool), structure=struc)
        assert n_raw_components == 2, "test fixture must produce two disjoint pieces pre-merge"
        assert int(data.max()) == 1
        assert sorted(np.unique(data).tolist()) == [0, 1]
