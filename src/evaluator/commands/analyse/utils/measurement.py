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
# DEFINE FUNCTION: measureMembraneVolumeDiameter
# =========================
def measureMembraneVolumeDiameter(component, scale):
    '''
    Measures the volume of membrane components in voxels and converts to nm^3. Calculates the equivalent spherical diameter in nm.
    '''
    vol_vox = component.area
    vol_nm3 = vol_vox * (scale ** 3)
    equiv_diameter_nm = (6 * vol_nm3 / numpy.pi) ** (1 / 3)
    return vol_nm3, equiv_diameter_nm

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