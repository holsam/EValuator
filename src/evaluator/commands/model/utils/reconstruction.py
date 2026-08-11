'''
=======================================
EValuator: FITTED VESICLE RECONSTRUCTION UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np

# ====================
# Define helper functions
# ====================
# _rasterise_fitted_vesicle: returns a boolean mask of the given shape, marking voxels inside fitted sphere/ellipsoid
def _rasterise_fitted_vesicle(
    shape: tuple[int, int, int],
    centre_vox: np.ndarray,
    radius_vox: float | None,
    radii_vox: np.ndarray | None,
    orientation: np.ndarray | None,
    label_value: int,
) -> np.ndarray:
    zz, yy, xx = np.meshgrid(
        np.arange(shape[0]), np.arange(shape[1]), np.arange(shape[2]), indexing='ij'
    )
    coords = np.stack([zz, yy, xx], axis=-1).astype(float)   # (Z, Y, X, 3)
    if radii_vox is None or orientation is None:
        # If no radii/orientation: is sphere
        dist = np.linalg.norm(coords - centre_vox, axis=-1)
        mask = dist <= radius_vox
    else:
        # Otherwise: is ellipsoid case:
        local = (coords - centre_vox) @ orientation
        norm_dist = np.sqrt(np.sum((local / radii_vox) ** 2, axis=-1))
        mask = norm_dist <= 1.0
    return mask

# ====================
# Define functions
# ====================
# build_fitted_mrc: construct a full labelled volume from a list of fit_vesicle output dictionaries, each labelled with the same label as original vesicle
def build_fitted_mrc(
    shape: tuple[int, int, int],
    fit_records: list[dict],
    voxel_size_nm: float,
    include_unreliable: bool = False,
) -> np.ndarray:
    volume = np.zeros(shape, dtype=np.uint16)
    for record in fit_records:
        if not include_unreliable and not record['reliability']['is_reliable']:
            continue
        centre_vox = np.asarray(record['centre']) / voxel_size_nm
        radius_vox = record['radius'] / voxel_size_nm if record['radius'] else None
        radii_vox = (
            np.asarray(record['radii']) / voxel_size_nm if record['radii'] is not None else None
        )
        mask = _rasterise_fitted_vesicle(
            shape, centre_vox, radius_vox, radii_vox, record['orientation'], record['label_id']
        )
        volume[mask] = record['label_id']
    return volume