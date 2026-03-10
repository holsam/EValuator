'''
=======================================
EV POST-PROCESSING PIPELINE DEVELOPMENT
=======================================
usage: ev-post-processing.py [-h] (--seg SEG | --seg-dir SEG_DIR) -o OUT [--min-diam MIN_DIAM] [--max-diam MAX_DIAM] [-v]
---------------------------------------
TODO: description
---------------------------------------
TODO: how-to-use
---------------------------------------
LOGGING EXPLANATION
    - Default logging state is 'Warning' (30), which will ouput any warnings as well as the core output (e.g. anything in main())
    - -v sets logging level to 'Info' (20), which will show the above as well as info messages (progress of process_tomograms/process_components)
    - -vv sets logging level to 'Debug' (10), which will show the above and function level messages
---------------------------------------
'''

# =========================
# IMPORT DEPENDENCIES
# =========================
import argparse, datetime, logging, mrcfile, numpy, pandas, sys
from pathlib import Path
from scipy import ndimage
from skimage import measure
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# =========================
# SET DEFAULT CONFIGURATION
# =========================
CLOSURE_FILL_THRESHOLD = 0.05
MAX_DIAMETER_NM = 500.0
MIN_DIAMETER_NM = 20.0
VERBOSITY = 0

# =========================
# INITIALISE LOGGER
# =========================
lg = logging.getLogger("__name__")

# =========================
# DEFINE FUNCTION: parse_arguments
# =========================
def parse_arguments():
    '''
    Initialise and set up parser to read arguments, then read supplied arguments and return. Possible arguments:
    '''
    parser = argparse.ArgumentParser(description="Post-processing pipeline of membrain-seg EV segmentations.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seg", type=Path, help="Path to a single segmentation .mrc file")
    mode.add_argument("--seg-dir", type=Path, help="Path to directory containing segmentation .mrc files (batch processing)")
    parser.add_argument("-o", "--out", type=Path, required=True, help="Path to output CSV file")
    parser.add_argument("--min-diam", type=float, default=MIN_DIAMETER_NM, help=f"Minimum EV equivalent diameter in nm to use for filtering (default: {MIN_DIAMETER_NM})")
    parser.add_argument("--max-diam", type=float, default=MAX_DIAMETER_NM, help=f"Maximum EV equivalent diameter in nm to use for filtering (default: {MAX_DIAMETER_NM})")
    parser.add_argument("-v", "--verbosity", action="count", default=VERBOSITY, help=f"Increase verbosity (-v: show info messages; -vv show detailed info messages)")
    #TODO: add argument for CLOSURE_FILL_THRESHOLD
    args = parser.parse_args() 
    return args

# =========================
# DEFINE FUNCTION: validate_arguments
# =========================
'''
Given a set of arguments (specifically input files), check these exist and are mrc files.
'''
def validate_arguments(args):
    if args.seg:
        if args.seg.exists():
            seg_files = [args.seg]
            # TODO: check is .mrc file? Kind of handled later on (will just auto-exit when mrcfile fails to read) but makes sense to handle here.
        else:
            raise FileNotFoundError(f"{args.seg} does not exist.")
    else:
        if args.seg_dir.exists():
            seg_files = sorted(args.seg_dir.glob("*.mrc"))
            if not seg_files:
                raise FileNotFoundError(f"No .mrc files found in {args.seg_dir}.")
        else:
            raise ReferenceError(f"{args.seg_dir} does not exist.")
    # TODO: add in validation for output file? E.g. check whether output file already exists and add '-n' if so? Or just change argument to be directory to output folder instead.
    return seg_files

# =========================
# DEFINE FUNCTION: read_segmentation_mrc
# =========================
def read_segmentation_mrc(path: Path):
    '''
    Reads a segmented MRC file (as produced by membrain-seg). If MRC file header contains voxel_size_nm, read this as well otherwise fall back to None
    '''
    with mrcfile.open(str(path), mode="r", permissive=True) as file:
        data = file.data.astype(bool)
        vox_a = float(file.voxel_size.x)
    if vox_a == 0.0:
        lg.warning(f"{path.name}: voxel size not found in MRC header. Physical measurement units will be voxels - set voxel size manually.")
        voxel_size_nm = None
    else:
        # Convert Å to nm
        voxel_size_nm = vox_a / 10.0
    return data, voxel_size_nm

# =========================
# DEFINE FUNCTION: label_components
# =========================
def label_components(binary_vol: numpy.ndarray):
    '''
    Labels connected components in binary volumes using full 3D (26) connectivity 
    '''
    struc = ndimage.generate_binary_structure(3, 3)
    components, n_components = ndimage.label(binary_vol, structure=struc)
    return components, n_components

# =========================
# DEFINE FUNCTION: check_enclosed
# =========================
def check_enclosed(component_mask: numpy.ndarray, threshold: float = CLOSURE_FILL_THRESHOLD):
    '''
    Checks whether a membrane component forms an enclosed structure by filling in holes in the binary mask - if filled volumes are greater than original, there is an enclosed structure (i.e. EV).
    Threshold corresponds the ratio of (filled volume - original volume) / filled volume at which a shape is classified as 'enclosed'
    The fill ratio returned is the fraction of the filled volume which can be attributed to the enclosed interior
    '''   
    filled = ndimage.binary_fill_holes(component_mask)
    n_original = numpy.sum(component_mask)
    n_filled = numpy.sum(filled)
    if n_filled == 0:
        return False, 0.0
    fill_ratio = (n_filled - n_original) / n_filled
    closed = fill_ratio > threshold
    return closed, float(fill_ratio)

# =========================
# DEFINE FUNCTION: compute_surface_area
# =========================
def compute_surface_area(component_mask: numpy.ndarray, voxel_size_nm: float):
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
# DEFINE FUNCTION: derive_axes
# =========================
def derive_axes(intertia_tensor, voxel_size_nm=None):
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
# DEFINE FUNCTION: measure_membrane_vol_diameter()
# =========================
def measure_membrane_vol_diameter(component, scale):
    '''
    Measures the volume of membrane components in voxels and converts this to nm^3. Based on a perfect sphere, also calculates the diameter (in nm) which would give this volume (to be used in determining actual axis size).
    '''
    vol_vox = component.area #nb component.area = voxel count which is same as volume
    vol_nm3 = vol_vox * (scale ** 3)
    equiv_diameter_nm = (6 * vol_nm3 / numpy.pi) ** (1/3)
    return vol_nm3, equiv_diameter_nm

# =========================
# DEFINE FUNCTION: create_component_mask()
# =========================
def create_component_mask(component, labelled_vol, label_val):
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
# DEFINE FUNCTION: measure_lumen_vol()
# =========================
def measure_lumen_vol(component_mask, scale):
    '''
    Calculate the volume (sum of voxels) of filled components in component_mask to measure the volume of EV lumen
    '''
    filled_mask = ndimage.binary_fill_holes(component_mask)
    lumen_vol_vox = numpy.sum(filled_mask) - numpy.sum(component_mask)
    lumen_vol_nm3 = lumen_vol_vox * (scale ** 3)
    return lumen_vol_nm3

# =========================
# DEFINE FUNCTION: measure_axes()
# =========================
def measure_axes(component, equiv_diameter_nm):
    '''
    Measure major and minor axes of EV by approximating as ellipsoid.
    The semi-axes are derived algebraically (using eigenvalues on inertia) and then scaled to 'real-world size' using the equivalent diameter calculated as if the EV was a perfect sphere (but adjusted to the specific ellipsoid shape).
    '''
    # Derive semi-axes
    inv_sqrt_axes = derive_axes(intertia_tensor=component.inertia_tensor)
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
# DEFINE FUNCTION: measure_eccentricity_aspectratio()
# =========================
'''
Given a major and minor diameter, calculate the eccentricity (as a measure of the shape of the EV: (tubular) 0 ≤ e ≤ 1 (spherical)).
'''
def measure_eccentricity_aspectratio(major_axis_diameter, minor_axis_diameter):
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
# DEFINE FUNCTION: save_results_csv
# =========================
'''
Convert (list of) list of dictionaries to a single dataframe and save this to a .csv file for further analysis.
'''
def save_results_csv(pipeline_results, out_path:Path):
    # Convert list of dictionaries to pandas dataframe
    pipeline_df = pandas.DataFrame(pipeline_results)
    # Save dataframe to CSV file (at given output path)
    pipeline_df.to_csv(out_path, index=False)
    # Log info-level message to state saving worked
    lg.info(f"Pipeline results saved to: {out_path}")
    # Return dataframe of results
    return pipeline_df

# =========================
# DEFINE FUNCTION: process_component
# =========================
def process_component(component_label, labelled_volumes, component_properties, voxel_size_nm, filename):
    '''
    For a given component, make all the defined measurements and return as a dictionary
    '''
    # Set up scale and labels based on whether voxel size in nm is known
    scale = voxel_size_nm if voxel_size_nm is not None else 1.0
    scale_label = "nm" if voxel_size_nm is not None else "vox"
    lg.debug(f"{filename} - component {component_label} - scale set.")
    # Create component mask (using bounding box)Get bounding box of component and convert to ZYX ordered array, then create a mask for this
    component_mask = create_component_mask(component=component_properties, labelled_vol=labelled_volumes, label_val=component_label)
    lg.debug(f"{filename} - component {component_label} - component mask created.")
    # Measurement 1: membrane volume and equivalent diameter
    membrane_vol_nm3, equiv_diameter_nm = measure_membrane_vol_diameter(component=component_properties, scale=scale)
    lg.debug(f"{filename} - component {component_label} - membrane volume and equivalent diameter measurements finished.")
    # Measurement 2: check if component is enclosed
    enclosed, fill_ratio = check_enclosed(component_mask=component_mask)
    lg.debug(f"{filename} - component {component_label} - enclosure check finished.")
    # Measurement 3: internal (lumen) volume
    lumen_vol_nm3 = measure_lumen_vol(component_mask=component_mask, scale=scale)
    lg.debug(f"{filename} - component {component_label} - lumen volume measurement finished.")
    # Measurement 4: surface area
    surface_area = compute_surface_area(component_mask, voxel_size_nm)
    lg.debug(f"{filename} - component {component_label} - surface area measurement finished.")
    # Measurement 5: major/minor axes sizes, 
    major_axis_diameter, minor_axis_diameter = measure_axes(component=component_properties, equiv_diameter_nm=equiv_diameter_nm)
    lg.debug(f"{filename} - component {component_label} - major/minor axes diameter measurements finished.")
    # Measurement 6: eccentricity, aspect_ratio
    eccentricity, aspect_ratio = measure_eccentricity_aspectratio(major_axis_diameter=major_axis_diameter, minor_axis_diameter=minor_axis_diameter)
    lg.debug(f"{filename} - component {component_label} - eccentricity and aspect ratio measurements finished.")
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
# DEFINE FUNCTION: process_segmentation
# =========================
def process_segmentation(seg_path: Path):
    '''
    Process a given segmentation file, by labelling components and calling the component process function for each of these.
    '''
    lg.debug(f"{seg_path.name} - started processing segmentation file.")
    # Read segmentation data and voxel size information from file
    data, voxel_size_nm = read_segmentation_mrc(seg_path)
    lg.debug(f"{seg_path.name} - read data from file.")
    # Label components and get number of components
    components, n_components = label_components(data)
    lg.debug(f"{seg_path.name} - labelled components.")
    # If no components found, log warning-level message and exit pipeline
    if n_components == 0:
        lg.warning(f"{seg_path.name} - no components identified. Skipping file.")
        return []
    # Otherwise log info-level message about number of components identified
    lg.info(f"{seg_path.name} - {n_components} components identified for analysis.")
    # Generate a list of region properties
    component_list = measure.regionprops(components)
    lg.debug(f"{seg_path.name} - measured component region properties.")
    # Calculate voxel size limits (based on whether vox->nm conversion is known)
    if voxel_size_nm is not None:
        min_vox = (MIN_DIAMETER_NM / (2 * voxel_size_nm)) ** 3 * (4/3) * numpy.pi
        max_vox = (MAX_DIAMETER_NM / (2 * voxel_size_nm)) ** 3 * (4/3) * numpy.pi
    else:
        min_vox = 0
        max_vox = numpy.inf
    lg.debug(f"{seg_path.name} - defined file voxel limits.")
    # Initialise results list
    file_results = []
    # Loop through each component in the list of component properties (using tqdm for progress bar and loggin_redirect_tqdm to handle logging)
    with logging_redirect_tqdm():
        for component in tqdm(component_list, desc="Components processed"):
            lg.debug(f"{seg_path.name} - component {component.label} - checking against voxel count filter.")
            # Use a basic filter (voxel count which is computed easily) to check component isn't too large or small
            if not (min_vox <= component.area <= max_vox):
                lg.debug(f"{seg_path.name} - component {component.label} - outside of voxel count filter. Skipping component.")
                continue
            lg.debug(f"{seg_path.name} - component {component.label} - checking against extent filter.")
            # Another filter to check the ratio of component voxels to bounding box volume (very permissive at this stage)
            if (component.extent < 0.01):
                lg.debug(f"{seg_path.name} - component {component.label} - outside of extent filter. Skipping component.")
                continue
            # Call process_component to measure morphological features
            f"{seg_path.name} - component {component.label} - measuring component features."
            component_data = process_component(component.label, components, component, voxel_size_nm, seg_path.name)
            # If processed component data is None (i.e. somethings gone wrong) - log warning-level message
            if component_data is None:
                lg.warning(f"{seg_path.name} - component {component.label} - component processing failed. Skipping component.")
                continue
            # Append component data to list of results for the segmentation file
            file_results.append(component_data)
            lg.debug(f"{seg_path.name} - component {component.label} - processing finished.")
    # Return list of dictionaries with component features
    return file_results

# =========================
# DEFINE FUNCTION: main
# =========================
def main():
    global MAX_DIAMETER_NM, MIN_DIAMETER_NM, VERBOSITY
    # ---------------------
    # Parse arguments and set defaults for non-defined variables
    # ---------------------
    args = parse_arguments()
    MAX_DIAMETER_NM = args.max_diam
    MIN_DIAMETER_NM = args.min_diam
    verbosity_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    VERBOSITY = verbosity_levels[min(args.verbosity, len(verbosity_levels) - 1)]
    # ---------------------
    # Validate arguments and get files to process
    # ---------------------
    seg_files = validate_arguments(args)
    # ---------------------
    # SET UP LOGGER CONFIGURATION
    # ---------------------
    logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level = VERBOSITY)
    # ---------------------
    # PRINT STARTUP MESSAGE
    # ---------------------
    print(f"\nPOST-PROCESSING PIPELINE FOR EV SEGMENTATIONS")
    print(f"Full command: ev-post-processing.py {sys.argv}")
    START_TIME = datetime.datetime.now()
    print(f"\nEV post-processing pipeline started: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{len(seg_files)} segmentation files found") if not args.seg else print(f"1 segmentation file found")
    # ---------------------
    # RUN PIPELINE
    # ---------------------
    pipeline_results = []
    with logging_redirect_tqdm():
        for seg_file in tqdm(seg_files, desc="Segmentation files processed"):
            try:
                seg_file_results = process_segmentation(seg_file)
                pipeline_results.extend(seg_file_results)
            except Exception as e:
                lg.warning(f"Failed to process {seg_file.name}: {e}")
                continue
    # ---------------------
    # Save results if EVs processed
    # ---------------------
    END_TIME = datetime.datetime.now()
    if not pipeline_results:
        lg.warning(f"No EVs detected across all segmentation files.")
        lg.warning(f"Nothing saved to {args.out}.")
        print(f"EV post-processing pipeline finished: {END_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    pipeline_df = save_results_csv(pipeline_results, args.out)
    # ---------------------
    # PRINT FINAL MESSAGE
    # ---------------------
    RUNTIME = (END_TIME - START_TIME)
    print(f"EV post-processing pipeline finished: {END_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n*Pipeline run summary*")
    print(f"- Runtime: {(RUNTIME)}")
    print(f"- Segmentation files processed: {len(seg_files)}")
    print(f"- Segmentation files with EVs: {pipeline_df['tomogram'].nunique()} ({(100*pipeline_df['tomogram'].nunique())/len(seg_files):.1f}%)")
    print(f"- EVs processed: {len(pipeline_df)}")
    print(f"- Number of enclosed EVs: {pipeline_df['is_enclosed'].sum()} ({100*pipeline_df['is_enclosed'].mean():.1f}%)")
    print(f"- Equivalent diameters: {pipeline_df['equiv_diameter_nm'].mean():.1f} ± {pipeline_df['equiv_diameter_nm'].std():.1f} nm (mean ± SD)\n")

if __name__=="__main__":
    main()