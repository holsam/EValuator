# ====================
# Import external dependencies
# ====================
import numpy as np
import pytest

# ====================
# Import internal dependencies
# ====================
from evaluator.commands.label.utils.geometric_proxies import estimateCentroidRadius, estimateArcCoverage
from evaluator.commands.label.utils.merge import findMergeGroups, applyMerges

# ====================
# Define point-cloud generator helpers
# ====================
def _sphere_points(centre=(0.0, 0.0, 0.0), radius=10.0, n=2000):
    rng = np.random.default_rng(0)
    vecs = rng.normal(size=(n, 3))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs * radius + np.asarray(centre)

def _rotate_to_pole(points, pole):
    '''Rotate points generated around +z so +z maps onto unit vector pole'''
    pole = pole / np.linalg.norm(pole)
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(z, pole)
    sin_angle = np.linalg.norm(axis)
    cos_angle = np.dot(z, pole)
    if sin_angle < 1e-12:
        return points if cos_angle > 0 else points * np.array([1.0, -1.0, -1.0])
    axis /= sin_angle
    K = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0],
    ])
    R = np.eye(3) + K * sin_angle + K @ K * (1 - cos_angle)
    return points @ R.T

def _cap_points(centre=(0.0, 0.0, 0.0), radius=10.0, pole=(0, 0, 1), half_angle_deg=30.0, n=500):
    rng = np.random.default_rng(0)
    cos_min = np.cos(np.radians(half_angle_deg))
    cos_theta = rng.uniform(cos_min, 1.0, n)
    sin_theta = np.sqrt(1 - cos_theta ** 2)
    phi = rng.uniform(0, 2 * np.pi, n)
    local = np.stack([sin_theta * np.cos(phi), sin_theta * np.sin(phi), cos_theta], axis=1)
    local = _rotate_to_pole(local, np.asarray(pole, dtype=float))
    return local * radius + np.asarray(centre)

# ====================
# Define arc-coverage estimator tests
# ====================
class TestEstimateArcCoverage:
    def test_full_sphere_near_one(self):
        pts = _sphere_points()
        centroid, radius = estimateCentroidRadius(pts)
        assert estimateArcCoverage(pts, centroid, radius) > 0.9

    def test_single_cap_below_threshold(self):
        pts = _cap_points(half_angle_deg=20.0)
        centroid, radius = estimateCentroidRadius(pts)
        assert estimateArcCoverage(pts, centroid, radius) < 0.4

    def test_two_opposing_arcs_combined_exceeds_either_alone(self):
        cap_a = _cap_points(pole=(0, 0, 1), half_angle_deg=25.0)
        cap_b = _cap_points(pole=(0, 0, -1), half_angle_deg=25.0)
        centroid_a, radius_a = estimateCentroidRadius(cap_a)
        coverage_a = estimateArcCoverage(cap_a, centroid_a, radius_a)
        combined = np.concatenate([cap_a, cap_b])
        centroid_c, radius_c = estimateCentroidRadius(combined)
        coverage_c = estimateArcCoverage(combined, centroid_c, radius_c)
        assert coverage_a < 0.4
        assert coverage_c > coverage_a

    def test_empty_points_returns_zero(self):
        assert estimateArcCoverage(np.empty((0, 3)), np.zeros(3), 1.0) == 0.0

# ====================
# Define merge heuristic tests
# ====================
class TestFindMergeGroups:
    def test_split_pair_same_source_merges(self):
        cap_a = _cap_points(centre=(0, 0, 0), pole=(0, 0, 1), half_angle_deg=25.0)
        cap_b = _cap_points(centre=(0, 0, 0), pole=(0, 0, -1), half_angle_deg=25.0)
        groups = findMergeGroups({1: cap_a, 2: cap_b}, centre_tol_factor=1.5, radius_tol_pct=0.30)
        assert sorted(groups[0]) == [1, 2]

    def test_separate_vesicles_not_merged(self):
        pts_a = _sphere_points(centre=(0, 0, 0), radius=5.0)
        pts_b = _sphere_points(centre=(500, 500, 500), radius=20.0)
        groups = findMergeGroups({1: pts_a, 2: pts_b}, centre_tol_factor=1.5, radius_tol_pct=0.30)
        assert sorted(sorted(g) for g in groups) == [[1], [2]]

    def test_chain_merge_transitive(self):
        pts_a = _sphere_points(centre=(0, 0, 0), radius=5.0)
        pts_b = _sphere_points(centre=(7, 0, 0), radius=5.0)
        pts_c = _sphere_points(centre=(14, 0, 0), radius=5.0)
        groups = findMergeGroups(
            {1: pts_a, 2: pts_b, 3: pts_c}, centre_tol_factor=1.5, radius_tol_pct=0.30
        )
        assert sorted(groups[0]) == [1, 2, 3]

class TestApplyMerges:
    def test_voxel_count_preserved(self):
        vol = np.zeros((10, 10, 10), dtype=np.int32)
        vol[0:5, 0, 0] = 1
        vol[5:10, 0, 0] = 2
        merged = applyMerges(vol, [[1, 2]])
        assert np.sum(merged == 1) == 10
        assert 2 not in np.unique(merged)

    def test_group_of_one_is_noop(self):
        vol = np.zeros((5, 5, 5), dtype=np.int32)
        vol[0, 0, 0] = 1
        merged = applyMerges(vol, [[1]])
        assert np.array_equal(merged, vol)