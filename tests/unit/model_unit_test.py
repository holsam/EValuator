# ====================
# Import external dependencies
# ====================
import numpy as np
import pytest

# ====================
# Import internal dependencies
# ====================
from evaluator.commands.model.utils.least_squares_fit import (
    fit_sphere_least_squares,
    fit_ellipsoid,
    fit_vesicle,
)
from evaluator.commands.model.utils.reconstruction import build_fitted_mrc

# ====================
# Define point-cloud generator helpers
# ====================
# -- _sphere_points: n points over the full sphere surface (Fibonacci sampling)
def _sphere_points(centre=(50.0, 50.0, 50.0), radius=20.0, n=800, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    i = np.arange(n)
    phi = np.arccos(1 - 2 * (i + 0.5) / n)      # polar angle: 0 -> pi (full sphere)
    theta = np.pi * (1 + 5 ** 0.5) * i          # golden angle azimuth
    x = radius * np.sin(phi) * np.cos(theta)
    y = radius * np.sin(phi) * np.sin(theta)
    z = radius * np.cos(phi)
    pts = np.stack([x, y, z], axis=1) + np.asarray(centre)
    if noise:
        pts = pts + rng.normal(0.0, noise, size=pts.shape)
    return pts

# -- _ellipsoid_points: n points over the full ellipsoid surface, optionally rotated
def _ellipsoid_points(centre=(50.0, 50.0, 50.0), radii=(10.0, 20.0, 30.0), rotation=None, n=800, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    i = np.arange(n)
    phi = np.arccos(1 - 2 * (i + 0.5) / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    local = np.stack([
        radii[0] * np.sin(phi) * np.cos(theta),
        radii[1] * np.sin(phi) * np.sin(theta),
        radii[2] * np.cos(phi),
    ], axis=1)
    if rotation is not None:
        local = local @ rotation.T
    pts = local + np.asarray(centre)
    if noise:
        pts = pts + rng.normal(0.0, noise, size=pts.shape)
    return pts

# -- _rotation_about_x: right-handed rotation matrix about the x-axis (index 0)
def _rotation_about_x(angle_deg):
    a = np.radians(angle_deg)
    return np.array([
        [1, 0, 0],
        [0, np.cos(a), -np.sin(a)],
        [0, np.sin(a), np.cos(a)],
    ])

# -- _narrow_band_points: points confined to a ~20 degree latitude band,
#    simulating a vesicle with most of its surface missing
def _narrow_band_points(centre=(50.0, 50.0, 50.0), radius=20.0, n=200, seed=0):
    rng = np.random.default_rng(seed)
    phi = np.radians(rng.uniform(80.0, 100.0, size=n))   # polar angle near equator
    theta = rng.uniform(0.0, 2 * np.pi, size=n)
    x = radius * np.sin(phi) * np.cos(theta)
    y = radius * np.sin(phi) * np.sin(theta)
    z = radius * np.cos(phi)
    return np.stack([x, y, z], axis=1) + np.asarray(centre)

# -- _flat_ring_points: points on a flat annulus (constant z), a degenerate
#    input for ellipsoid fitting
def _flat_ring_points(centre=(50.0, 50.0, 50.0), radius=15.0, n=40):
    theta = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    z = np.zeros_like(theta)
    return np.stack([x, y, z], axis=1) + np.asarray(centre)


# ====================
# Define fit_sphere_least_squares tests
# ====================
class TestFitSphereLeastSquares:
    def test_recovers_known_centre_and_radius(self):
        '''A clean sphere point cloud must recover its true centre and radius.'''
        centre, radius = (50.0, 50.0, 50.0), 20.0
        pts = _sphere_points(centre=centre, radius=radius, noise=0.01, seed=1)
        fit_centre, fit_radius, rmse = fit_sphere_least_squares(pts)
        assert np.allclose(fit_centre, centre, atol=0.5)
        assert np.isclose(fit_radius, radius, atol=0.5)
        assert rmse < 0.5
    def test_too_few_points_raises(self):
        pts = _sphere_points(n=3)
        with pytest.raises(ValueError):
            fit_sphere_least_squares(pts)
    def test_rmse_increases_with_noise(self):
        clean = _sphere_points(noise=0.0, seed=2)
        noisy = _sphere_points(noise=2.0, seed=2)
        _, _, rmse_clean = fit_sphere_least_squares(clean)
        _, _, rmse_noisy = fit_sphere_least_squares(noisy)
        assert rmse_noisy > rmse_clean


# ====================
# Define fit_ellipsoid tests
# ====================
class TestFitEllipsoid:
    def test_recovers_known_radii_axis_aligned(self):
        '''An axis-aligned ellipsoid must recover its true (sorted) radii and centre.'''
        centre, radii = (50.0, 50.0, 50.0), (10.0, 20.0, 30.0)
        pts = _ellipsoid_points(centre=centre, radii=radii, noise=0.02, seed=3)
        result = fit_ellipsoid(pts)
        assert result is not None
        assert np.allclose(result['center'], centre, atol=0.5)
        # Radii are returned in the order set by eigenvalue sort, not
        # necessarily matching input order, so compare sorted values.
        assert np.allclose(sorted(result['radii']), sorted(radii), atol=0.5)
    def test_too_few_points_returns_none(self):
        pts = _ellipsoid_points(n=8)
        assert fit_ellipsoid(pts) is None
    def test_degenerate_flat_points_returns_none(self):
        '''A flat ring (no z variation) is a degenerate quadric fit.'''
        pts = _flat_ring_points()
        assert fit_ellipsoid(pts) is None


# ====================
# Define fit_vesicle model-selection tests
# ====================
class TestFitVesicleModelSelection:
    def test_perfect_sphere_selects_sphere(self):
        pts = _sphere_points(radius=20.0, noise=0.01, seed=4)
        result = fit_vesicle(pts)
        assert result['chosen_model'].startswith('sphere')
        assert result['radii'] is None
        assert result['orientation'] is None
    def test_elongated_off_axis_selects_ellipsoid(self):
        '''
        Major axis (radius 30) rotated 90 degrees about x so it points
        along global y, i.e. 90 degrees from the beam (z) axis - well
        outside the beam-axis guard tolerance.
        '''
        pts = _ellipsoid_points(
            radii=(10.0, 10.0, 30.0),
            rotation=_rotation_about_x(90.0),
            noise=0.02, seed=5,
        )
        result = fit_vesicle(pts)
        assert result['chosen_model'] == 'ellipsoid'
        assert result['radii'] is not None
        assert result['orientation'] is not None
    def test_elongated_along_beam_axis_selects_sphere_beam_axis(self):
        '''Major axis (radius 30) left aligned with global z (the beam axis).'''
        pts = _ellipsoid_points(radii=(10.0, 10.0, 30.0), noise=0.02, seed=6)
        result = fit_vesicle(pts)
        assert result['chosen_model'] == 'sphere (beam-axis)'
        assert result['radii'] is None
    def test_insufficient_points_for_ellipsoid_defaults_to_sphere(self):
        '''Between 4 and 8 points: too few for an ellipsoid attempt at all.'''
        pts = _sphere_points(n=6, seed=7)
        result = fit_vesicle(pts)
        assert result['chosen_model'] == 'sphere'
        assert result['bic_ellipsoid'] is None
    def test_degenerate_ellipsoid_fit_falls_back_to_sphere(self):
        pts = _flat_ring_points(n=40)
        result = fit_vesicle(pts)
        assert result['chosen_model'] == 'sphere (degenerate)'
    def test_raises_for_fewer_than_min_sphere_points(self):
        pts = _sphere_points(n=3)
        with pytest.raises(ValueError):
            fit_vesicle(pts)
    def test_output_contains_expected_keys(self):
        pts = _sphere_points(seed=8)
        result = fit_vesicle(pts)
        expected_keys = {
            'chosen_model', 'centre', 'radius', 'radii', 'orientation',
            'rmse_nm', 'bic_sphere', 'bic_ellipsoid', 'reliability',
            'beam_axis', 'sphere_fit', 'ellipsoid_fit',
        }
        assert expected_keys.issubset(result.keys())


# ====================
# Define fit_vesicle reliability-gate tests
# ====================
class TestFitVesicleReliability:
    def test_good_sphere_passes_gate(self):
        pts = _sphere_points(n=800, noise=0.01, seed=9)
        result = fit_vesicle(pts)
        rel = result['reliability']
        assert rel['is_reliable'] is True
        assert rel['rmse_ok'] is True
        assert rel['count_ok'] is True
        assert rel['span_ok'] is True
    def test_low_point_count_fails_gate(self):
        '''Fewer than 20 points fails the count check even if the fit itself is good.'''
        pts = _sphere_points(n=10, noise=0.01, seed=10)
        result = fit_vesicle(pts)
        rel = result['reliability']
        assert rel['count_ok'] is False
        assert rel['is_reliable'] is False
    def test_narrow_latitude_band_fails_gate(self):
        '''A ~20 degree latitude band is well under the 60 degree span threshold.'''
        pts = _narrow_band_points(n=200, seed=11)
        result = fit_vesicle(pts)
        rel = result['reliability']
        assert rel['span_ok'] is False
        assert rel['is_reliable'] is False
    def test_noisy_points_fail_rmse_gate(self):
        '''Noise comparable to the radius pushes relative RMSE over threshold.'''
        pts = _sphere_points(radius=20.0, n=800, noise=6.0, seed=12)
        result = fit_vesicle(pts)
        rel = result['reliability']
        assert rel['rmse_ok'] is False
        assert rel['is_reliable'] is False


# ====================
# Define build_fitted_mrc tests
# ====================
class TestBuildFittedMRC:
    # -- Helper fixtures -----------------
    @pytest.fixture
    def sphere_records(self):
        '''One reliable and one unreliable sphere, well separated, in a (40,40,40) volume.'''
        return [
            {
                'centre': np.array([10.0, 10.0, 10.0]),
                'radius': 5.0,
                'radii': None,
                'orientation': None,
                'reliability': {'is_reliable': True},
                'label_id': 1,
            },
            {
                'centre': np.array([30.0, 30.0, 30.0]),
                'radius': 5.0,
                'radii': None,
                'orientation': None,
                'reliability': {'is_reliable': False},
                'label_id': 2,
            },
        ]
    @pytest.fixture
    def ellipsoid_record(self):
        '''A single axis-aligned, reliable ellipsoid in a (40,40,40) volume.'''
        return [{
            'centre': np.array([20.0, 20.0, 20.0]),
            'radius': 8.0,
            'radii': np.array([4.0, 6.0, 9.0]),
            'orientation': np.eye(3),
            'reliability': {'is_reliable': True},
            'label_id': 3,
        }]

    # -- Tests ----------------------------
    def test_default_excludes_unreliable(self, sphere_records):
        volume = build_fitted_mrc((40, 40, 40), sphere_records, voxel_size_nm=1.0)
        assert 1 in np.unique(volume)
        assert 2 not in np.unique(volume)
    def test_include_unreliable_flag_includes_all(self, sphere_records):
        volume = build_fitted_mrc((40, 40, 40), sphere_records, voxel_size_nm=1.0, include_unreliable=True)
        assert 1 in np.unique(volume)
        assert 2 in np.unique(volume)
    def test_output_shape_matches_input(self, sphere_records):
        shape = (40, 40, 40)
        volume = build_fitted_mrc(shape, sphere_records, voxel_size_nm=1.0)
        assert volume.shape == shape
    def test_output_dtype_uint16(self, sphere_records):
        volume = build_fitted_mrc((40, 40, 40), sphere_records, voxel_size_nm=1.0)
        assert volume.dtype == np.uint16
    def test_sphere_voxel_count_matches_analytic(self, sphere_records):
        volume = build_fitted_mrc((40, 40, 40), sphere_records[:1], voxel_size_nm=1.0)
        n_voxels = int((volume == 1).sum())
        expected = (4 / 3) * np.pi * 5.0 ** 3
        assert np.isclose(n_voxels, expected, rtol=0.1)
    def test_ellipsoid_voxel_count_matches_analytic(self, ellipsoid_record):
        volume = build_fitted_mrc((40, 40, 40), ellipsoid_record, voxel_size_nm=1.0)
        n_voxels = int((volume == 3).sum())
        expected = (4 / 3) * np.pi * 4.0 * 6.0 * 9.0
        assert np.isclose(n_voxels, expected, rtol=0.1)
    def test_empty_records_returns_all_zero_volume(self):
        shape = (20, 20, 20)
        volume = build_fitted_mrc(shape, [], voxel_size_nm=1.0)
        assert volume.shape == shape
        assert np.all(volume == 0)