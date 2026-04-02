'''
=======================================
EValuator: SEGMENTATION ANALYSIS PIPELINE
=======================================
'''
# ====================
# Import dependencies
# ====================
import datetime, numpy, pandas, typer
from pathlib import Path
from rich import print
from scipy import ndimage
from skimage import measure
from skimage.morphology import ball
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from typing import Annotated

# ====================
# Import EValuator functions and variables
# ====================
from ..main import config, lg
from .. import utils as evalutil

# ====================
# Initialise typer as evaluatorAnalyse
# ====================
evaluatorAnalyse = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False
)

# ====================
# Define command: analyse
# ====================
@evaluatorAnalyse.command(rich_help_panel="Commands")
def analyse(
    # --------------------
    # Define CLI arguments
    # --------------------
    # Define input argument: should be a path which exists and is readable, and can be a file or directory 
    input: Annotated[
        Path, 
        typer.Argument(help="Path to either a single .MRC segmentation file or a directory containing multiple .MRC segmentation files.", exists=True,file_okay=True,dir_okay=True,readable=True)
    ],
    # --------------------
    # Define CLI options
    # --------------------
    # Define output option: should be a path which can not exist or is a writeable directory if it exists, and defaults to current working directory
    output: Annotated[
        Path | None, 
        typer.Option("-o", "--out-dir", help="Path to output directory. Output files will be written to this directory under '.../evaluator/results/analyse/'.", file_okay=False,dir_okay=True,writable=True)
    ] = Path("."),
    # Define mindiam option: should be a float which is greater than 0, and defaults to the 'min_diameter_nm' value specified in config.toml
    mindiam: Annotated[
        float,
        typer.Option("--min-diam", help="Minimum EV equivalent diameter in nm to use for filtering.", min=0)
    ] = config['filter']['min_diameter_nm'],
    # Define maxdiam option: should be a float which is greater than 0, and defaults to the 'max_diameter_nm' value specified in config.toml
    maxdiam: Annotated[
        float,
        typer.Option("--max-diam", help="Maximum EV equivalent diameter in nm to use for filtering.", min=0)
    ] = config['filter']['max_diameter_nm'],
    # Define fillthreshold option: should be a float which is greater than 0, and defaults to the 'closure_fill_threshold' value specified in config.toml
    fillthreshold: Annotated[
        float,
        typer.Option("--fill-threshold", help="Closure fill threshold to use for determining enclosed EVs.", min=0.0, max=1.0)
    ] = config['filter']['closure_fill_threshold'],
):
    # Set help text for 'analyse' command using docstring
    '''
    Run post-processing pipeline on MemBrain-seg EV segmentation files.
    '''
    # Set option values
    global minimum_diameter
    minimum_diameter = mindiam
    global maximum_diameter
    maximum_diameter = maxdiam
    global fill_threshold
    fill_threshold = fillthreshold
    # Check input files are ok
    lg.debug(f"analyse | Validating input file(s)...")
    seg_files = analyseCheckInput(input)
    # Create output directory structure
    lg.debug(f"analyse | Creating output directory structure...")
    out_dir = evalutil.generateOutputFileStructure(output, "analyse")
    # Define output file path
    lg.debug(f"analyse | Defining output file...")
    out_file = evalutil.checkUniqueFileName(out_dir, "analyse")
    # Print number of files to analyse
    print(f"{len(seg_files)} segmentation files found") if not len(seg_files)==1 else print(f"1 segmentation file found")
    # Define  and print start time
    START_TIME = datetime.datetime.now()
    print(f"\nEV post-processing pipeline started: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    # Set up list to hold results
    analyse_results = []
    # Run processSegmentation() for each file in seg_files using tqdm to show progress bar
    lg.debug(f"analyse | Starting pipeline...")
    with logging_redirect_tqdm():
        for segfile in tqdm(seg_files, desc="Segmentation files processed"):
            try:
                segfile_results = processSegmentation(segfile)
                analyse_results.extend(segfile_results)
            # If any exceptions arise during processing, just flag as warning
            except Exception as e:
                lg.warning(f"Failed to process {segfile.name}: {e}")
                continue
    # Define and print end time
    END_TIME = datetime.datetime.now()
    print(f"EV analysis pipeline finished: {END_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    # Check analyse_results contains some data
    if not analyse:
        lg.warning(f"No EVs detected across all segmentation files.")
        lg.warning(f"Nothing saved to {out_file}.")
        return
    # Save analyse_results as csv file
    lg.debug(f"analyse | Saving output CSV ({out_file.name})...")
    analyse_df = saveResultsCSV(analyse_results, out_file)
    # Print summary message
    lg.debug(f"analyse | Printing summary message...")
    printSummaryMessage(results=analyse_df, nfiles=len(seg_files), startt=START_TIME, endt=END_TIME, out_path=out_file)

# =========================
# DEFINE FUNCTION: processSegmentation
# =========================
def processSegmentation(seg_path: Path):
    '''
    Process a given segmentation file, by labelling components and calling the component process function for each of these.
    '''
    lg.info(f"analyse | {seg_path.name} | Started processing segmentation file.")
    # Read segmentation data and voxel size information from file
    lg.debug(f"analyse | {seg_path.name} | Reading file... ")
    data, voxel_size_nm = evalutil.readMRCFile(seg_path)
    data=data.astype(bool)
    # Label components and get number of components
    lg.debug(f"analyse | {seg_path.name} | Labelling components... ")
    components, n_components = evalutil.labelComponents(data)
    # If no components found, log warning-level message and exit pipeline
    if n_components == 0:
        lg.warning(f"analyse | {seg_path.name} | No components identified - skipping file.")
        return []
    # Otherwise log info-level message about number of components identified
    lg.info(f"analyse | {seg_path.name} | {n_components} components identified for analysis.")
    # Generate a list of region properties
    lg.debug(f"analyse | {seg_path.name} | Measuring component properties...")
    component_list = measure.regionprops(components)
    # Calculate voxel size limits (based on whether vox->nm conversion is known)
    lg.debug(f"analyse | {seg_path.name} | Calculating voxel size limits...")
    membrane_thickness_vox = config['filter']['membrane_thickness_nm'] / voxel_size_nm
    if voxel_size_nm is not None:
        min_vox = shellVolume(minimum_diameter, voxel_size_nm, membrane_thickness_vox)
        max_vox = shellVolume(maximum_diameter, voxel_size_nm, membrane_thickness_vox)
    else:
        min_vox = 0
        max_vox = numpy.inf
    # Initialise results list
    file_results = []
    lg.debug(f"analyse | {seg_path.name} | Starting component processing...")
    # Loop through each component in the list of component properties (using tqdm for progress bar and loggin_redirect_tqdm to handle logging)
    with logging_redirect_tqdm():
        for component in tqdm(component_list, desc="Components processed"):
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Checking against voxel count filter...")
            # Use a basic filter (voxel count which is computed easily) to check component isn't too large or small
            if not (min_vox <= component.area <= max_vox):
                lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Voxel count {component.area} outside of filter ({min_vox}≤c≤{max_vox}) - skipping component.")
                continue
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Checking against extent filter...")
            # Another filter to check the ratio of component voxels to bounding box volume (very permissive at this stage)
            if (component.extent < 0.01):
                lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Component extent {component.extent} outside of filter (e<0.01) - skipping component.")
                continue
            # Call processComponent to measure morphological features
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Measuring component features...")
            component_data = processComponent(component.label, components, component, voxel_size_nm, seg_path.name)
            # If processed component data is None (i.e. somethings gone wrong) - log warning-level message
            if component_data is None:
                lg.warning(f"analyse | {seg_path.name} | Component {component.label} | Component processing failed - skipping component.")
                continue
            # Append component data to list of results for the segmentation file
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Finishing processing...")
            file_results.append(component_data)
    # Return list of dictionaries with component features
    lg.debug(f"analyse | {seg_path.name} | Component processing finished.")
    lg.info(f"analyse | {seg_path.name} | Finished processing segmentation file.")
    return file_results

# =========================
# DEFINE FUNCTION: processComponent
# =========================
def processComponent(component_label, labelled_volumes, component_properties, voxel_size_nm, filename):
    '''
    For a given component, make all the defined measurements and return as a dictionary
    '''
    # Set up scale and labels based on whether voxel size in nm is known
    lg.debug(f"analyse | {filename} | Component {component_label} | Setting scale...")
    scale = voxel_size_nm if voxel_size_nm is not None else 1.0
    scale_label = "nm" if voxel_size_nm is not None else "vox"
    # Create component mask (using bounding box)Get bounding box of component and convert to ZYX ordered array, then create a mask for this
    lg.debug(f"analyse | {filename} | Component {component_label} | Creating component mask...")
    component_mask = createComponentMask(component=component_properties, labelled_vol=labelled_volumes, label_val=component_label)
    # Measurement 1: membrane volume and equivalent diameter
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring membrane volume and equivalent diameter...")
    membrane_vol_nm3, equiv_diameter_nm = measureMembraneVolumeDiameter(component=component_properties, scale=scale)
    # Apply morphological closure to remove small gaps in membrane
    component_mask_closed = morphologicalClosure(component_mask)
    # Measurement 2: check if component is enclosed
    lg.debug(f"analyse | {filename} | Component {component_label} | Checking if component is enclosed...")
    enclosed, fill_ratio = checkEnclosed(component_mask=component_mask_closed, threshold=fill_threshold)
    # Measurement 3: internal (lumen) volume
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring lumen volume...")
    lumen_vol_nm3 = measureLumenVolume(component_mask=component_mask, scale=scale)
    # Measurement 4: surface area
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring surface area...")
    surface_area = computeSurfaceArea(component_mask, voxel_size_nm)
    # Measurement 5: major/minor axes sizes, 
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring major/minor axes diameters...")
    major_axis_diameter, minor_axis_diameter = measureAxes(component=component_properties, equiv_diameter_nm=equiv_diameter_nm)
    # Measurement 6: eccentricity, aspect_ratio
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring eccentricity and aspect ratio...")
    eccentricity, aspect_ratio = measureEccentricityAspectRatio(major_axis_diameter=major_axis_diameter, minor_axis_diameter=minor_axis_diameter)
    # Return dictionary of morphological features
    return {
        "tomogram": filename,
        "label": component_label,
        "equiv_diameter_nm": round(equiv_diameter_nm, 2),
        "major_axis_diameter": round(major_axis_diameter, 2),
        "minor_axis_diameter": round(minor_axis_diameter, 2),
        "aspect_ratio": round(aspect_ratio, 2),
        "eccentricity": round(eccentricity, 2),
        "membrane_volume": round(membrane_vol_nm3, 2),
        "lumen_volume": round(lumen_vol_nm3, 2),
        "surface_area": round(surface_area, 2) if not numpy.isnan else numpy.nan,
        "is_enclosed": enclosed,
        "closure_fill_ratio": round(fill_ratio, 4),
        "voxel_size_nm": round(scale, 4) if voxel_size_nm is not None else None,
        "measurement units": scale_label,
    }

# =========================
# DEFINE FUNCTION: analyseCheckInput
# =========================
def analyseCheckInput(analyse_input:Path):
    '''
    Given the entered input, check which file(s) are valid MRC files to process.
    As typer has better argument validation than argparse, no need to check if it exists here - just whether single file or directory.
    '''
    if analyse_input.is_file():
        check_files = [analyse_input]
    if analyse_input.is_dir():
        check_files = sorted(analyse_input.glob("*.mrc"))
    for file in check_files:
        if not evalutil.validateMRCFile(file):
            lg.warning(f"{file} is not a valid MRC file and will not be processed.")
            check_files.remove(file)
        else:
            continue
    if not check_files:
        lg.error(f"No valid MRC files found in input: {analyse_input}.")
    return check_files

# =========================
# DEFINE FUNCTION: morphologicalClosure
# =========================
def morphologicalClosure(binary_vol: numpy.ndarray):
    '''
    Applies a morphological closing operation (dilation followed by erosion). This removes small dark spots and connects small bright cracks (i.e. helps fill in EV membranes which may not be segmented perfectly).
    '''
    binary_vol_closed=ndimage.binary_closing(binary_vol, structure=ball(2))
    return binary_vol_closed

# =========================
# DEFINE FUNCTION: checkEnclosed
# =========================
def checkEnclosed(component_mask: numpy.ndarray, threshold: float):
    '''
    Checks whether a membrane component forms an enclosed structure by filling in holes in the binary mask - if filled volumes are greater than original, there is an enclosed structure (i.e. EV).
    Threshold corresponds the ratio of (filled volume - original volume) / filled volume at which a shape is classified as 'enclosed'
    The fill ratio returned is the fraction of the filled volume which can be attributed to the enclosed interior
    '''
    # Pad with a border of false voxels to prevent edge leakage
    padded_mask = numpy.pad(component_mask, pad_width=1, mode='constant', constant_values=False)   
    filled_mask = ndimage.binary_fill_holes(padded_mask)
    # Remove padding before any measurements
    filled_mask = filled_mask[1:-1, 1:-1, 1:-1]
    n_original = numpy.sum(component_mask)
    n_filled = numpy.sum(filled_mask)
    if n_filled == 0:
        return False, 0.0
    fill_ratio = (n_filled - n_original) / n_filled
    closed = fill_ratio > threshold
    return closed, float(fill_ratio)

# =========================
# DEFINE FUNCTION: computeSurfaceArea
# =========================
def computeSurfaceArea(component_mask: numpy.ndarray, voxel_size_nm: float):
    '''
    Estimates surface area (in either nm^2 or vox^2 depending on if voxel size known) using marching cubes algorithm.
    '''
    try:
        verts, faces, _, _ = measure.marching_cubes(
            component_mask.astype(numpy.uint8),
            level = 0.5,
            spacing=(1.0,1.0,1.0),
        )
        sa_vox = measure.mesh_surface_area(verts, faces)
    except (ValueError, RuntimeError):
        return numpy.nan
    # Convert surface area in vox^2 to nm^2
    if voxel_size_nm is not None:
        return sa_vox * (voxel_size_nm ** 2)
    return sa_vox

# =========================
# DEFINE FUNCTION: deriveAxes
# =========================
def deriveAxes(intertia_tensor, voxel_size_nm=None):
    '''
    Derive semi-axes (i.e. a ≥ b ≥ c) of the best-fit ellipsoid from inertia tension eigenvalues: given I_c = (m/5)(a^2 + b^2), use reverse relationship to recover a, b using known eigenvalues.
    '''
    # Compute the eigenvalues of the component's intertia_tensor (resistence to rotation around three principal angles a ≥ b ≥ c)
    # eigvalsh outputs these in ascending order - i.e. I_a ≤ I_b < I_c
    eigvals = numpy.linalg.eigvalsh(intertia_tensor)
    #eigvals = numpy.sort(eigvals)[::-1] # get eigenvalues in descending order
    # Remove any negative eigenvalues
    eigvals = numpy.clip(eigvals, 0, None)
    # Calculate the inverse square roots of each eigenvalue
    with numpy.errstate(divide="ignore", invalid="ignore"):
        inv_sqrt = numpy.where(eigvals>0, 1.0/numpy.sqrt(eigvals), 0.0)
    return inv_sqrt


# =========================
# DEFINE FUNCTION: measureMembraneVolumeDiameter()
# =========================
def measureMembraneVolumeDiameter(component, scale):
    '''
    Measures the volume of membrane components in voxels and converts this to nm^3. Based on a perfect sphere, also calculates the diameter (in nm) which would give this volume (to be used in determining actual axis size).
    '''
    vol_vox = component.area #nb component.area = voxel count which is same as volume
    vol_nm3 = vol_vox * (scale ** 3)
    equiv_diameter_nm = (6 * vol_nm3 / numpy.pi) ** (1/3)
    return vol_nm3, equiv_diameter_nm

# =========================
# DEFINE FUNCTION: createComponentMask()
# =========================
def createComponentMask(component, labelled_vol, label_val):
    '''
    Get bounding box of the given component and convert to ZYX array for masking, then return mask
    '''
    # Get bounding box of component
    bbox = component.bbox
    # bbox is ordered as: min_z, min_y, min_x, max_z, max_y, max_x, so convert to ordered ZYX array
    slices = (
        slice(bbox[0], bbox[3]),
        slice(bbox[1], bbox[4]),
        slice(bbox[2], bbox[5]),
    )
    # Create component mask
    component_mask = labelled_vol[slices] == label_val
    # Return component mask
    return component_mask

# =========================
# DEFINE FUNCTION: measureLumenVolume()
# =========================
def measureLumenVolume(component_mask, scale):
    '''
    Calculate the volume (sum of voxels) of filled components in component_mask to measure the volume of EV lumen
    '''
    filled_mask = ndimage.binary_fill_holes(component_mask)
    lumen_vol_vox = numpy.sum(filled_mask) - numpy.sum(component_mask)
    lumen_vol_nm3 = lumen_vol_vox * (scale ** 3)
    return lumen_vol_nm3

# =========================
# DEFINE FUNCTION: measureAxes()
# =========================
def measureAxes(component, equiv_diameter_nm):
    '''
    Measure major and minor axes of EV by approximating as ellipsoid.
    The semi-axes are derived algebraically (using eigenvalues on inertia) and then scaled to 'real-world size' using the equivalent diameter calculated as if the EV was a perfect sphere (but adjusted to the specific ellipsoid shape).
    '''
    # Derive semi-axes
    inv_sqrt_axes = deriveAxes(intertia_tensor=component.inertia_tensor)
    # Scale semi-axes to equivalent diameter
    # NB equiv_diam_nm assumes a sphere of equal volume but for ellipsoid this is calculated as (abc)^(1/3)
    geomean_inv_sqrt = (inv_sqrt_axes[0] * inv_sqrt_axes[1] * inv_sqrt_axes[2]) ** (1/3)
    if geomean_inv_sqrt > 0:
        axis_scale = (equiv_diameter_nm / 2.0) / geomean_inv_sqrt
    principal_semiaxis_a, principal_semiaxis_b, principal_semiaxis_c = inv_sqrt_axes * axis_scale
    # Calculate axes diameters
    # NB principal_semiaxis_b is not used as a & c capture the extremes and are enough for morphological classification:
    #   for sphere: a ≈ b ≈ c
    #   for prolate ellipsoid (i.e. elongated): a > b ≈ c
    #   for oblate ellipsoid (i.e. flattened): a ≈ b > c
    major_axis = 2 * principal_semiaxis_a
    minor_axis = 2 * principal_semiaxis_c
    # Return axes diameters
    return major_axis, minor_axis

# =========================
# DEFINE FUNCTION: measureEccentricityAspectRatio()
# =========================
'''
Given a major and minor diameter, calculate the eccentricity (as a measure of the shape of the EV: (tubular) 0 ≤ e ≤ 1 (spherical)).
'''
def measureEccentricityAspectRatio(major_axis_diameter, minor_axis_diameter):
    # Calculate semi-axes diameters
    semimajor = major_axis_diameter / 2
    semiminor = minor_axis_diameter / 2
    # Calculate eccentricity
    eccentricity = numpy.sqrt(1-(semiminor/semimajor)**2) if semimajor > 0 else numpy.nan
    # Calculate aspect ratio (major/minor diameter)
    aspect_ratio = major_axis_diameter / minor_axis_diameter if minor_axis_diameter > 0 else numpy.nan
    # Return axes diameters, eccentricity and aspect_ratio
    return eccentricity, aspect_ratio

# =========================
# DEFINE FUNCTION: saveResultsCSV
# =========================
'''
Convert (list of) list of dictionaries to a single dataframe and save this to a .csv file for further analysis.
'''
def saveResultsCSV(analyse_results, out_path:Path):
    # Convert list of dictionaries to pandas dataframe
    analyse_df = pandas.DataFrame(analyse_results)
    # Save dataframe to CSV file (at given output path)
    analyse_df.to_csv(out_path, index=False)
    # Log info-level message to state saving worked
    lg.info(f"Analyse command results saved to: {out_path}")
    # Return dataframe of results
    return analyse_df

# =========================
# DEFINE FUNCTION: printSummaryMessage
# =========================
def printSummaryMessage(results, nfiles:int, startt:datetime.datetime, endt: datetime.datetime, out_path: Path):
    RUNTIME = (endt - startt)
    print(f"\n[bold]Pipeline run summary[/bold]")
    print(f"- Runtime: {RUNTIME}")
    print(f"- Segmentation files processed: {nfiles}")
    print(f"- Segmentation files with EVs: {results['tomogram'].nunique()} ({(100*results['tomogram'].nunique())/nfiles:.1f}%)")
    print(f"- EVs processed: {len(results)}")
    print(f"- Number of enclosed EVs: {results['is_enclosed'].sum()} ({100*results['is_enclosed'].mean():.1f}%)")
    print(f"- Equivalent diameters: {results['equiv_diameter_nm'].mean():.1f} ± {results['equiv_diameter_nm'].std():.1f} nm (mean ± SD)")
    print(f"Results saved to: {out_path}\n")

# =========================
# DEFINE FUNCTION: shellVolume
# =========================
def shellVolume(diameter_nm, voxel_size_nm, thickness_vox):
    r_outer = diameter_nm / (2 * voxel_size_nm)
    r_inner = max(0, r_outer - thickness_vox)
    return (4/3) * numpy.pi * (r_outer**3 - r_inner**3)
