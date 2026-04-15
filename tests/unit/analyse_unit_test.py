# -- Import external dependencies ------
import pytest
import numpy as np
import pandas as pd

# -- Import internal dependencies ------
from evaluator.commands.analyse import (
    checkEnclosed,
    computeSurfaceArea,
    deriveAxes,
    measureAxes,
    measureEccentricityAspectRatio,
    measureLumenVolume,
    measureMembraneVolumeDiameter,
    morphologicalClosure,
    saveResultsCSV,
    shellVolume,
)
from tests.unit.conftest import R_INNER, R_OUTER, VOX_NM_SMALL

# -- Define shell volume test ----------
class TestShellVolume:
    def test_solid_sphere_when_thickness_exceeds_radius(self):
        """Shell with r_inner=0 must equal the volume of a solid sphere."""
        diameter_nm = 20.0
        vox_nm = 1.0
        # membrane_thickness_vox >= r_outer forces r_inner to 0
        vol = shellVolume(diameter_nm, vox_nm, thickness_vox=10.0)
        r_outer  = diameter_nm / (2 * vox_nm)   # 10 vox
        expected = (4 / 3) * np.pi * r_outer ** 3
        assert np.isclose(vol, expected, rtol=1e-6)
    def test_thin_shell_value(self):
        """Check against manual analytic calculation for a representative shell."""
        diameter_nm  = 100.0
        vox_nm = 0.536
        thickness_vox = 10.0
        vol = shellVolume(diameter_nm, vox_nm, thickness_vox)
        r_outer = diameter_nm / (2 * vox_nm)
        r_inner = max(0.0, r_outer - thickness_vox)
        expected = (4 / 3) * np.pi * (r_outer ** 3 - r_inner ** 3)
        assert np.isclose(vol, expected, rtol=1e-6)
    def test_larger_diameter_gives_larger_volume(self):
        """shellVolume must be strictly increasing in diameter."""
        vol_large = shellVolume(500.0, 0.536, 13.0)
        vol_small = shellVolume(20.0, 0.536, 13.0)
        assert vol_small < vol_large
    def test_returns_positive(self):
        assert shellVolume(50.0, 0.536, 10.0) > 0

# -- Define morphological closure test -
class TestMorphologicalClosure:
    def test_fills_single_missing_voxel(self, hollow_sphere_vol):
        """A single-voxel gap in the shell surface must be bridged by closing."""
        punctured = hollow_sphere_vol.copy()
        # Remove one surface voxel on the equatorial plane
        punctured[40, 40, 20] = False
        closed = morphologicalClosure(punctured)
        assert closed[40, 40, 20], "Gap voxel was not restored by morphological closing"
    def test_all_original_voxels_preserved(self, hollow_sphere_vol):
        """Closing must not remove any pre-existing True voxels."""
        closed = morphologicalClosure(hollow_sphere_vol)
        assert np.all(closed[hollow_sphere_vol]), (
            "morphologicalClosure removed voxels that were present in the original mask"
        )
    def test_returns_bool_array(self, hollow_sphere_vol):
        closed = morphologicalClosure(hollow_sphere_vol)
        assert closed.dtype == bool or closed.dtype == np.bool_
    def test_same_shape(self, hollow_sphere_vol):
        closed = morphologicalClosure(hollow_sphere_vol)
        assert closed.shape == hollow_sphere_vol.shape

# -- Define check enclosed test --------
class TestCheckEnclosed:
    def test_hollow_sphere_is_enclosed(self, hollow_sphere_vol):
        is_enc, fill_ratio = checkEnclosed(hollow_sphere_vol, threshold=0.05)
        assert is_enc is True, "A complete hollow sphere must be classified as enclosed"
        assert fill_ratio > 0.05
    def test_flat_plane_is_not_enclosed(self):
        """A flat slab has no interior and must not be classified as enclosed."""
        vol = np.zeros((40, 40, 40), dtype=bool)
        vol[20:22, :, :] = True
        is_enc, _ = checkEnclosed(vol, threshold=0.05)
        assert is_enc is False
    def test_fill_ratio_bounded(self, hollow_sphere_vol):
        _, fill_ratio = checkEnclosed(hollow_sphere_vol, threshold=0.05)
        assert 0.0 < fill_ratio <= 1.0
    def test_fill_ratio_reflects_interior_fraction(self, hollow_sphere_vol):
        """
        For sphere with r_outer=20, r_inner=12:
            interior ≈ (4/3)π x 12^3 ≈ 7238 vox
            total ≈ (4/3)π x 20^3 ≈ 33510 vox
            fill_ratio ≈ 7238/33510 ≈ 0.216
        """
        _, fill_ratio = checkEnclosed(hollow_sphere_vol, threshold=0.05)
        expected = ((4 / 3) * np.pi * R_INNER ** 3) / ((4 / 3) * np.pi * R_OUTER ** 3)
        assert np.isclose(fill_ratio, expected, atol=0.03), (
            f"fill_ratio {fill_ratio:.4f} deviates too far from expected {expected:.4f}"
        )
    def test_high_threshold_flips_classification(self, hollow_sphere_vol):
        """Setting threshold just above the actual fill_ratio must flip is_enclosed."""
        _, fill_ratio = checkEnclosed(hollow_sphere_vol, threshold=0.05)
        is_enc_strict, _ = checkEnclosed(hollow_sphere_vol, threshold=fill_ratio + 0.01)
        assert is_enc_strict is False
    def test_empty_volume_not_enclosed(self):
        vol = np.zeros((20, 20, 20), dtype=bool)
        is_enc, fill_ratio = checkEnclosed(vol, threshold=0.05)
        assert is_enc is False
        assert fill_ratio == 0.0

# -- Define membrane volume & diameter test
class TestMeasureMembraneVolumeDiameter:
    def test_volume_equals_voxel_count_at_scale_one(self, hollow_sphere_vol, sphere_regionprops):
        vol_nm3, _ = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0)
        assert np.isclose(vol_nm3, float(hollow_sphere_vol.sum()), rtol=1e-9)
    def test_volume_scales_cubically(self, sphere_regionprops):
        vol_1, _ = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0)
        vol_nm, _ = measureMembraneVolumeDiameter(sphere_regionprops, scale=VOX_NM_SMALL)
        assert np.isclose(vol_nm, vol_1 * (VOX_NM_SMALL ** 3), rtol=1e-9)
    def test_diameter_is_positive(self, sphere_regionprops):
        _, diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=VOX_NM_SMALL)
        assert diam > 0
    def test_diameter_plausible_for_sphere(self, sphere_regionprops):
        """
        equiv_diameter is derived from shell volume, not geometric diameter.
        For r_outer=20, r_inner=12 at scale=1: shell_vol ≈ 26,266 vox.
        equiv_diam = (6 x 26266 / π)^(1/3) ≈ 36.9 vox.
        """
        _, diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0)
        assert 30.0 < diam < 45.0, f"Unexpected equiv_diameter {diam:.2f} vox"

# -- Define lumen measurement test -----
class TestMeasureLumenVolume:
    def test_enclosed_sphere_has_positive_lumen(self, hollow_sphere_vol):
        lumen = measureLumenVolume(hollow_sphere_vol, scale=1.0)
        assert lumen > 0
    def test_lumen_close_to_analytic_interior(self, hollow_sphere_vol):
        """Discrete lumen ≈ (4/3)π x r_inner^3 within 5%."""
        expected = (4 / 3) * np.pi * R_INNER ** 3
        lumen = measureLumenVolume(hollow_sphere_vol, scale=1.0)
        assert np.isclose(lumen, expected, rtol=0.05)
    def test_flat_plane_has_zero_lumen(self):
        vol = np.zeros((40, 40, 40), dtype=bool)
        vol[20:22, :, :] = True
        assert measureLumenVolume(vol, scale=1.0) == 0.0
    def test_lumen_scales_cubically(self, hollow_sphere_vol):
        lumen_vox = measureLumenVolume(hollow_sphere_vol, scale=1.0)
        lumen_nm3 = measureLumenVolume(hollow_sphere_vol, scale=VOX_NM_SMALL)
        assert np.isclose(lumen_nm3, lumen_vox * (VOX_NM_SMALL ** 3), rtol=1e-9)

# -- Define surface area measurement test
class TestComputeSurfaceArea:
    def test_returns_positive(self, hollow_sphere_vol):
        sa = computeSurfaceArea(hollow_sphere_vol, voxel_size_nm=1.0)
        assert sa > 0
    def test_not_nan(self, hollow_sphere_vol):
        sa = computeSurfaceArea(hollow_sphere_vol, voxel_size_nm=1.0)
        assert not np.isnan(sa)
    def test_magnitude_close_to_analytic(self, hollow_sphere_vol):
        """
        Marching cubes finds both inner and outer isosurfaces of the shell.
        Total ≈ 4π(r_outer^2 + r_inner^2) ≈ 4π(400 + 144) ≈ 6837 vox^2.
        Allow 15% tolerance for discretisation.
        """
        expected = 4 * np.pi * (R_OUTER ** 2 + R_INNER ** 2)
        sa = computeSurfaceArea(hollow_sphere_vol, voxel_size_nm=1.0)
        assert np.isclose(sa, expected, rtol=0.15), (
            f"Surface area {sa:.1f} vox^2 deviates >15% from analytic {expected:.1f} vox^2"
        )
    def test_scales_with_voxel_size_squared(self, hollow_sphere_vol):
        sa_vox = computeSurfaceArea(hollow_sphere_vol, voxel_size_nm=1.0)
        sa_nm = computeSurfaceArea(hollow_sphere_vol, voxel_size_nm=VOX_NM_SMALL)
        assert np.isclose(sa_nm, sa_vox * (VOX_NM_SMALL ** 2), rtol=1e-5)
    def test_none_voxel_size_returns_voxel_units(self, hollow_sphere_vol):
        sa = computeSurfaceArea(hollow_sphere_vol, voxel_size_nm=None)
        assert sa > 0 and not np.isnan(sa)
    def test_empty_volume_returns_nan(self):
        vol = np.zeros((10, 10, 10), dtype=bool)
        sa = computeSurfaceArea(vol, voxel_size_nm=1.0)
        assert np.isnan(sa)

# -- Define axis derivation test -------
class TestDeriveAxes:
    def test_identity_tensor_returns_ones(self):
        """Identity inertia tensor → all eigenvalues=1 → inv_sqrt=[1,1,1]."""
        result = deriveAxes(np.eye(3))
        assert np.allclose(result, [1.0, 1.0, 1.0])
    def test_diagonal_tensor_known_values(self):
        """
        Diagonal tensor [1, 4, 9] → eigvalsh ascending [1,4,9]
        → inv_sqrt = [1/1, 1/2, 1/3].
        """
        tensor = np.diag([1.0, 4.0, 9.0])
        result = deriveAxes(tensor)
        assert np.allclose(result, [1.0, 0.5, 1.0 / 3.0], rtol=1e-6)
    def test_zero_eigenvalue_gives_zero_not_inf(self):
        """A zero eigenvalue must produce 0.0 in inv_sqrt, not NaN or inf."""
        tensor = np.diag([0.0, 1.0, 4.0])
        result = deriveAxes(tensor)
        assert result[0] == 0.0
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))
    def test_output_is_descending(self):
        """inv_sqrt must be in descending order (largest first)."""
        tensor = np.diag([1.0, 4.0, 9.0])
        result = deriveAxes(tensor)
        assert result[0] >= result[1] >= result[2]
    def test_symmetric_tensor_gives_equal_axes(self):
        """An isotropic (spherical) inertia tensor must give equal inv_sqrt values."""
        tensor = 5.0 * np.eye(3)
        result = deriveAxes(tensor)
        assert np.allclose(result[0], result[1]) and np.allclose(result[1], result[2])

# -- Define axes measurements test -----
class TestMeasureAxes:
    def test_sphere_major_approx_equals_minor(self, sphere_regionprops):
        """A spherical shell must give major ≈ minor axes (within 10%)."""
        _, equiv_diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0)
        major, minor = measureAxes(sphere_regionprops, equiv_diam)
        assert np.isclose(major, minor, rtol=0.10), (
            f"Sphere major ({major:.2f}) and minor ({minor:.2f}) axes differ by >10%"
        )
    def test_major_geq_minor(self, sphere_regionprops):
        _, equiv_diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0)
        major, minor = measureAxes(sphere_regionprops, equiv_diam)
        assert major >= minor
    def test_both_axes_positive(self, sphere_regionprops):
        _, equiv_diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0)
        major, minor = measureAxes(sphere_regionprops, equiv_diam)
        assert major > 0 and minor > 0

# -- Define eccentricity & aspect ratio test
class TestMeasureEccentricityAspectRatio:
    def test_perfect_sphere_eccentricity_zero(self):
        ecc, _ = measureEccentricityAspectRatio(10.0, 10.0)
        assert np.isclose(ecc, 0.0)
    def test_perfect_sphere_aspect_ratio_one(self):
        _, ar = measureEccentricityAspectRatio(10.0, 10.0)
        assert np.isclose(ar, 1.0)
    def test_elongated_eccentricity_between_zero_and_one(self):
        ecc, _ = measureEccentricityAspectRatio(20.0, 10.0)
        assert 0.0 < ecc < 1.0
    def test_elongated_aspect_ratio_greater_than_one(self):
        _, ar = measureEccentricityAspectRatio(20.0, 10.0)
        assert ar > 1.0
    def test_aspect_ratio_exact_value(self):
        _, ar = measureEccentricityAspectRatio(30.0, 10.0)
        assert np.isclose(ar, 3.0)
    def test_zero_minor_axis_gives_nan_aspect_ratio(self):
        _, ar = measureEccentricityAspectRatio(10.0, 0.0)
        assert np.isnan(ar)
    def test_zero_major_axis_gives_nan_eccentricity(self):
        ecc, _ = measureEccentricityAspectRatio(0.0, 10.0)
        assert np.isnan(ecc)

# -- Define results saving test --------
class TestSaveResultsCSV:
    def test_file_created(self, tmp_path):
        records = [{"tomogram": "t.mrc", "label": 1, "equiv_diameter_nm": 50.0}]
        out = tmp_path / "results.csv"
        saveResultsCSV(records, out)
        assert out.exists()
    def test_row_count_matches(self, tmp_path):
        records = [
            {"tomogram": "t.mrc", "label": 1, "val": 10.0},
            {"tomogram": "t.mrc", "label": 2, "val": 20.0},
        ]
        out = tmp_path / "results.csv"
        saveResultsCSV(records, out)
        df = pd.read_csv(out)
        assert len(df) == 2
    def test_columns_match_records(self, tmp_path):
        records = [{"tomogram": "t.mrc", "label": 1, "equiv_diameter_nm": 99.0}]
        out = tmp_path / "results.csv"
        df = saveResultsCSV(records, out)
        assert "tomogram" in df.columns
        assert "label" in df.columns
        assert "equiv_diameter_nm" in df.columns
    def test_returns_dataframe(self, tmp_path):
        records = [{"a": 1}]
        out = tmp_path / "r.csv"
        result = saveResultsCSV(records, out)
        assert isinstance(result, pd.DataFrame)