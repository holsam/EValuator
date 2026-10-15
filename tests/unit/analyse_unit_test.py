# -- Import external dependencies ------
import pytest
import numpy as np
import pandas as pd

# -- Import internal dependencies ------
from evaluator.commands.analyse.utils.filtering import checkEnclosed, morphologicalDilation
from evaluator.commands.analyse.utils.geometry import arcCoverage, deriveAxes, measureAxes, shellVolume, sphereFitResidual
from evaluator.commands.analyse.utils.io import saveResultsCSV
from evaluator.commands.analyse.utils.measurement import classifyVesicle, computeSurfaceArea, measureEccentricityAspectRatio, measureLumenVolume, measureMembraneVolumeDiameter, touchesZBoundary
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

# -- Define morphological dilation test
class TestMorphologicalDilation:
    def test_fills_single_missing_voxel(self, hollow_sphere_vol):
        """A single-voxel gap in the shell surface must be bridged by dilating"""
        punctured = hollow_sphere_vol.copy()
        # Remove one surface voxel on the equatorial plane
        punctured[40, 40, 20] = False
        closed = morphologicalDilation(punctured)
        assert closed[40, 40, 20], "Gap voxel was not restored by morphological dilation"
    def test_all_original_voxels_preserved(self, hollow_sphere_vol):
        '''
        Closing must not remove any pre-existing True voxels.
        '''
        closed = morphologicalDilation(hollow_sphere_vol)
        assert np.all(closed[hollow_sphere_vol]), "morphologicalDilation removed voxels that were present in the original mask"
    def test_returns_bool_array(self, hollow_sphere_vol):
        closed = morphologicalDilation(hollow_sphere_vol)
        assert closed.dtype == bool or closed.dtype == np.bool_
    def test_same_shape(self, hollow_sphere_vol):
        closed = morphologicalDilation(hollow_sphere_vol)
        assert closed.shape == hollow_sphere_vol.shape
    def test_dilation_not_clipped_at_box_face(self):
        '''
        Components touching mask boundary should be dilated outward instead of being clipped at the box face.
        '''
        vol = np.zeros((10, 10, 10), dtype=bool)
        vol[0, 5, 5] = True
        dilated = morphologicalDilation(vol)
        assert dilated[2, 5, 5], "Inward dilation did not reach the expected extent"
    def test_symmetric_dilation_extent_matches_interior_point(self):
        '''
        The mask boundary should not asymmetrically clip results.
        '''
        boundary_vol = np.zeros((10, 10, 10), dtype=bool)
        boundary_vol[0, 5, 5] = True
        interior_vol = np.zeros((10, 10, 10), dtype=bool)
        interior_vol[5, 5, 5] = True
        dilated_boundary = morphologicalDilation(boundary_vol)
        dilated_interior = morphologicalDilation(interior_vol)
        # count of dilated voxels on the non-clipped (y, x) plane through the seed voxel must match
        assert dilated_boundary[0, :, :].sum() == dilated_interior[5, :, :].sum()

# -- Define touches-z-boundary test --------
class TestTouchesZBoundary:
    def test_component_away_from_boundary_not_flagged(self, sphere_regionprops):
        assert touchesZBoundary(sphere_regionprops, volume_shape=(200, 200, 200)) is False
    def test_component_touching_last_z_slice_flagged(self, sphere_regionprops):
        # Shrink the volume's z-extent so sphere's max-z edge sits on the last slice
        assert touchesZBoundary(sphere_regionprops, volume_shape=(sphere_regionprops.bbox[3], 200, 200)) is True

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
        """Setting threshold just above the actual fill_ratio must flip is_enclosed"""
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
    def test_diameter_matches_true_outer_diameter_given_correct_thickness(self, sphere_regionprops):
        '''
        Synthetic shell has r_outer=20, r_inner=12, thickness=8 vox.
        Shell-volume-inversion formula should recover the true outer diameter (2*r_outer=40 vox).
        '''
        _, diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0, membrane_thickness_nm=8.0)
        assert 38.0 < diam < 42.0, f"Unexpected outer diameter {diam:.2f} vox (expected ~40 vox)"
    def test_solid_sphere_fallback_reproduces_old_biased_value_when_no_thickness(self, sphere_regionprops):
        vol_nm3, diam = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0, membrane_thickness_nm=0.0)
        assert np.isclose(diam, (6 * vol_nm3 / np.pi) ** (1 / 3))
    def test_thicker_assumed_membrane_gives_smaller_outer_diameter(self, sphere_regionprops):
        _, diam_thin = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0, membrane_thickness_nm=4.0)
        _, diam_thick = measureMembraneVolumeDiameter(sphere_regionprops, scale=1.0, membrane_thickness_nm=12.0)
        assert diam_thick < diam_thin

# -- Define lumen measurement test -----
class TestMeasureLumenVolume:
    def test_enclosed_sphere_has_positive_lumen(self, hollow_sphere_vol):
        lumen = measureLumenVolume(hollow_sphere_vol, scale=1.0)
        assert lumen > 0
    def test_lumen_close_to_analytic_interior(self, hollow_sphere_vol):
        """Discrete lumen ≈ (4/3)π x r_inner^3 within 5%"""
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
        Marching cubes finds both inner and outer isosurfaces of the shell
        Total ≈ 4π(r_outer^2 + r_inner^2) ≈ 4π(400 + 144) ≈ 6837 vox^2
        Allow 15% tolerance for discretisation
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
    def test_identity_tensor_returns_equal_axes(self):
        """Identity inertia tensor (i.e. isotropic) gives equal relative axis lengths"""
        result = deriveAxes(np.eye(3))
        assert np.allclose(result, result[0])
    def test_known_ellipsoid_semi_axes_recovered(self):
        """
        Solid ellipsoid with known semi-axes a=3,b=2,c=1 (mass=1) has principal moments I_a=(b^2+c^2)/5, I_b=(a^2+c^2)/5, I_c=(a^2+b^2)/5.
        deriveAxes must recover axis lengths proportional to the true (3, 2, 1) ratio.
        """
        a, b, c = 3.0, 2.0, 1.0
        i_a = (b ** 2 + c ** 2) / 5.0
        i_b = (a ** 2 + c ** 2) / 5.0
        i_c = (a ** 2 + b ** 2) / 5.0
        tensor = np.diag(sorted([i_a, i_b, i_c]))  # eigvalsh returns ascending order
        result = deriveAxes(tensor)
        result_ratio = result / result[-1]
        true_ratio = np.array([a, b, c]) / c
        assert np.allclose(result_ratio, true_ratio, rtol=1e-6), f"Recovered axis ratio {result_ratio} does not match true ratio {true_ratio}"
    def test_zero_eigenvalue_gives_zero_not_nan_or_inf(self):
        """A zero eigenvalue must produce 0.0, not NaN or inf."""
        tensor = np.diag([0.0, 4.0, 4.0])
        result = deriveAxes(tensor)
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))
    def test_output_is_descending(self):
        """Axis lengths must be in descending order (largest first)"""
        a, b, c = 3.0, 2.0, 1.0
        i_a, i_b, i_c = (b ** 2 + c ** 2) / 5.0, (a ** 2 + c ** 2) / 5.0, (a ** 2 + b ** 2) / 5.0
        tensor = np.diag(sorted([i_a, i_b, i_c]))
        result = deriveAxes(tensor)
        assert result[0] >= result[1] >= result[2]
    def test_symmetric_tensor_gives_equal_axes(self):
        """An isotropic (spherical) inertia tensor must give equal axis lengths"""
        tensor = 5.0 * np.eye(3)
        result = deriveAxes(tensor)
        assert np.allclose(result[0], result[1]) and np.allclose(result[1], result[2])
    def test_no_artificial_oblate_ceiling(self):
        """
        A strongly oblate ellipsoid (a=b=5, c=1) must give an axis ratio beyond inverse square root's ~1.414 ceiling.
        """
        a, b, c = 5.0, 5.0, 1.0
        i_a = (b ** 2 + c ** 2) / 5.0
        i_b = (a ** 2 + c ** 2) / 5.0
        i_c = (a ** 2 + b ** 2) / 5.0
        tensor = np.diag(sorted([i_a, i_b, i_c]))
        result = deriveAxes(tensor)
        assert (result[0] / result[-1]) > 2.0

# -- Define axes measurements test -----
class TestMeasureAxes:
    def test_sphere_major_approx_equals_minor(self, sphere_regionprops):
        """A spherical shell must give major ≈ minor axes (within 10%)"""
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
    def test_known_ellipsoid_axis_ratio_recovered(self):
        """
        Measurement of ellipsoid with semi-axes 12, 6, 3 vox recovers major/minor axis ratio close to 4.0.
        """
        from skimage import measure as skmeasure
        shape = (30, 30, 30)
        zz, yy, xx = np.indices(shape)
        cz, cy, cx = 15, 15, 15
        a, b, c = 12.0, 6.0, 3.0
        vol = (((zz - cz) / a) ** 2 + ((yy - cy) / b) ** 2 + ((xx - cx) / c) ** 2) <= 1.0
        props = skmeasure.regionprops(vol.astype(np.int32))[0]
        _, equiv_diam = measureMembraneVolumeDiameter(props, scale=1.0)
        major, minor = measureAxes(props, equiv_diam)
        assert np.isclose(major / minor, a / c, rtol=0.15), f"Recovered axis ratio {major / minor:.2f} too far from true ratio {a / c:.2f}"
    def test_single_voxel_component_returns_nan_not_crash(self):
        """A degenerate single-voxel component returns NaN."""
        from skimage import measure as skmeasure
        vol = np.zeros((5, 5, 5), dtype=np.int32)
        vol[2, 2, 2] = 1
        props = skmeasure.regionprops(vol)[0]
        major, minor = measureAxes(props, equiv_diameter_nm=10.0)
        assert np.isnan(major) and np.isnan(minor)
    def test_line_component_returns_nan_not_crash(self):
        """A 1-voxel-wide line component returns NaN."""
        from skimage import measure as skmeasure
        vol = np.zeros((10, 5, 5), dtype=np.int32)
        vol[2:8, 2, 2] = 1
        props = skmeasure.regionprops(vol)[0]
        major, minor = measureAxes(props, equiv_diameter_nm=10.0)
        assert np.isnan(major) and np.isnan(minor)

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

# -- Vesicle-vs-debris discrimination tests --------
_QC_DEFAULTS = {
    "qc_max_sphere_rmse_rel": 0.25,
    "qc_max_aspect_ratio": 2.5,
    "qc_min_solidity": 0.10,
    "qc_min_arc_coverage": 0.50,
}

def _sphere_surface_coords(radius=15.0, n=2000):
    rng = np.random.default_rng(0)
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v * radius + 50.0

class TestSphereFitResidual:
    def test_round_shell_low_residual(self, sphere_regionprops):
        assert sphereFitResidual(sphere_regionprops.coords) < 0.15
    def test_flat_sheet_high_residual(self):
        zz, yy, xx = np.indices((3, 60, 60))
        coords = np.argwhere(np.ones((3, 60, 60), dtype=bool))
        assert sphereFitResidual(coords) > 0.25
    def test_degenerate_returns_nan(self):
        assert np.isnan(sphereFitResidual(np.array([[0, 0, 0], [1, 1, 1]])))
    def test_max_fit_points_subsamples_but_stays_accurate(self):
        pts = _sphere_surface_coords(radius=15.0, n=50000)
        full = sphereFitResidual(pts, max_fit_points=50000)
        capped = sphereFitResidual(pts, max_fit_points=500)
        assert capped < 0.05
        assert abs(capped - full) < 0.05

class TestArcCoverage:
    def test_full_sphere_high_coverage(self):
        assert arcCoverage(_sphere_surface_coords()) > 0.8
    def test_small_patch_low_coverage(self):
        pts = _sphere_surface_coords()
        patch = pts[(pts[:, 2] > 63)]  # a polar cap only
        assert arcCoverage(patch) < 0.5
    def test_degenerate_returns_nan(self):
        assert np.isnan(arcCoverage(np.array([[0, 0, 0], [1, 0, 0]])))

class TestClassifyVesicle:
    def test_clean_round_component(self):
        ok, flags = classifyVesicle(5000, 0.05, 1.1, 0.4, 0.9, True, _QC_DEFAULTS)
        assert ok is True and flags == ""
    def test_elongated_tube_flagged(self):
        ok, flags = classifyVesicle(5000, 0.1, 6.0, 0.3, 0.9, True, _QC_DEFAULTS)
        assert ok is False and "aspect_ratio" in flags
    def test_open_low_coverage_flagged(self):
        ok, flags = classifyVesicle(5000, 0.1, 1.2, 0.3, 0.2, False, _QC_DEFAULTS)
        assert ok is False and flags == "open_shell"
    def test_open_but_high_coverage_passes(self):
        ok, flags = classifyVesicle(5000, 0.1, 1.2, 0.3, 0.7, False, _QC_DEFAULTS)
        assert ok is True and flags == ""
    def test_too_small(self):
        ok, flags = classifyVesicle(3, np.nan, np.nan, np.nan, np.nan, False, _QC_DEFAULTS)
        assert ok is False and flags == "too_small"
    def test_nan_metric_is_flagged_not_passed(self):
        ok, flags = classifyVesicle(5000, np.nan, 1.2, 0.3, 0.9, True, _QC_DEFAULTS)
        assert ok is False and "sphere_rmse" in flags
    def test_threshold_override_flips_result(self):
        args = (5000, 0.1, 2.0, 0.3, 0.9, True)
        assert classifyVesicle(*args, _QC_DEFAULTS)[0] is True
        assert classifyVesicle(*args, {**_QC_DEFAULTS, "qc_max_aspect_ratio": 1.5})[0] is False
    def test_z_boundary_touch_flagged(self):
        ok, flags = classifyVesicle(5000, 0.05, 1.1, 0.4, 0.9, True, _QC_DEFAULTS, touches_z_boundary=True)
        assert ok is False and "touches_z_boundary" in flags
    def test_z_boundary_touch_defaults_false(self):
        ok, flags = classifyVesicle(5000, 0.05, 1.1, 0.4, 0.9, True, _QC_DEFAULTS)
        assert ok is True and "touches_z_boundary" not in flags

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