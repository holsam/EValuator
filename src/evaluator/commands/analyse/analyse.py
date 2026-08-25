'''
=======================================
EValuator: SEGMENTATION ANALYSIS
=======================================
'''
# ====================
# Import external dependencies
# ====================
import datetime, numpy
from functools import partial
from pathlib import Path
from rich import print
from skimage import measure
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# ====================
# Import shared EValuator utilities
# ====================
from evaluator.utils import batch as batchutil
from evaluator.utils import config as confutil
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil
from evaluator.utils.settings import lg

# ====================
# Import EValuator analyse utilities
# ====================
from evaluator.commands.analyse.utils import filtering, geometry, io, measurement

# ====================
# Define command: analyse
# ====================
def analyse(
    input,
    output,
    **overrides,
):
    # Load configuration file
    lg.debug(f"analyse | Loading configuration file...")
    config, evaluator_dir = confutil.load_config(output)
    # If CLI overrides provided:
    lg.debug(f"analyse | Setting run parameters...")
    updates = {k: v for k, v in overrides.items() if v is not None}
    params = config.analyse.model_copy(update=updates)
    # Validate input file(s)
    lg.debug(f"analyse | Validating input file(s)...")
    seg_files = batchutil.resolve_mrc_inputs(input)
    # Create output directory structure
    lg.debug(f"analyse | Creating output directory structure...")
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, "analyse")
    confutil.write_params(params, out_dir)
    # Define output file path
    lg.debug(f"analyse | Defining output file...")
    out_file = pathutil.checkUniqueFileName(out_dir, "analyse")
    # Print number of files to analyse
    print(f"{len(seg_files)} segmentation files found") if not len(seg_files) == 1 else print(f"1 segmentation file found")
    # Record and print start time
    START_TIME = datetime.datetime.now()
    print(f"\nEV post-processing pipeline started: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    # Run pipeline
    lg.debug(f"analyse | Starting pipeline...")
    worker = partial(
        processSegmentation,
        fill_threshold=params.fill_threshold,
    )
    per_file_results = batchutil.run_batch(seg_files, worker=worker, desc="Segmentation files processed", max_workers=params.max_workers)
    analyse_results = [row for file_results in per_file_results for row in file_results]
    END_TIME = datetime.datetime.now()
    print(f"EV analysis pipeline finished: {END_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    if not analyse_results:
        lg.warning(f"No EVs detected across all segmentation files.")
        lg.warning(f"Nothing saved to {out_file}.")
        return
    lg.debug(f"analyse | Saving output CSV ({out_file.name})...")
    analyse_df = io.saveResultsCSV(analyse_results, out_file)
    lg.debug(f"analyse | Printing summary message...")
    io.printSummaryMessage(results=analyse_df, nfiles=len(seg_files), startt=START_TIME, endt=END_TIME, out_path=out_file)

# =========================
# DEFINE FUNCTION: processSegmentation
# =========================
def processSegmentation(seg_path: Path, fill_threshold):
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
    file_results = []
    lg.debug(f"analyse | {seg_path.name} | Starting component processing...")
    with logging_redirect_tqdm():
        for component in tqdm(component_list, desc="Components processed"):
            lg.debug(f"analyse | {seg_path.name} | Component {component.label} | Measuring component features...")
            component_data = processComponent(component.label, components, component, voxel_size_nm, seg_path.name, fill_threshold)
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
def processComponent(component_label, labelled_volumes, component_properties, voxel_size_nm, filename, fill_threshold):
    '''
    For a given component, make all defined measurements and return as a dictionary.
    '''
    lg.debug(f"analyse | {filename} | Component {component_label} | Setting scale...")
    scale = voxel_size_nm if voxel_size_nm is not None else 1.0
    scale_label = "nm" if voxel_size_nm is not None else "vox"
    lg.debug(f"analyse | {filename} | Component {component_label} | Creating component mask...")
    component_mask = measurement.createComponentMask(component=component_properties, labelled_vol=labelled_volumes, label_val=component_label)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring membrane volume and equivalent diameter...")
    membrane_vol_nm3, equiv_diameter_nm = measurement.measureMembraneVolumeDiameter(component=component_properties, scale=scale)
    component_mask_dilated = filtering.morphologicalDilation(component_mask)
    lg.debug(f"analyse | {filename} | Component {component_label} | Checking if component is enclosed...")
    enclosed, fill_ratio = filtering.checkEnclosed(component_mask=component_mask_dilated, threshold=fill_threshold)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring lumen volume...")
    lumen_vol_nm3 = measurement.measureLumenVolume(component_mask=component_mask, scale=scale)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring surface area...")
    surface_area = measurement.computeSurfaceArea(component_mask, voxel_size_nm)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring major/minor axes diameters...")
    major_axis_diameter, minor_axis_diameter = geometry.measureAxes(component=component_properties, equiv_diameter_nm=equiv_diameter_nm)
    lg.debug(f"analyse | {filename} | Component {component_label} | Measuring eccentricity and aspect ratio...")
    eccentricity, aspect_ratio = measurement.measureEccentricityAspectRatio(major_axis_diameter=major_axis_diameter, minor_axis_diameter=minor_axis_diameter)
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
