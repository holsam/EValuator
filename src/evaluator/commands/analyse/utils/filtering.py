'''
=======================================
EValuator: FILTERING ANALYSIS UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy
from scipy import ndimage
from skimage.morphology import ball

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import lg
from evaluator.utils import mrc as mrcutil

# =========================
# DEFINE FUNCTION: morphologicalDilation
# =========================
def morphologicalDilation(binary_vol: numpy.ndarray):
    '''
    Applies morphological dilation to bridge small gaps in thin membrane shells.
    Use over morphologicalClosure to as erosion can remove gap-filling voxels added by dilation.
    To avoid outward asymmetric clipping from bounding-box input mask, pad volume by structuring element's radius then crop back to original shape.
    '''
    pad = 2
    padded = numpy.pad(binary_vol, pad_width=pad, mode='constant', constant_values=False)
    dilated = ndimage.binary_dilation(padded, structure=ball(2))
    return dilated[pad:-pad, pad:-pad, pad:-pad]

# =========================
# DEFINE FUNCTION: checkEnclosed
# =========================
def checkEnclosed(component_mask: numpy.ndarray, threshold: float):
    '''
    Checks whether a membrane component forms an enclosed structure by filling holes.
    Returns (is_enclosed, fill_ratio), where fill_ratio is the fraction of the filled
    volume attributable to the enclosed interior.
    '''
    padded_mask = numpy.pad(component_mask, pad_width=1, mode='constant', constant_values=False)
    filled_mask = ndimage.binary_fill_holes(padded_mask)
    filled_mask = filled_mask[1:-1, 1:-1, 1:-1]
    n_original = numpy.sum(component_mask)
    n_filled = numpy.sum(filled_mask)
    if n_filled == 0:
        return False, 0.0
    fill_ratio = (n_filled - n_original) / n_filled
    closed = bool(fill_ratio > threshold)
    return closed, float(fill_ratio)