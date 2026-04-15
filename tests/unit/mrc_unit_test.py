# -- Import external dependencies ------
import mrcfile
import numpy as np
import pytest

# -- Import internal dependencies ------
from evaluator.utils.mrc import (
    labelComponents,
    readMRCFile,
    validateMRCFile,
    writeMRCFile,
)

# -- Define MRC validation test --------
class TestValidateMRCFile:
    def test_valid_mrc_returns_true(self, tmp_path):
        p = tmp_path / "valid.mrc"
        with mrcfile.new(str(p)) as mrc:
            mrc.set_data(np.zeros((4, 4, 4), dtype=np.float32))
        assert validateMRCFile(p) is True
    def test_text_file_returns_false(self, tmp_path):
        p = tmp_path / "text.txt"
        p.write_text("not an mrc file")
        assert validateMRCFile(p) is False
    def test_nonexistent_path_returns_false(self, tmp_path):
        assert validateMRCFile(tmp_path / "ghost.mrc") is False
    def test_empty_file_returns_false(self, tmp_path):
        p = tmp_path / "empty.mrc"
        p.write_bytes(b"")
        assert validateMRCFile(p) is False

# -- Define read MRC data test ---------
class TestReadMRCFile:
    def _write_simple(self, path, shape=(5, 6, 7), vox_a=5.36):
        data = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
        with mrcfile.new(str(path)) as mrc:
            mrc.set_data(data)
            if vox_a is not None:
                mrc.voxel_size = vox_a
        return data
    def test_shape_preserved(self, tmp_path):
        p = tmp_path / "t.mrc"
        self._write_simple(p, shape=(3, 5, 7))
        data, _ = readMRCFile(p)
        assert data.shape == (3, 5, 7)
    def test_voxel_size_converted_to_nm(self, tmp_path):
        p = tmp_path / "t.mrc"
        self._write_simple(p, vox_a=5.36)
        _, vox_nm = readMRCFile(p)
        assert np.isclose(vox_nm, 0.536, rtol=1e-3)
    def test_zero_voxel_size_returns_none(self, tmp_path):
        p = tmp_path / "novox.mrc"
        data = np.ones((4, 4, 4), dtype=np.float32)
        with mrcfile.new(str(p)) as mrc:
            mrc.set_data(data)
            # voxel_size defaults to 0.0
        _, vox_nm = readMRCFile(p)
        assert vox_nm is None
    def test_data_values_preserved(self, tmp_path):
        p = tmp_path / "t.mrc"
        original = self._write_simple(p, shape=(2, 3, 4))
        read, _ = readMRCFile(p)
        assert np.allclose(read, original)

# -- Define write data to MRC file test 
class TestWriteMRCFile:
    def test_roundtrip_data(self, tmp_path):
        p    = tmp_path / "rt.mrc"
        data = np.arange(27, dtype=np.float32).reshape(3, 3, 3)
        writeMRCFile(data, 0.536, p)
        read, _ = readMRCFile(p)
        assert np.allclose(read, data)
    def test_roundtrip_voxel_size(self, tmp_path):
        p = tmp_path / "rt.mrc"
        writeMRCFile(np.ones((4, 4, 4), dtype=np.float32), 0.536, p)
        _, vox_nm = readMRCFile(p)
        assert np.isclose(vox_nm, 0.536, rtol=1e-3)
    def test_none_voxel_size_reads_back_as_none(self, tmp_path):
        p = tmp_path / "novox.mrc"
        writeMRCFile(np.ones((4, 4, 4), dtype=np.float32), None, p)
        _, vox_nm = readMRCFile(p)
        assert vox_nm is None
    def test_creates_file(self, tmp_path):
        p = tmp_path / "new.mrc"
        assert not p.exists()
        writeMRCFile(np.zeros((2, 2, 2), dtype=np.float32), 1.0, p)
        assert p.exists()

# -- Define label components test ------
class TestLabelComponents:
    def test_two_isolated_voxels_give_two_components(self):
        vol = np.zeros((15, 15, 15), dtype=bool)
        vol[2, 2, 2] = True
        vol[12, 12, 12] = True
        _, n = labelComponents(vol)
        assert n == 2
    def test_diagonal_touch_is_separate_under_6_connectivity(self):
        """Two voxels sharing only a corner must be separate components."""
        vol = np.zeros((10, 10, 10), dtype=bool)
        vol[4, 4, 4] = True
        vol[5, 5, 5] = True   # diagonal, not face-adjacent
        _, n = labelComponents(vol)
        assert n == 2
    def test_face_adjacent_voxels_are_one_component(self):
        vol = np.zeros((10, 10, 10), dtype=bool)
        vol[5, 5, 5] = True
        vol[5, 5, 6] = True   # face-adjacent in X
        _, n = labelComponents(vol)
        assert n == 1
    def test_empty_volume_gives_zero_components(self):
        vol = np.zeros((8, 8, 8), dtype=bool)
        labelled, n = labelComponents(vol)
        assert n == 0
        assert np.all(labelled == 0)
    def test_labels_are_consecutive_integers_from_one(self):
        vol = np.zeros((20, 20, 20), dtype=bool)
        vol[2:4, 2:4, 2:4] = True
        vol[15:17, 15:17, 15:17] = True
        labelled, n = labelComponents(vol)
        unique_labels = set(np.unique(labelled)) - {0}
        assert unique_labels == set(range(1, n + 1))
    def test_hollow_sphere_is_single_component(self, hollow_sphere_vol):
        """
        A spherical shell with 8-voxel thickness must be a single connected
        component under 6-connectivity (no isolated poles).
        """
        _, n = labelComponents(hollow_sphere_vol)
        assert n == 1