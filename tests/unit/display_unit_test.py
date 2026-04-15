
'''
Rendering functions (renderTiled, renderSingleSlice, renderOverlayMovie) are
excluded: they produce matplotlib figures and are covered by visual inspection
rather than automated assertions.
'''

# -- Import external dependencies ------
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# -- Import internal dependencies ------
from evaluator.utils.display import (
    assignLabelColours,
    getLabelCentroid2D,
    getValidLabelsFromCSV,
    normaliseArray,
)

# -- Define array normalisation test ---
class TestNormaliseArray:
    def test_output_in_unit_interval(self):
        arr = np.array([[0.0, 5.0, 10.0], [15.0, 20.0, 25.0]])
        normed = normaliseArray(arr)
        assert normed.min() >= 0.0
        assert normed.max() <= 1.0
    def test_constant_array_returns_zeros(self):
        arr = np.full((6, 6), 7.0)
        assert np.all(normaliseArray(arr) == 0.0)
    def test_output_range_for_random_array(self):
        rng = np.random.default_rng(0)
        arr = rng.standard_normal((30, 30))
        normed = normaliseArray(arr)
        assert 0.0 <= normed.min() and normed.max() <= 1.0
    def test_output_shape_preserved(self):
        arr = np.ones((5, 8))
        assert normaliseArray(arr).shape == (5, 8)
    def test_percentile_clipping_suppresses_outliers(self):
        """A single extreme outlier must not collapse the overall contrast."""
        arr = np.zeros((10, 10))
        arr[0, 0] = 1e6   # outlier
        arr[5, 5] = 1.0   # representative signal
        normed = normaliseArray(arr)
        # Most of the array should still have non-zero contrast
        assert normed[5, 5] > 0.0

# -- Define retrieving labels from CSV file test
class TestGetValidLabelsFromCSV:
    def _write_csv(self, tmp_path, records):
        p = tmp_path / "results.csv"
        pd.DataFrame(records).to_csv(p, index=False)
        return p
    def test_returns_correct_label_set(self, tmp_path):
        csv = self._write_csv(tmp_path, [
            {"tomogram": "tomo.mrc", "label": 1},
            {"tomogram": "tomo.mrc", "label": 3},
        ])
        labels = getValidLabelsFromCSV(csv, "tomo.mrc")
        assert labels == {1, 3}
    def test_filters_by_filename(self, tmp_path):
        csv = self._write_csv(tmp_path, [
            {"tomogram": "tomo_A.mrc", "label": 1},
            {"tomogram": "tomo_B.mrc", "label": 2},
        ])
        labels = getValidLabelsFromCSV(csv, "tomo_A.mrc")
        assert labels == {1}
        assert 2 not in labels
    def test_returns_none_when_no_match(self, tmp_path):
        csv = self._write_csv(tmp_path, [{"tomogram": "other.mrc", "label": 1}])
        assert getValidLabelsFromCSV(csv, "tomo.mrc") is None
    def test_returns_none_for_missing_columns(self, tmp_path):
        csv = self._write_csv(tmp_path, [{"wrong_col": 1}])
        assert getValidLabelsFromCSV(csv, "tomo.mrc") is None
    def test_returns_none_for_nonexistent_file(self):
        assert getValidLabelsFromCSV(Path("/no/such/file.csv"), "tomo.mrc") is None
    def test_labels_are_integers(self, tmp_path):
        csv = self._write_csv(tmp_path, [{"tomogram": "t.mrc", "label": 7}])
        labels = getValidLabelsFromCSV(csv, "t.mrc")
        assert all(isinstance(l, int) for l in labels)
    def test_multiple_rows_same_file(self, tmp_path):
        records = [{"tomogram": "t.mrc", "label": i} for i in range(1, 6)]
        csv = self._write_csv(tmp_path, records)
        labels = getValidLabelsFromCSV(csv, "t.mrc")
        assert labels == {1, 2, 3, 4, 5}

# -- Define label colour assignment test
class TestAssignLabelColours:
    def test_returns_one_colour_per_label(self):
        labels = {1, 3, 7, 9}
        colours = assignLabelColours(labels)
        assert len(colours) == len(labels)
    def test_keys_match_input_labels(self):
        labels = {2, 5, 11}
        colours = assignLabelColours(labels)
        assert set(colours.keys()) == labels
    def test_values_are_rgba_tuples(self):
        colours = assignLabelColours({1, 2, 3})
        for rgba in colours.values():
            assert len(rgba) == 4, f"Expected RGBA tuple, got length {len(rgba)}"
    def test_single_label(self):
        colours = assignLabelColours({42})
        assert 42 in colours
        assert len(colours[42]) == 4

# -- Define label centroid calculation test
class TestGetLabelCentroid2D:
    def test_returns_centroid_for_present_label(self):
        seg = np.zeros((10, 10), dtype=int)
        seg[3:6, 3:6] = 1   # 3×3 block centred at (4, 4)
        row, col = getLabelCentroid2D(seg, 1)
        assert row == 4
        assert col == 4
    def test_returns_none_for_absent_label(self):
        seg = np.zeros((10, 10), dtype=int)
        assert getLabelCentroid2D(seg, 99) is None
    def test_centroid_is_integer_tuple(self):
        seg = np.zeros((12, 12), dtype=int)
        seg[5, 5] = 2
        result = getLabelCentroid2D(seg, 2)
        assert result is not None
        row, col = result
        assert isinstance(row, int)
        assert isinstance(col, int)
    def test_single_voxel_centroid(self):
        seg = np.zeros((8, 8), dtype=int)
        seg[3, 6] = 1
        row, col = getLabelCentroid2D(seg, 1)
        assert row == 3 and col == 6