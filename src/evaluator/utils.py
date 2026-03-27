'''
=======================================
EValuator: UTILITY FUNCTIONS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import mrcfile, numpy, tomllib
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir
from rich import print
from scipy import ndimage
from typing import Optional

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

# =========================
# DEFINE FUNCTION: generateOutputFileStructure
# =========================
def generateOutputFileStructure(out_dir: Path, command: str):
    # Create expected EValuator output directory structure given command
    exp_stru = ''.join(["evaluator/results/",command])
    # Check if user entered expected EValuator output directory structure
    if not out_dir.match(exp_stru):
        # If not, create Path to final output directory
        out_struc = Path(out_dir, exp_stru)
        # Create final output directory structure (including any parent directories as required)
        out_struc.mkdir(parents=True, exist_ok=True)
        # Return output directory structure
        return out_struc
    else:
        # If supplied expected structure, just return the input
        return out_dir

# =========================
# DEFINE FUNCTION: checkUniqueFileName
# =========================
def checkUniqueFileName(out_dir: Path, command: str, orig_name: Optional[str] = "", overlay_style: Optional[str] = "", fmt: Optional[str] = "", vis_out: Optional[str] = ""):
    naming_patterns = {
        "analyse": "evaluator-analyse_results",
        "label":''.join([orig_name,"_overlay-",overlay_style]),
        "visualise":''.join([orig_name,"_",vis_out])
    }
    out_fmt = {
        "analyse": ".csv",
        "label":''.join([".",fmt]),
        "visualise":''.join([".",fmt])
    }
    # Create starting file name
    out_filepath = Path(out_dir, ''.join([naming_patterns[command],out_fmt[command]]))
    # Check if start_name exists
    if out_filepath.exists():
        # Set up counter
        file_counter = 1
        # Add counter to filename and check if exists, incrementing counter if so until no file found
        while True:
            out_filepath = Path(out_dir, ''.join([naming_patterns[command],"-",str(file_counter),out_fmt[command]]))
            if out_filepath.exists():
                file_counter+=1
            else:
                break
    return out_filepath


# ====================
# Define function: userConfigPath
# ====================
def userConfigPath() -> Path:
    '''
    Returns the file path <OS config directory>/evaluator/config.toml depending on the OS of running environment:
        Linux/macOS : ~/.config/evaluator/config.toml
        Windows     : %APPDATA%\\evaluator\\config.toml
    '''
    return Path(user_config_dir("evaluator"), "config.toml")

# ====================
# Define function: loadDefaultConfig
# ====================
def loadDefaultConfig() -> dict:
    '''
    Load the bundled default config.toml from the installed package.
    '''    
    with pkg_files('evaluator').joinpath('config.toml').open('rb') as defaultconfig:
        return tomllib.load(defaultconfig)
