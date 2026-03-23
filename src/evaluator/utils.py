'''
=======================================
EValuator: UTILITY FUNCTIONS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import logging, mrcfile, numpy, sys
from pathlib import Path
from rich import print
from scipy import ndimage

# ====================
# Import internal dependencies
# ====================
from .main import lg

# ====================
# Define function: initEvaluator
# ====================
def initEvaluator():
    # Print top-level splash
    print(f"\n[bold]EValuator[/bold] :microscope-text:")
    print(f"A command line tool for automated morphological analysis and visualisation of extracellular vesicles (EVs) from cryo-electron tomography (cryo-ET) data.")

# ====================
# Define function: validateMRCFile
# ====================
def validateMRCFile(path: Path):
    '''
    Use mrcfile package's built-in validate function to confirm file can be read.
    '''
    if not mrcfile.validate(path):
        lg.warning(f"{path.name} is not a valid MRC file - skipping.")
        return False
    else:
        return True

# ====================
# Define function: readMRCFile
# ====================
def readMRCFile(path: Path):
    '''
    Read an MRC file and return the data array and voxel size in nanometres. If no voxel size is encoded in header, returns None instead.
    '''
    with mrcfile.open(str(path), mode='r', permissive=True) as file:
        data = file.data.copy()
        vox_a = float(file.voxel_size.x)
    if vox_a == 0.0:
        lg.warning(f"{path.name}: voxel size not found in MRC header. Physical measurement units will be voxels.")
        voxel_size_nm = None
    else:
        voxel_size_nm = vox_a / 10.0
    return data, voxel_size_nm


# ====================
# Define function: labelComponents
# ====================
def labelComponents(binary_vol: numpy.ndarray):
    '''
    Labels connected components in binary volumes using full 3D (26) connectivity 
    '''
    struc = ndimage.generate_binary_structure(3, 3)
    components, n_components = ndimage.label(binary_vol, structure=struc)
    return components, n_components

# =========================
# DEFINE FUNCTION: normaliseArray
# =========================
def normaliseArray(data: numpy.ndarray) -> numpy.ndarray:
    '''
    Linearly normalises a 2D array to [0.0, 1.0] for greyscale display. Clips to 1st/99th percentile to avoid outlier-driven contrast collapse. Returns a zero array if the slice is constant to avoiding division by zero error.
    '''
    # Convert to float
    data = data.astype(float)
    # Calculate 1st percentile
    lo = numpy.percentile(data, 1)
    # Calculate 99th percentile
    hi = numpy.percentile(data, 99)
    # Check if array is constant
    if hi == lo:
        return numpy.zeros_like(data)
    return numpy.clip((data-lo)/(hi-lo), 0.0, 1.0)