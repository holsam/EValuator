'''
=======================================
EValuator: SEGMENTATION ANALYSIS PIPELINE
=======================================
'''
# ====================
# Import external dependencies
# ====================
import datetime, numpy, pandas, typer
from pathlib import Path
from rich import print
from scipy import ndimage
from skimage import measure
from skimage.morphology import ball
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm


# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import config, lg
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil

# ====================
# Define command: analyse
# ====================
def run_pipeline(
    input,
    output,
    mindiam,
    maxdiam,
    fillthreshold,
):
    global minimum_diameter
    minimum_diameter = mindiam
    global maximum_diameter
    maximum_diameter = maxdiam
    global fill_threshold
    fill_threshold = fillthreshold
    # Validate input file(s)
    lg.debug(f"analyse | Validating input file(s)...")
    seg_files = analyseCheckInput(input)
    # Create output directory structure
    lg.debug(f"analyse | Creating output directory structure...")
    out_dir = pathutil.generateOutputFileStructure(output, "analyse")
    # Define output file path
    lg.debug(f"analyse | Defining output file...")
    out_file = pathutil.checkUniqueFileName(out_dir, "analyse")
    # Print number of files to analyse
    print(f"{len(seg_files)} segmentation files found") if not len(seg_files) == 1 else print(f"1 segmentation file found")
    # Record and print start time
    START_TIME = datetime.datetime.now()
    print(f"\nEV post-processing pipeline started: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    # Run pipeline
    analyse_results = []
    lg.debug(f"analyse | Starting pipeline...")
    with logging_redirect_tqdm():
        for segfile in tqdm(seg_files, desc="Segmentation files processed"):
            try:
                segfile_results = processSegmentation(segfile)
                analyse_results.extend(segfile_results)
            except Exception as e:
                lg.warning(f"Failed to process {segfile.name}: {e}")
                continue
    END_TIME = datetime.datetime.now()
    print(f"EV analysis pipeline finished: {END_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    if not analyse_results:
        lg.warning(f"No EVs detected across all segmentation files.")
        lg.warning(f"Nothing saved to {out_file}.")
        return
    lg.debug(f"analyse | Saving output CSV ({out_file.name})...")
    analyse_df = saveResultsCSV(analyse_results, out_file)
    lg.debug(f"analyse | Printing summary message...")
    printSummaryMessage(results=analyse_df, nfiles=len(seg_files), startt=START_TIME, endt=END_TIME, out_path=out_file)

# =========================
# DEFINE FUNCTION: processSegmentation
# =========================
def processSegmentation(seg_path: Path):
    '''
    Process a given labelled segmentation file by calling the component processing
    function for each component.
    '''
    lg.info(f"analyse | {seg_path.name} | Started processing segmentation file.")
    lg.debug(f"analyse | {seg_path.name} | Reading file...")
    data, voxel_size_nm = mrcutil.readMRCFile(seg_path)
    # Support both binary segmentations and pre-labelled MRC files from `label`
    if len(numpy.unique(data)) <= 2:
        # Binary: label on the fly
        lg.debug(f"analyse | {seg_path.name} | Binary volume detected — labelling components...")
        data = data.astype(bool)
        components, n_components = mrcutil.labelComponents(data)
    else:
        # Already labelled
        lg.debug(f"analyse | {seg_path.name} | Pre-labelled volume detected — using existing labels...")
        components = data.astype(numpy.int32)
        n_components = int(components.max())
    if n_components == 0:
        lg.warning(f"analyse | {seg_path.name} | No components identified - skipping file.")
        return []
    lg.info(f"analyse | {seg_path.name} | {n_components} components identified for analysis.")
    lg.debug(f"analyse | {seg_path.name} | Measuring component properties...")
    component_list = measure.regionprops(components)
    lg.debug(f"analyse | {seg_path.name} | Calculating voxel size limits...")
    membrane_thickness_vox = config['filter']['membrane_thickness_nm'] / voxel_size_nm if voxel_size_nm else 1.0
    if voxel_size_nm is not None:
        min_vox = shellVolume(minimum_diameter, voxel_size_nm, membrane_thickness_vox)
        max_vox = shellVolume(maximum_diameter, voxel_size_nm, membrane_thickness_vox)
    else:
        min_vox = 0
        max_vox = numpy.inf
    file_results = []
    lg.debug(f"analyse | {seg_path.name} | Starting component processing...")
    with logging_redirect_tqdm():
        for component in tqdm(component_list, desc="Components processed"):
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Checking voxel count filter...")
            if not (min_vox <= component.area <= max_vox):
                lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Voxel count {component.area} outside filter ({min_vox}≤c≤{max_vox}) — skipping.")
                continue
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Checking extent filter...")
            if component.extent < 0.01:
                lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Extent {component.extent} outside filter (e<0.01) — skipping.")
                continue
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Measuring component features...")
            component_data = processComponent(component.label, components, component, voxel_size_nm, seg_path.name)
            if component_data is None:
                lg.warning(f"analyse | {seg_path.name} | Component {component.label} | Component processing failed — skipping.")
                continue
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Finished processing.")
            file_results.append(component_data)
    lg.debug(f"analyse | {seg_path.name} | Component processing finished.")
    lg.info(f"analyse | {seg_path.name} | Finished processing segmentation file.")
    return file_results

# =========================
# DEFINE FUNCTION: processComponent
# =========================
def processComponent(component_label, labelled_volumes, component_properties, voxel_size_nm, filename):
    '''
    For a given component, make all defined measurements and return as a dictionary.
    '''
    lg.debug(f"analyse | {filename} | Component {component_label} | Setting scale...")
    scale = voxel_size_nm if voxel_size_nm is not None else 1.0
    scale_label = "nm" if voxel_size_nm is not None else "vox"
    lg.debug(f"analyse | {filename} | Component {component_label} | Creating component mask...")
    component_mask = createComponentMask(component=component_properties, labelled_vol=labelled_volumes, label_val=component_label)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring membrane volume and equivalent diameter...")
    membrane_vol_nm3, equiv_diameter_nm = measureMembraneVolumeDiameter(component=component_properties, scale=scale)
    component_mask_dilated = morphologicalDilation(component_mask)
    lg.debug(f"analyse | {filename} | Component {component_label} | Checking if component is enclosed...")
    enclosed, fill_ratio = checkEnclosed(component_mask=component_mask_dilated, threshold=fill_threshold)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring lumen volume...")
    lumen_vol_nm3 = measureLumenVolume(component_mask=component_mask, scale=scale)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring surface area...")
    surface_area = computeSurfaceArea(component_mask, voxel_size_nm)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring major/minor axes diameters...")
    major_axis_diameter, minor_axis_diameter = measureAxes(component=component_properties, equiv_diameter_nm=equiv_diameter_nm)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring eccentricity and aspect ratio...")
    eccentricity, aspect_ratio = measureEccentricityAspectRatio(major_axis_diameter=major_axis_diameter, minor_axis_diameter=minor_axis_diameter)
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
        "surface_area": round(surface_area, 2) if not numpy.isnan(surface_area) else numpy.nan,
        "is_enclosed": enclosed,
        "closure_fill_ratio": round(fill_ratio, 4),
        "voxel_size_nm": round(scale, 4) if voxel_size_nm is not None else None,
        "measurement_units": scale_label,
    }

# =========================
# DEFINE FUNCTION: analyseCheckInput
# =========================
def analyseCheckInput(analyse_input: Path):
    '''
    Given the entered input, check which file(s) are valid MRC files to process.
    '''
    if analyse_input.is_file():
        check_files = [analyse_input]
    if analyse_input.is_dir():
        check_files = sorted(analyse_input.glob("*.mrc"))
    for file in list(check_files):
        if not mrcutil.validateMRCFile(file):
            lg.warning(f"{file} is not a valid MRC file and will not be processed.")
            check_files.remove(file)
    if not check_files:
        lg.error(f"No valid MRC files found in input: {analyse_input}.")
    return check_files

# =========================
# DEFINE FUNCTION: morphologicalClosure
# =========================
def morphologicalClosure(binary_vol: numpy.ndarray):
    '''
    Applies morphological closing (dilation then erosion) using a minimal 6-connectivity structuring element.
    Removes small isolated protrusions while preserving the overall shell structure.
    '''
    struc = ndimage.generate_binary_structure(3, 1)
    return ndimage.binary_closing(binary_vol, structure=struc, border_value=False)

# =========================
# DEFINE FUNCTION: morphologicalDilation
# =========================
def morphologicalDilation(binary_vol: numpy.ndarray):
    '''
    Applies morphological dilation to bridge small gaps in thin membrane shells. 
    Use over morphologicalClosure to as erosion can remove gap-filling voxels added by dilation.
    '''
    return ndimage.binary_dilation(binary_vol, structure=ball(2))

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

# =========================
# DEFINE FUNCTION: computeSurfaceArea
# =========================
def computeSurfaceArea(component_mask: numpy.ndarray, voxel_size_nm: float):
    '''
    Estimates surface area using the marching cubes algorithm.
    Returns nm^2 if voxel size is known, otherwise vox^2.
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
# DEFINE FUNCTION: deriveAxes
# =========================
def deriveAxes(intertia_tensor, voxel_size_nm=None):
    '''
    Derive semi-axes (a ≥ b ≥ c) of the best-fit ellipsoid from inertia tensor eigenvalues.
    eigvalsh returns eigenvalues in ascending order (I_a ≤ I_b ≤ I_c).
    '''
    eigvals = numpy.linalg.eigvalsh(intertia_tensor)
    eigvals = numpy.clip(eigvals, 0, None)
    with numpy.errstate(divide="ignore", invalid="ignore"):
        inv_sqrt = numpy.where(eigvals > 0, 1.0 / numpy.sqrt(eigvals), 0.0)
    return inv_sqrt

# =========================
# DEFINE FUNCTION: measureMembraneVolumeDiameter
# =========================
def measureMembraneVolumeDiameter(component, scale):
    '''
    Measures the volume of membrane components in voxels and converts to nm^3.
    Calculates the equivalent spherical diameter in nm.
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
# DEFINE FUNCTION: measureAxes
# =========================
def measureAxes(component, equiv_diameter_nm):
    '''
    Measure major and minor axes by approximating the EV as an ellipsoid.
    Semi-axes are derived from inertia tensor eigenvalues and scaled to
    real-world size using the equivalent diameter.
    '''
    inv_sqrt_axes = deriveAxes(intertia_tensor=component.inertia_tensor)
    geomean_inv_sqrt = (inv_sqrt_axes[0] * inv_sqrt_axes[1] * inv_sqrt_axes[2]) ** (1 / 3)
    if geomean_inv_sqrt > 0:
        axis_scale = (equiv_diameter_nm / 2.0) / geomean_inv_sqrt
    principal_semiaxis_a, principal_semiaxis_b, principal_semiaxis_c = inv_sqrt_axes * axis_scale
    major_axis = 2 * principal_semiaxis_a
    minor_axis = 2 * principal_semiaxis_c
    return major_axis, minor_axis

# =========================
# DEFINE FUNCTION: measureEccentricityAspectRatio
# =========================
def measureEccentricityAspectRatio(major_axis_diameter, minor_axis_diameter):
    '''
    Given major and minor diameters, calculate eccentricity and aspect ratio.
    Eccentricity: 0 (spherical) → 1 (tubular).
    '''
    semimajor = major_axis_diameter / 2
    semiminor = minor_axis_diameter / 2
    eccentricity = numpy.sqrt(1 - (semiminor / semimajor) ** 2) if semimajor > 0 else numpy.nan
    aspect_ratio = major_axis_diameter / minor_axis_diameter if minor_axis_diameter > 0 else numpy.nan
    return eccentricity, aspect_ratio

# =========================
# DEFINE FUNCTION: saveResultsCSV
# =========================
def saveResultsCSV(analyse_results, out_path: Path):
    '''
    Convert list of result dictionaries to a pandas DataFrame and save to CSV.
    '''
    analyse_df = pandas.DataFrame(analyse_results)
    analyse_df.to_csv(out_path, index=False)
    lg.info(f"Analyse results saved to: {out_path}")
    return analyse_df

# =========================
# DEFINE FUNCTION: printSummaryMessage
# =========================
def printSummaryMessage(results, nfiles: int, startt: datetime.datetime, endt: datetime.datetime, out_path: Path):
    RUNTIME = endt - startt
    print(f"\n[bold]Pipeline run summary[/bold]")
    print(f"- Runtime: {RUNTIME}")
    print(f"- Segmentation files processed: {nfiles}")
    print(f"- Segmentation files with EVs: {results['tomogram'].nunique()} ({(100 * results['tomogram'].nunique()) / nfiles:.1f}%)")
    print(f"- EVs processed: {len(results)}")
    print(f"- Number of enclosed EVs: {results['is_enclosed'].sum()} ({100 * results['is_enclosed'].mean():.1f}%)")
    print(f"- Equivalent diameters: {results['equiv_diameter_nm'].mean():.1f} ± {results['equiv_diameter_nm'].std():.1f} nm (mean ± SD)")
    print(f"Results saved to: {out_path}\n")

# =========================
# DEFINE FUNCTION: shellVolume
# =========================
def shellVolume(diameter_nm, voxel_size_nm, thickness_vox):
    '''
    Calculate the expected voxel count of a hollow spherical shell,
    used for the voxel-count size filter.
    '''
    r_outer = diameter_nm / (2 * voxel_size_nm)
    r_inner = max(0, r_outer - thickness_vox)
    return (4 / 3) * numpy.pi * (r_outer ** 3 - r_inner ** 3)