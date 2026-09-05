'''
=======================================
EValuator: GEOMETRIC ANALYSIS UTILITIES
=======================================
'''
# ====================
# Import external dependencies
# ====================
import numpy
from scipy.spatial import ConvexHull

# ====================
# Import shared EValuator fit/proxy maths
# ====================
from evaluator.commands.model.utils.least_squares_fit import fit_sphere_least_squares, _sphere_geometric_residuals
from evaluator.commands.label.utils.geometric_proxies import estimateCentroidRadius, estimateArcCoverage

# Default value for `qc_max_fit_points` config parameter
_QC_MAX_FIT_POINTS = 4000

def _subsample(pts: numpy.ndarray, max_points: int = _QC_MAX_FIT_POINTS) -> numpy.ndarray:
    if len(pts) <= max_points:
        return pts
    rng = numpy.random.default_rng(0)  # deterministic: same rows every run
    return pts[rng.choice(len(pts), max_points, replace=False)]

# =========================
# DEFINE FUNCTION: sphereFitResidual
# =========================
def sphereFitResidual(coords: numpy.ndarray, max_fit_points: int = _QC_MAX_FIT_POINTS) -> float:
    '''
    Relative RMSE (RMSE/fitted radius) of best-fit sphere over component surface voxels
    '''
    pts = _subsample(numpy.asarray(coords, dtype=float), max_fit_points)
    if len(pts) < 4:
        return numpy.nan
    centre, radius, _ = fit_sphere_least_squares(pts)
    if not radius > 0:
        return numpy.nan
    residuals = _sphere_geometric_residuals(pts, centre, radius)
    return float(numpy.sqrt(numpy.mean(residuals ** 2)) / radius)

# =========================
# DEFINE FUNCTION: solidity
# =========================
def solidity(coords: numpy.ndarray, n_voxels: int, max_fit_points: int = _QC_MAX_FIT_POINTS) -> float:
    '''
    Voxel count/convex-hull volume
    '''
    pts = _subsample(numpy.asarray(coords, dtype=float), max_fit_points)
    if len(pts) < 4:
        return numpy.nan
    try:
        hull_volume = ConvexHull(pts).volume
    except Exception:
        return numpy.nan
    return n_voxels / hull_volume if hull_volume > 0 else numpy.nan

# =========================
# DEFINE FUNCTION: arcCoverage
# =========================
def arcCoverage(coords: numpy.ndarray, max_fit_points: int = _QC_MAX_FIT_POINTS) -> float:
    '''
    Fraction of the fitted sphere's surface occupied by component's voxels
    '''
    pts = _subsample(numpy.asarray(coords, dtype=float), max_fit_points)
    if len(pts) < 4:
        return numpy.nan
    centroid, radius_estimate = estimateCentroidRadius(pts)
    return estimateArcCoverage(pts, centroid, radius_estimate)

# =========================
# DEFINE FUNCTION: deriveAxes
# =========================
def deriveAxes(intertia_tensor, voxel_size_nm=None):
    '''
    Derive semi-axes (a ≥ b ≥ c) of the best-fit ellipsoid from inertia tensor eigenvalues. eigvalsh returns eigenvalues in ascending order (I_a ≤ I_b ≤ I_c).
    '''
    eigvals = numpy.linalg.eigvalsh(intertia_tensor)
    eigvals = numpy.clip(eigvals, 0, None)
    with numpy.errstate(divide="ignore", invalid="ignore"):
        inv_sqrt = numpy.where(eigvals > 0, 1.0 / numpy.sqrt(eigvals), 0.0)
    return inv_sqrt

# =========================
# DEFINE FUNCTION: measureAxes
# =========================
def measureAxes(component, equiv_diameter_nm):
    '''
    Measure major and minor axes by approximating the EV as an ellipsoid. Semi-axes are derived from inertia tensor eigenvalues and scaled to real-world size using the equivalent diameter.
    '''
    inv_sqrt_axes = deriveAxes(intertia_tensor=component.inertia_tensor)
    geomean_inv_sqrt = (inv_sqrt_axes[0] * inv_sqrt_axes[1] * inv_sqrt_axes[2]) ** (1 / 3)
    if geomean_inv_sqrt > 0:
        axis_scale = (equiv_diameter_nm / 2.0) / geomean_inv_sqrt
    principal_semiaxis_a, principal_semiaxis_b, principal_semiaxis_c = inv_sqrt_axes * axis_scale
    major_axis = 2 * principal_semiaxis_a
    minor_axis = 2 * principal_semiaxis_c
    return major_axis, minor_axis


# =========================
# DEFINE FUNCTION: shellVolume
# =========================
def shellVolume(diameter_nm, voxel_size_nm, thickness_vox):
    '''
    Calculate the expected voxel count of a hollow spherical shell, used for the voxel-count size filter.
    '''
    r_outer = diameter_nm / (2 * voxel_size_nm)
    r_inner = max(0, r_outer - thickness_vox)
    return (4 / 3) * numpy.pi * (r_outer ** 3 - r_inner ** 3)