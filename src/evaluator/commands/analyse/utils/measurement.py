'''
=======================================
EValuator: MEASUREMENT ANALYSIS UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy
from scipy import ndimage
from skimage import measure

# DEFAULT_MEMBRANE_THICKNESS_NM: measured median membrane segmentation thickness produced by MemBrain-seg
DEFAULT_MEMBRANE_THICKNESS_NM = 2.6

# =========================
# DEFINE FUNCTION: computeSurfaceArea
# =========================
def computeSurfaceArea(component_mask: numpy.ndarray, voxel_size_nm: float):
    '''
    Estimates surface area using the marching cubes algorithm. Returns nm^2 if voxel size is known, otherwise vox^2.
    '''
    try:
        verts, faces, _, _ = measure.marching_cubes(
            component_mask.astype(numpy.uint8),
            level=0.5,
            spacing=(1.0, 1.0, 1.0),
        )
        sa_vox = measure.mesh_surface_area(verts, faces)
    except (ValueError, RuntimeError):
        return numpy.nan
    if voxel_size_nm is not None:
        return sa_vox * (voxel_size_nm ** 2)
    return sa_vox

# =========================
# DEFINE FUNCTION: estimateMembraneThickness
# =========================
def estimateMembraneThickness(mask: numpy.ndarray, voxel_size_nm: float | None, *, min_ridge_voxels: int = 100) -> float | None:
    '''
    Estimate segmented membrane shell thickness (twice the median Euclidean distance-transform value along local maxima).
    '''
    if not mask.any():
        return None
    # crop to the mask's bounding box to keep the distance transform small
    mask = mask[ndimage.find_objects(mask.astype(numpy.uint8))[0]]
    dist = ndimage.distance_transform_edt(mask, sampling=voxel_size_nm if voxel_size_nm is not None else 1.0)
    # plateau-tolerant ridge: voxels at least as far from the background as all 26 neighbours
    ridge = mask & (dist >= ndimage.maximum_filter(dist, size=3))
    if ridge.sum() < min_ridge_voxels:
        return None
    return float(2 * numpy.median(dist[ridge]))


# =========================
# DEFINE FUNCTION: measureMembraneVolumeDiameter
# =========================
def measureMembraneVolumeDiameter(component, scale, membrane_thickness_nm: float = 2.6):
    '''
    Measures the volume of membrane components in voxels and converts to nm^3. Derives the equivalent spherical diameter by treating membrane volume as a spherical shell of known thickness.
    '''
    vol_vox = component.area
    vol_nm3 = vol_vox * (scale ** 3)
    t = membrane_thickness_nm
    if t is not None and t > 0:
        # use the positive root from solving 4/3 pi (R^3 - (R-t)^3) = vol_nm3
        discriminant = max(vol_nm3 / (numpy.pi * t) - (t ** 2) / 3, 0.0)
        outer_radius_nm = (t / 2) + (numpy.sqrt(discriminant) / 2)
        equiv_diameter_nm = 2 * outer_radius_nm
    else:
        # no thickness available: fall back to a biased solid-sphere-equivalent diameter
        equiv_diameter_nm = (6 * vol_nm3 / numpy.pi) ** (1 / 3)
    return vol_nm3, equiv_diameter_nm

# =========================
# DEFINE FUNCTION: measureXYDiameter
# =========================
def measureXYDiameter(component_mask, scale):
    '''
    Diameter from the widest xy slice (mean of the y and x extents), in nm if scale is a voxel size.
    Independent of z, so unaffected by clipping at the z faces.
    '''
    per_slice = (_sliceExtent(component_mask.any(axis=2)) + _sliceExtent(component_mask.any(axis=1))) / 2
    return float(per_slice.max() * scale)

# =========================
# DEFINE HELPER FUNCTION: _sliceExtent
# =========================
def _sliceExtent(slice_mask: numpy.ndarray) -> numpy.ndarray:
    '''
    Per-row extent (voxels) between the first and last True along axis 1; 0 for empty rows.
    '''
    idx = numpy.arange(slice_mask.shape[1])
    hi = numpy.where(slice_mask, idx, -1).max(axis=1)
    lo = numpy.where(slice_mask, idx, slice_mask.shape[1]).min(axis=1)
    return numpy.where(slice_mask.any(axis=1), hi - lo + 1, 0)

# =========================
# DEFINE FUNCTION: createComponentMask
# =========================
def createComponentMask(component, labelled_vol, label_val):
    '''
    Extract the bounding-box sub-volume for a given component label and return
    a boolean mask.
    '''
    bbox = component.bbox
    slices = (
        slice(bbox[0], bbox[3]),
        slice(bbox[1], bbox[4]),
        slice(bbox[2], bbox[5]),
    )
    return labelled_vol[slices] == label_val

# =========================
# DEFINE FUNCTION: measureLumenVolume
# =========================
def measureLumenVolume(component_mask, scale):
    '''
    Calculate the lumen volume by filling holes and subtracting the membrane shell.
    '''
    filled_mask = ndimage.binary_fill_holes(component_mask)
    lumen_vol_vox = numpy.sum(filled_mask) - numpy.sum(component_mask)
    return lumen_vol_vox * (scale ** 3)

# =========================
# DEFINE FUNCTION: measureEccentricityAspectRatio
# =========================
def measureEccentricityAspectRatio(major_axis_diameter, minor_axis_diameter):
    '''
    Given major and minor diameters, calculate eccentricity and aspect ratio. Eccentricity: 0 (spherical) → 1 (tubular).
    '''
    semimajor = major_axis_diameter / 2
    semiminor = minor_axis_diameter / 2
    eccentricity = numpy.sqrt(1 - (semiminor / semimajor) ** 2) if semimajor > 0 else numpy.nan
    aspect_ratio = major_axis_diameter / minor_axis_diameter if minor_axis_diameter > 0 else numpy.nan
    return eccentricity, aspect_ratio

# =========================
# DEFINE FUNCTION: classifyVesicle
# =========================
def classifyVesicle(n_voxels, sphere_rmse_rel, aspect_ratio, solidity, arc_coverage, is_enclosed, qc_params):
    '''
    Classify component as `is_vesicle_like` unless any enabled check fails.
    '''
    if n_voxels < 4:
        return False, 'too_small'
    flags = []
    if not (sphere_rmse_rel <= qc_params['qc_max_sphere_rmse_rel']):
        flags.append('sphere_rmse')
    if not (aspect_ratio <= qc_params['qc_max_aspect_ratio']):
        flags.append('aspect_ratio')
    if not (solidity >= qc_params['qc_min_solidity']):
        flags.append("solidity")
    if not (is_enclosed or arc_coverage >= qc_params['qc_min_arc_coverage']):
        flags.append('open_shell')
    return len(flags) == 0, ','.join(flags)

# =========================
# DEFINE FUNCTION: touchesZBoundary
# =========================
def touchesZBoundary(component_properties, volume_shape) -> bool:
    '''
    If a component's bounding box reaches the Z boundary, it may be truncated by the reconstruction box.
    '''
    z_min, z_max = component_properties.bbox[0], component_properties.bbox[3]
    return z_min == 0 or z_max == volume_shape[0]
