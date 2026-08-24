'''
=======================================
EValuator: LABEL GEOMETRIC PROXY UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy

# =========================
# DEFINE FUNCTION: estimateCentroidRadius
# =========================
def estimateCentroidRadius(points: numpy.ndarray) -> tuple[numpy.ndarray, float]:
    '''
    Estimate radius from bounding-box (half the mean of extent diamters), only intended as a coarse estimate for filtering purposes
    '''
    centroid = points.mean(axis=0)
    extent = points.max(axis=0) - points.min(axis=0)
    radius_estimate = float(numpy.mean(extent) / 2.0)
    return centroid, radius_estimate

# =========================
# DEFINE FUNCTION: estimateArcCoverage
# =========================
def estimateArcCoverage(points: numpy.ndarray, centroid: numpy.ndarray, radius_estimate: float) -> float:
    '''
    Estimate fraction of spherical surface covered by segmentation via angular binning
    '''
    if radius_estimate <= 0 or len(points) == 0:
        return 0.0
    vecs = points - centroid
    norms = numpy.linalg.norm(vecs, axis=1)
    norms[norms == 0] = 1e-9
    unit_vecs = vecs / norms[:, None]
    # Coarse lat/long grid (10-degree bins each), equal-area: bin sin(lat)
    n_lat_bins, n_lon_bins = 18, 36
    lon = numpy.degrees(numpy.arctan2(unit_vecs[:, 1], unit_vecs[:, 0]))
    lat_idx = numpy.clip((((unit_vecs[:, 2] + 1) / 2) * n_lat_bins).astype(int), 0, n_lat_bins - 1)
    lon_idx = numpy.clip(((lon + 180) / 360 * n_lon_bins).astype(int), 0, n_lon_bins - 1)
    occupied = set(zip(lat_idx.tolist(), lon_idx.tolist()))
    return len(occupied) / (n_lat_bins * n_lon_bins)
