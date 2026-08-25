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
# Import EValuator utilities
# ====================
from evaluator.utils.settings import lg

# ====================
# Define constants
# ====================
_BBOX_PAD_VOX = 2   # padding (voxels) added around each vesicle's bounding box

# ====================
# Define helper functions
# ====================
# _bounding_box: compute a padded, volume-clipped axis-aligned bounding box (as half-open [lo, hi) index ranges per axis) around a fitted vesicle; returns None if the geometry is non-finite or the box doesn't intersect the volume
def _bounding_box(
    shape: tuple[int, int, int],
    centre_vox: np.ndarray,
    radius_vox: float | None,
    radii_vox: np.ndarray | None,
    orientation: np.ndarray | None,
    pad: int = _BBOX_PAD_VOX,
) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
    centre = np.asarray(centre_vox, dtype=float)
    if radii_vox is None or orientation is None:
        # Sphere: same half-width in every direction
        half_widths = np.full(3, float(radius_vox))
    else:
        # Ellipsoid: axis-aligned bounding box of a rotated ellipsoid (half-width along global axis i is sqrt(sum_k (orientation[i,k] * radii_vox[k])^2).)
        half_widths = np.sqrt((np.asarray(orientation, dtype=float) ** 2) @ (np.asarray(radii_vox, dtype=float) ** 2))
    if not np.all(np.isfinite(centre)) or not np.all(np.isfinite(half_widths)):
        return None
    shape_arr = np.asarray(shape)
    lo = np.floor(centre - half_widths - pad).astype(int)
    hi = np.ceil(centre + half_widths + pad).astype(int) + 1   # exclusive upper bound
    lo = np.clip(lo, 0, shape_arr)
    hi = np.clip(hi, 0, shape_arr)
    if np.any(hi <= lo):
        # Bounding box doesn't intersect the volume at all
        return None
    return tuple(int(v) for v in lo), tuple(int(v) for v in hi)

# _rasterise_fitted_vesicle: returns the bounding-box index range and a boolean mask of the given shape, marking voxels inside the fitted sphere/ellipsoid; returns None if the vesicle's geometry has no valid intersection with the volume
def _rasterise_fitted_vesicle(
    shape: tuple[int, int, int],
    centre_vox: np.ndarray,
    radius_vox: float | None,
    radii_vox: np.ndarray | None,
    orientation: np.ndarray | None,
) -> tuple[tuple[int, int, int], tuple[int, int, int], np.ndarray] | None:
    bbox = _bounding_box(shape, centre_vox, radius_vox, radii_vox, orientation)
    if bbox is None:
        return None
    (z0, y0, x0), (z1, y1, x1) = bbox
    zz, yy, xx = np.meshgrid(
        np.arange(z0, z1), np.arange(y0, y1), np.arange(x0, x1), indexing='ij'
    )
    coords = np.stack([zz, yy, xx], axis=-1).astype(float)   # (dz, dy, dx, 3), local to the box
    if radii_vox is None or orientation is None:
        # If no radii/orientation: is sphere
        dist = np.linalg.norm(coords - centre_vox, axis=-1)
        local_mask = dist <= radius_vox
    else:
        # Otherwise: is ellipsoid case:
        local = (coords - centre_vox) @ orientation
        norm_dist = np.sqrt(np.sum((local / radii_vox) ** 2, axis=-1))
        local_mask = norm_dist <= 1.0
    return (z0, y0, x0), (z1, y1, x1), local_mask

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
        result = _rasterise_fitted_vesicle(shape, centre_vox, radius_vox, radii_vox, record['orientation'])
        if result is None:
            lg.warning(f"model | Label {record['label_id']} | Fitted geometry has no valid intersection with the volume (non-finite or entirely out of bounds); skipped in fitted MRC")
            continue
        (z0, y0, x0), (z1, y1, x1), local_mask = result
        volume[z0:z1, y0:y1, x0:x1][local_mask] = record['label_id']
    return volume
