'''
Utility Functions: MRC file handling
'''

# -- Import external dependencies ----------------
import mrcfile, numpy
from pathlib import Path

# -- Define validateMRCFile function -------------
def validateMRCFile(
        path: Path
        ):
    '''
    Attempt to open MRC file in permissive mode.
    Using this method instead of mrcfile.validate() as validate() is overly stringent with header issues - missing values etc will cause validate() to fail when the file is actually ok to use.
    '''
    try:
        mrcfile.open(str(path), mode="r", permissive=True)
        return True
    except Exception:
        return False

# -- Define readMRCFile function -----------------
def readMRCFile(
        path: Path
        ):
    '''
    Read an MRC file and return the data array and voxel size in nanometres. If no voxel size is encoded in header, returns None instead.
    '''
    with mrcfile.open(str(path), mode='r', permissive=True) as file:
        data = file.data.copy()
        vox_a = float(file.voxel_size.x)
    if vox_a == 0.0:
        voxel_size_nm = None
    else:
        voxel_size_nm = vox_a / 10.0
    return data, voxel_size_nm

# -- Define writeMRCFile function -----------------
def writeMRCFile(
        data: numpy.ndarray, 
        voxel_size_nm: float | None, 
        path: Path
        ):
    '''
    Write a numpy array to an MRC file. If voxel_size_nm is provided,
    encodes it in the header (converting nm back to Angstroms).
    '''
    with mrcfile.new(str(path), overwrite=True) as mrc:
        mrc.set_data(data)
        if voxel_size_nm is not None:
            vox_a = voxel_size_nm * 10.0
            mrc.voxel_size = vox_a
