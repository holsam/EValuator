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
    Estimate sphere centre/radius as a coarse proxy for filtering purposes
    '''
    centroid = points.mean(axis=0)
    extent = points.max(axis=0) - points.min(axis=0)
    bbox_radius = float(numpy.mean(extent) / 2.0)
    if len(points) < 4:
        return centroid, bbox_radius
    centered = points - centroid
    eigenvalues, eigenvectors = numpy.linalg.eigh(numpy.cov(centered.T))
    # If spread is roughly isotropic, use bounding-box proxies
    if eigenvalues.max() <= 0 or eigenvalues.min() / eigenvalues.max() > 0.5:
        return centroid, bbox_radius
    # Smallest-variance eigenvector = symmetry axis of the anisotropic cloud
    axis = eigenvectors[:, 0]
    depth = centered @ axis
    radial = numpy.linalg.norm(centered - numpy.outer(depth, axis), axis=1)
    
    # Determine cap/symmetric distribution
    # Cap apexes taper to spread ≈ 0 at one depth extreme whereas a symmetric shape stays close to rim_radius at both extremes
    # Orient axis so the smaller-radial (candidate apex) extreme is depth.max() then separate cap apexes from symmetric ends by calculating taper ratio
    # If taper ratio > threshold, no real apex identified so have symmetric anisotopic shape: bbox centroid is accurate enought but extent is likely to underestimate radius
    if radial[numpy.argmax(depth)] > radial[numpy.argmin(depth)]:
        axis, depth = -axis, -depth

    rim_radius = float(radial.max())
    apex_radial = float(radial[numpy.argmax(depth)])
    taper_ratio = apex_radial / rim_radius if rim_radius > 0 else 1.0
    TAPER_RATIO_THRESHOLD = 0.5  # separate cap apexes (~0.1-0.3) from symmetric ends (~0.8-1.0)
    if taper_ratio > TAPER_RATIO_THRESHOLD:
        radius_estimate = float(numpy.linalg.norm(centered, axis=1).mean())
        return centroid, radius_estimate

    cap_height = float(depth.max() - depth.min())
    if cap_height <= 1e-9:
        return centroid, bbox_radius

    radius_estimate = (rim_radius ** 2 + cap_height ** 2) / (2 * cap_height)
    apex_point = centroid + axis * depth.max()
    cap_centroid = apex_point - axis * radius_estimate
    return cap_centroid, radius_estimate

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
