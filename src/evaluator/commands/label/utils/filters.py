'''
=======================================
EValuator: LABEL COMPONENT FILTERING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy
from skimage import measure

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import lg
from evaluator.commands.analyse.utils import geometry

# =========================
# DEFINE FUNCTION: filterComponentsBySize
# =========================
def filterComponentsBySize(
    labelled_volume: numpy.ndarray,
    voxel_size_nm: float | None,
    minimum_diameter_nm: float,
    maximum_diameter_nm: float,
    membrane_thickness_nm: float,
) -> numpy.ndarray:
    '''
    Remove components where voxel count outside of expected shell volume or bounding-box extent ratio is below 0.01
    '''
    filtered = labelled_volume.copy()
    if voxel_size_nm is not None:
        membrane_thickness_vox = membrane_thickness_nm / voxel_size_nm
        min_vox = geometry.shellVolume(minimum_diameter_nm, voxel_size_nm, membrane_thickness_vox)
        max_vox = geometry.shellVolume(maximum_diameter_nm, voxel_size_nm, membrane_thickness_vox)
    else:
        min_vox, max_vox = 0, numpy.inf
    lg.debug(f"label | {seg_path.name} | Calculated voxel size limits: min_vox={min_vox}; max_vox={max_vox}{'' if voxel_size_nm is None else f'; membrane_thickness_vox={membrane_thickness_vox}'}")
    for component in measure.regionprops(filtered):
        if not (min_vox <= component.area <= max_vox):
            lg.debug(f"label | Component {component.label} | Voxel count {component.area} outside filter ({min_vox}<=c<={max_vox}) — excluding.")
            filtered[filtered == component.label] = 0
            continue
        if component.extent < 0.01:
            lg.debug(f"label | Component {component.label} | Extent {component.extent} outside filter (e<0.01) — excluding.")
            filtered[filtered == component.label] = 0
    return filtered