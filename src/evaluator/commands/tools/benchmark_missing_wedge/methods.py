'''
=======================================
EValuator: MISSING WEDGE BENCHMARKING SCRIPT METHODS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np
from scipy.ndimage import binary_closing, binary_erosion, find_objects, label
from skimage.draw import ellipsoid
from skimage.morphology import convex_hull_image

# ====================
# Define method functions
# ====================
# -- shell_voxel_diameter: returns float corresponding to raw shell voxel count
def _shell_voxel_diameter(binary: np.ndarray, voxel_size_nm: float) -> float:
    '''
    Calculate equivalent diameter from raw shell voxel count
    '''
    n = int(binary.sum())
    if n == 0:
        return float('nan')
    return 2 * (3 * n * voxel_size_nm ** 3 / (4 * np.pi)) ** (1 / 3)

# -- anisotropic_closing_per_component: returns ndarray with closed binary segmentation
def anisotropic_closing_per_component(
    binary: np.ndarray,
    z_radius: int = 5,
    xy_radius: int = 2,
    padding: int = 3,
    min_voxels: int = 50,
) -> np.ndarray:
    '''
    Close each connected component with a Z-elongated structuring element
    '''
    struct = ellipsoid(z_radius, xy_radius, xy_radius)
    labels, _ = label(binary)
    out = np.zeros_like(binary, dtype=bool)
    slices = find_objects(labels)

    for i, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        component_mask = labels[sl] == i
        if component_mask.sum() < min_voxels:
            continue
        padded_sl = tuple(
            slice(max(0, s.start - padding), min(binary.shape[d], s.stop + padding))
            for d, s in enumerate(sl)
        )
        component = labels[padded_sl] == i
        closed = binary_closing(component, structure=struct)
        out[padded_sl] |= closed

    return out

# N.B. this implementation of fit_least_squares is a simplified sphere-only approximation.
# The model command uses BIC to select between a spherical and ellipsoid model therefore actual runtimes may be longer.
# -- fit_least_squares: returns tuple of ndarray, float, float
def fit_least_squares(points: np.ndarray) -> tuple[np.ndarray, float, float]:
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

# -- hull_outer_diameter: returns float of equivalent diameter from convex hull of segmented shell voxels
def hull_outer_diameter(shell_binary: np.ndarray, voxel_size_nm: float) -> float:
    '''
    Calculate equivalent outer diameter from the convex hull of segmented shell voxels
    '''
    if shell_binary.sum() < 4:
        return float("nan")
    hull = convex_hull_image(shell_binary)
    volume_nm3 = hull.sum() * voxel_size_nm ** 3
    radius_nm = (3 * volume_nm3 / (4 * np.pi)) ** (1 / 3)
    return 2 * radius_nm

# -- hull_lumen_diameter: returns float of lumen diameter from convex hull of segmented shell voxels (eroded by membrane thickness)
def hull_lumen_diameter(
    shell_binary: np.ndarray,
    voxel_size_nm: float,
    membrane_thickness_nm: float,
) -> float:
    '''
    Calculate lumen diameter from hull eroded by membrane thickness
    '''
    if shell_binary.sum() < 4:
        return float("nan")
    hull = convex_hull_image(shell_binary)
    erosion_voxels = int(np.ceil(membrane_thickness_nm / voxel_size_nm))
    lumen = binary_erosion(hull, iterations=erosion_voxels)
    if lumen.sum() == 0:
        return float("nan")
    volume_nm3 = lumen.sum() * voxel_size_nm ** 3
    radius_nm = (3 * volume_nm3 / (4 * np.pi)) ** (1 / 3)
    return 2 * radius_nm

# -- xy_z_diameter_metrics: returns dictionary of xy_diameter, z_diameter, and xy_z_ratio
def xy_z_diameter_metrics(binary: np.ndarray, voxel_size_nm: float) -> dict:
    '''
    Compute XY-projected diameter and Z-extent separately
    '''
    coords = np.argwhere(binary)
    if len(coords) == 0:
        return {'xy_diameter_nm': np.nan, 'z_extent_nm': np.nan, 'xy_z_ratio': np.nan}
    # Calculate x,y-diameters
    xy_projection = binary.any(axis=0)
    xy_area_voxels = int(xy_projection.sum())
    xy_diameter_nm = 2 * np.sqrt(xy_area_voxels / np.pi) * voxel_size_nm
    # Calculate z extent
    z_extent_voxels = int(coords[:, 0].max() - coords[:, 0].min() + 1)
    z_extent_nm = z_extent_voxels * voxel_size_nm
    return {
        'xy_diameter_nm': float(xy_diameter_nm),
        'z_extent_nm': float(z_extent_nm),
        'xy_z_ratio': float(xy_diameter_nm / z_extent_nm) if z_extent_nm > 0 else np.nan,
    }

# -- orientation_quality_score: returns dictionary of score, anisotropy and z-alignment
def orientation_quality_score(binary: np.ndarray) -> dict:
    '''
    Score how 'safe' an EV is from missing-wedge bias
    '''
    coords = np.argwhere(binary).astype(float)
    if len(coords) < 10:
        return {'score': np.nan, 'anisotropy': np.nan, 'z_alignment': np.nan}
    # Calculate eigenvalues and eigenvectors of covariance of coordinates
    coords -= coords.mean(axis=0)
    cov = np.cov(coords.T)
    eigvals, eigvecs = np.linalg.eigh(cov)

    anisotropy = float(1 - eigvals[0] / eigvals[-1]) if eigvals[-1] > 0 else 0.0
    major_axis = eigvecs[:, -1]
    z_alignment = float(abs(major_axis[0]))
    score = float(1 - anisotropy * z_alignment)

    return {'score': score, 'anisotropy': anisotropy, 'z_alignment': z_alignment}

# -- weighted_population_diameter: returns dictionary of diameter statistics
def weighted_population_diameter(
    diameters_nm: np.ndarray,
    orientation_scores: np.ndarray,
    threshold: float = 0.5,
) -> dict:
    '''
    Summarise a population of diameters with orientation-quality weighting
    '''
    diameters_nm = np.asarray(diameters_nm)
    orientation_scores = np.asarray(orientation_scores)
    valid = ~np.isnan(diameters_nm) & ~np.isnan(orientation_scores)
    d = diameters_nm[valid]
    s = orientation_scores[valid]
    above = s >= threshold
    return {
        'n_total': int(valid.sum()),
        'n_above_threshold': int(above.sum()),
        'mean_all_nm': float(d.mean()),
        'median_all_nm': float(np.median(d)),
        'mean_filtered_nm': float(d[above].mean()) if above.any() else np.nan,
        'median_filtered_nm': float(np.median(d[above])) if above.any() else np.nan,
        'weighted_mean_nm': float(np.average(d, weights=s)),
    }