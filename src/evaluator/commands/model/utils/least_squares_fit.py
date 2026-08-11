'''
=======================================
EValuator: LEAST-SQUARES FIT MODELLING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np
from typing import Literal

# ====================
# Define constant schema variables
# ====================
# Schema constant — override by passing voxel_size_nm explicitly
DEFAULT_VOXEL_SIZE_NM = 1.0

# BIC parameter counts
_K_SPHERE = 4     # centre (3) + radius (1)
_K_ELLIPSOID = 9     # centre (3) + radii (3) + orientation (3 Euler angles)

# Minimum point counts
_MIN_PTS_SPHERE = 4
_MIN_PTS_ELLIPSOID = 9

# Anisotropy shortcut: ellipsoid collapses to sphere if max/min ratio is below this
_ANISOTROPY_THRESHOLD = 1.1

# Beam-axis guard: flag elongation within this many degrees of z
_DEFAULT_BEAM_AXIS_TOL_DEG = 25.0

# Reliability thresholds
_MAX_RELATIVE_RMSE = 0.15   # if (RMSE / radius) > threshold, suggests unreliable fit
_MIN_POINT_COUNT = 20     # if fewer surviving points than threshold, suggests unreliable fit
_MIN_LATITUDE_SPAN_DEG = 60     # if surviving band is narrower than threshold, suggests unreliable fit

# ====================
# Least-squares fit models
# ====================
def fit_sphere_least_squares(points: np.ndarray) -> tuple[np.ndarray, float, float]:
    '''
    Fit a sphere to a 3D point cloud by algebraic least squares
    '''
    if len(points) < 4:
        raise ValueError('At least 4 points required for sphere fit.')
    A = np.hstack([2 * points, np.ones((len(points), 1))])
    b = np.sum(points ** 2, axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    centre = sol[:3]
    radius = float(np.sqrt(sol[3] + centre @ centre))
    distances = np.linalg.norm(points - centre, axis=1)
    rmse = float(np.sqrt(np.mean((distances - radius) ** 2)))
    return centre, radius, rmse

def fit_ellipsoid(P):
    '''
    Algebraic least-squares ellipsoid fit (Li & Griffiths 2004 family)
    '''
    if len(P) < 9:
        return None
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    D = np.column_stack([x * x, y * y, z * z,
                         2 * x * y, 2 * x * z, 2 * y * z,
                         2 * x, 2 * y, 2 * z])
    try:
        v, *_ = np.linalg.lstsq(D, np.ones_like(x), rcond=None)
    except np.linalg.LinAlgError:
        return None
    a, b, c, d, e, f, g, h, i = v
    A = np.array([[a, d, e, g],
                  [d, b, f, h],
                  [e, f, c, i],
                  [g, h, i, -1.0]])
    try:
        centre = np.linalg.solve(-A[:3, :3], np.array([g, h, i]))
    except np.linalg.LinAlgError:
        return None
    T = np.eye(4); T[3, :3] = centre
    R = T @ A @ T.T
    R3 = R[:3, :3] / -R[3, 3]
    evals, evecs = np.linalg.eigh(R3)
    if np.any(evals <= 0):
        return None
    return dict(center=centre, radii=np.sqrt(1.0 / evals), evecs=evecs)

# ====================
# Define helper functions
# ====================
# _sphere_geometric_residuals: calculate the orthogonal distance of each point to the sphere surface
def _sphere_geometric_residuals(points: np.ndarray, centre: np.ndarray, radius: float) -> np.ndarray:
    return np.abs(np.linalg.norm(points - centre, axis=1) - radius)

# _ellipsoid_geometric_residuals: calculate the approximate orthogonal distance from each point to ellipsoid surface
def _ellipsoid_geometric_residuals(
    points: np.ndarray,
    centre: np.ndarray,
    radii: np.ndarray,
    evecs: np.ndarray,
) -> np.ndarray:
    # Shift to ellipsoid frame
    p_local = (points - centre) @ evecs  # (n, 3)
    # Normalised algebraic distance: == 1 on surface, > 1 outside
    norm_dist = np.sqrt(np.sum((p_local / radii) ** 2, axis=1))
    # Scale back to physical distance (approximate)
    return np.abs(norm_dist - 1.0) * np.mean(radii)

# _bic: returns a float for the calculated Bayesian Information Criterion for an array of residuals
def _bic(residuals: np.ndarray, k: int) -> float:
    n = len(residuals)
    rss = np.sum(residuals ** 2)
    return n * np.log(rss / n) + k * np.log(n)

# _assess_reliability: returns a dictionary containing results of three reliability assessments (relative RMSE, minimum point count, latitude span)
def _assess_reliability(
    points: np.ndarray,
    centre: np.ndarray,
    radius_or_mean_radius: float,
    rmse: float,
    rmse_relative_max: float = _MAX_RELATIVE_RMSE,
    min_points: int = _MIN_POINT_COUNT,
) -> dict:
    n = len(points)
    relative_rmse = rmse / radius_or_mean_radius if radius_or_mean_radius > 0 else np.inf
    rmse_ok = relative_rmse < rmse_relative_max
    count_ok = n >= min_points
    # Latitude span: angle from z-axis for each point relative to centre
    vecs = points - centre
    norms = np.linalg.norm(vecs, axis=1)
    with np.errstate(invalid='ignore'):
        latitudes = np.degrees(np.arcsin(np.clip(vecs[:, 2] / norms, -1, 1)))
    lat_span = float(latitudes.max() - latitudes.min()) if n > 0 else 0.0
    span_ok = lat_span >= _MIN_LATITUDE_SPAN_DEG
    return {
        'is_reliable': rmse_ok and count_ok and span_ok,
        'relative_rmse': float(relative_rmse),
        'rmse_ok': rmse_ok,
        'count_ok': count_ok,
        'lat_span_deg': lat_span,
        'span_ok': span_ok,
    }

# _beam_axis_flag: identifies if an ellipsoid's major axis is close to the z-axis, returning a dictionary containing this check and the angles
def _beam_axis_flag(evecs: np.ndarray, radii: np.ndarray, tol_deg: float) -> dict:
    major_idx = np.argmax(radii)
    major_axis = evecs[:, major_idx]
    # Angle between major axis and z
    cos_angle = np.clip(np.abs(major_axis[2]), 0, 1)
    angle_from_z = float(np.degrees(np.arccos(cos_angle)))
    flagged = angle_from_z < tol_deg
    return {
        'beam_axis_flagged': flagged,
        'major_axis_angle_from_z_deg': angle_from_z,
        'beam_axis_tol_deg': tol_deg,
    }


# ====================
# Define functions
# ====================
# fit_vesicle: fit a sphere and ellipsoid least squares model to a vesicle's point cloud and report better model
def fit_vesicle(
    points: np.ndarray,
    voxel_size_nm: float = DEFAULT_VOXEL_SIZE_NM,
    mode: Literal['report_both', 'bic'] = 'report_both',
    beam_axis_tol_deg: float = _DEFAULT_BEAM_AXIS_TOL_DEG,
    rmse_relative_max: float = _MAX_RELATIVE_RMSE,
    min_points: int = _MIN_POINT_COUNT,
) -> dict:
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 3:
        raise ValueError('points must be an (n, 3) array.')
    # Run sphere least squares fit
    if len(pts) < _MIN_PTS_SPHERE:
        raise ValueError(f'Need at least {_MIN_PTS_SPHERE} points; got {len(pts)}.')
    sph_centre, sph_radius, _ = fit_sphere_least_squares(pts)
    sph_residuals = _sphere_geometric_residuals(pts, sph_centre, sph_radius)
    sph_rmse_vox = float(np.sqrt(np.mean(sph_residuals ** 2)))
    bic_sphere = _bic(sph_residuals, _K_SPHERE)
    sph_centre_nm = sph_centre * voxel_size_nm
    sph_radius_nm = sph_radius * voxel_size_nm
    sph_rmse_nm = sph_rmse_vox * voxel_size_nm
    sphere_fit = {
        'centre': sph_centre_nm,
        'radius': sph_radius_nm,
        'rmse_nm': sph_rmse_nm,
        'bic': bic_sphere,
    }
    # Run ellipsoid least-squares fit (if enough points available)
    bic_ellipsoid = None
    ellipsoid_fit = None
    ell_result = None
    ell_fallback_reason = None
    if len(pts) >= _MIN_PTS_ELLIPSOID:
        ell_result = fit_ellipsoid(pts)
        if ell_result is not None:
            ell_centre = ell_result['center']
            ell_radii = ell_result['radii']   # ascending order
            ell_evecs = ell_result['evecs']
            ell_residuals = _ellipsoid_geometric_residuals(pts, ell_centre, ell_radii, ell_evecs)
            ell_rmse_vox = float(np.sqrt(np.mean(ell_residuals ** 2)))
            bic_ellipsoid = _bic(ell_residuals, _K_ELLIPSOID)
            ell_centre_nm = ell_centre * voxel_size_nm
            ell_radii_nm = ell_radii * voxel_size_nm
            ell_rmse_nm = ell_rmse_vox * voxel_size_nm
            ellipsoid_fit = {
                'centre': ell_centre_nm,
                'radii': ell_radii_nm,
                'orientation': ell_evecs,
                'rmse_nm': ell_rmse_nm,
                'bic': bic_ellipsoid,
            }
        else:
            ell_fallback_reason = 'degenerate'
    else:
        ell_fallback_reason = 'insufficient points'
    # Set model selection defaults
    chosen = 'sphere'
    use_ell = False
    # Select best model
    if ell_result is not None and bic_ellipsoid < bic_sphere:
        # BIC favours ellipsoid so run ellipsoid guards
        anisotropy = ell_result['radii'].max() / ell_result['radii'].min()
        if anisotropy < _ANISOTROPY_THRESHOLD:
            # Near-spherical ellipsoid: collapse to sphere
            chosen = 'sphere (anisotropy)'
        else:
            beam_info = _beam_axis_flag(ell_evecs, ell_radii, beam_axis_tol_deg)
            if beam_info['beam_axis_flagged']:
                chosen = 'sphere (beam-axis)'
            else:
                use_ell = True
                chosen = 'ellipsoid'
    elif ell_result is None and ell_fallback_reason == 'degenerate':
        # Ellipsoid was attempted but failed numerically
        chosen = 'sphere (degenerate)'
    if use_ell:
        out_centre = ell_centre_nm
        out_radius = float(np.mean(ell_radii_nm))
        out_radii = ell_radii_nm
        out_orientation = ell_evecs
        out_rmse = ell_rmse_nm
        reliability = _assess_reliability(pts, ell_centre, float(np.mean(ell_radii)), ell_rmse_vox, rmse_relative_max=rmse_relative_max, min_points=min_points)
        beam_axis_out = beam_info
    else:
        out_centre = sph_centre_nm
        out_radius = sph_radius_nm
        out_radii = None
        out_orientation = None
        out_rmse = sph_rmse_nm
        reliability = _assess_reliability(pts, sph_centre, sph_radius, sph_rmse_vox, rmse_relative_max=rmse_relative_max, min_points=min_points)
        beam_axis_out = None
    # Create output dictionary
    return {
        'chosen_model': chosen,
        'centre': out_centre,
        'radius': out_radius,
        'radii': out_radii,
        'orientation': out_orientation,
        'rmse_nm': out_rmse,
        'bic_sphere': bic_sphere,
        'bic_ellipsoid': bic_ellipsoid,
        'reliability': reliability,
        'beam_axis': beam_axis_out,
        'sphere_fit': sphere_fit,
        'ellipsoid_fit': ellipsoid_fit,
    }
