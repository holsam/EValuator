'''
=======================================
EValuator: MRC FILE UTILITIES
=======================================
Functions for reading, writing, validating, and labelling MRC volumes.
'''

# ====================
# Import external dependencies
# ====================
import mrcfile, numpy
from pathlib import Path
from scipy import ndimage

# ====================
# Import internal dependencies
# ====================
from .settings import lg

# ====================
# Define function: validateMRCFile
# ====================
def validateMRCFile(path: Path) -> bool:
    '''
    Attempt to open an MRC file in permissive mode.
    Uses permissive mode rather than mrcfile.validate() to avoid false
    negatives from minor header issues that do not affect usability.
    '''
    try:
        mrcfile.open(str(path), mode="r", permissive=True)
        return True
    except Exception:
        return False

# ====================
# Define function: readMRCFile
# ====================
def readMRCFile(path: Path):
    '''
    Read an MRC file and return the data array and voxel size in nanometres.
    If no voxel size is encoded in the header, returns None for voxel_size_nm.
    '''
    with mrcfile.open(str(path), mode='r', permissive=True) as file:
        data = file.data.copy()
        vox_x, vox_y, vox_z = float(file.voxel_size.x), float(file.voxel_size.y), float(file.voxel_size.z)
    if any(v == 0 for v in [vox_x, vox_y, vox_z]):
        lg.warning(f"{path.name}: voxel size not found in MRC header. Physical measurement units will be voxels.")
        voxel_size_nm = None
    else:
        # Check for anisotropy
        if vox_y and abs(vox_y - vox_x) / vox_x > 0.01:
            lg.warning(f"{path.name}: anisotropic voxel sizes found (x={vox_x}, y={vox_y} Å). Measurements assume isotropic voxels so will be biased along y.")
        if vox_z and abs(vox_z - vox_x) / vox_x > 0.01:
            lg.warning(f"{path.name}: anisotropic voxel sizes found (x={vox_x}, z={vox_z} Å). Measurements assume isotropic voxels so will be biased along z.")
        voxel_size_nm = vox_x / 10.0
    return data, voxel_size_nm

# ====================
# Define function: writeMRCFile
# ====================
def writeMRCFile(data: numpy.ndarray, voxel_size_nm: float | None, path: Path):
    '''
    Write a numpy array to an MRC file.
    If voxel_size_nm is provided, encodes it in the header (converting nm back to Angstroms).
    '''
    with mrcfile.new(str(path), overwrite=True) as mrc:
        mrc.set_data(data)
        if voxel_size_nm is not None:
            vox_a = voxel_size_nm * 10.0
            mrc.voxel_size = vox_a

# ====================
# Define function: labelComponents
# ====================
def labelComponents(binary_vol: numpy.ndarray):
    '''
    Labels connected components in a binary volume using face-only (6-connectivity) 3D connectivity.
    Returns the labelled volume and the number of components found.
    '''
    struc = ndimage.generate_binary_structure(3, 1)
    components, n_components = ndimage.label(binary_vol, structure=struc)
    return components, n_components