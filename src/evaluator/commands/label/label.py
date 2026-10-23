'''
=======================================
EValuator: SEGMENTATION EV LABELLING
=======================================
'''
# ====================
# Import external dependencies
# ====================
import numpy
from functools import partial
from pathlib import Path
from skimage import measure

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import batch as batchutil
from evaluator.utils import config as confutil
from evaluator.utils.settings import lg
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil

# ====================
# Import EValuator label utilities
# ====================
from evaluator.commands.label.utils.filters import filterComponentsBySize
from evaluator.commands.label.utils.geometric_proxies import estimateCentroidRadius, estimateArcCoverage, ARC_COVERAGE_N_BINS
from evaluator.commands.label.utils.merge import findMergeGroups, applyMerges

# ====================
# Define command: label
# ====================
def label_batch(input_path, output, max_workers=None, **overrides) -> None:
    '''
    Resolve input_path (file or directory) to MRC files and labels each in parallel
    '''
    mrc_files = batchutil.resolve_mrc_inputs(input_path)
    config, _ = confutil.load_config(output)
    max_workers = max_workers if max_workers is not None else config.label.max_workers
    worker = partial(label_components, output=output, **overrides)
    batchutil.run_batch(mrc_files, worker=worker, desc="Segmentation files processed", max_workers=max_workers)

def label_components(
    segmentation,
    output,
    **overrides,
) -> None:
    '''
    Label connected components in a binary segmentation MRC and write a labelled MRC
    '''
    # Load configuration file
    config, evaluator_dir = confutil.load_config(output)
    # If CLI overrides provided:
    updates = {k: v for k, v in overrides.items() if v is not None}
    params = config.label.model_copy(update=updates)
    # Validate input MRC
    lg.debug(f"label | Validating input segmentation file...")
    if not mrcutil.validateMRCFile(segmentation):
        raise ValueError(f"{segmentation.name} is not a valid MRC file and will not be processed.")
    # Read segmentation
    lg.debug(f"label | Reading input segmentation file...")
    seg_data, voxel_size_nm = mrcutil.readMRCFile(segmentation)
    seg_data = seg_data.astype(bool)
    # Label components
    lg.info(f"label | Labelling connected components...")
    labelled, n_components = mrcutil.labelComponents(seg_data)
    n_initial = n_components
    lg.info(f"label | {n_components} components identified.")

    # Step 1: merge split components (geometric proxies only)
    lg.debug(f"label | Merging split components...")
    component_points = {c.label: c.coords for c in measure.regionprops(labelled)}
    merge_groups = findMergeGroups(
        component_points,
        centre_tol_factor=params.merge_centre_tol_factor,
        radius_tol_pct=params.merge_radius_tol_pct,
        concentric_radius_pct=params.merge_concentric_radius_pct,
        concentric_centre_frac=params.merge_concentric_centre_frac,
    )
    labelled = applyMerges(labelled, merge_groups)
    n_merge_groups_merged = sum(1 for group in merge_groups if len(group) > 1)
    n_after_merge = len(numpy.unique(labelled)) - 1


    # Step 2: arc-coverage filter (post-merge)
    lg.debug(f"label | Applying arc-coverage filter...")
    n_excluded_arc_coverage = 0
    n_excluded_arc_coverage_size_floor = 0
    for component in measure.regionprops(labelled):
        centroid, radius_estimate = estimateCentroidRadius(component.coords)
        coverage = estimateArcCoverage(component.coords, centroid, radius_estimate)
        if coverage < params.min_arc_coverage:
            max_possible_coverage = min(component.area, ARC_COVERAGE_N_BINS) / ARC_COVERAGE_N_BINS
            size_floor = max_possible_coverage < params.min_arc_coverage
            reason = "size floor (too few voxels to reach threshold)" if size_floor else "incomplete coverage"
            lg.info(f"label | Component {component.label} | Arc coverage {coverage:.2f} below threshold ({params.min_arc_coverage}) — excluding ({reason}).")
            n_excluded_arc_coverage += 1
            if size_floor:
                n_excluded_arc_coverage_size_floor += 1
            labelled[labelled == component.label] = 0

    # Step 3: size/extent filter
    lg.debug(f"label | Applying size filter...")
    n_before_size_filter = len(numpy.unique(labelled)) - 1
    labelled = filterComponentsBySize(
        labelled,
        voxel_size_nm,
        minimum_diameter_nm=params.minimum_diameter_nm,
        maximum_diameter_nm=params.maximum_diameter_nm,
        membrane_thickness_nm=params.membrane_thickness_nm,
    )
    n_excluded_size = n_before_size_filter - (len(numpy.unique(labelled)) - 1)

    surviving_labels = sorted(int(l) for l in numpy.unique(labelled) if l != 0)
    remapped = numpy.zeros_like(labelled)
    for new_id, old_id in enumerate(surviving_labels, start=1):
        remapped[labelled == old_id] = new_id
    labelled = remapped
    n_components = len(surviving_labels)
    lg.info(f"label | {n_components} components retained after merge/filter.")

    # Build output path
    lg.debug(f"label | Creating output directory structure...")
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, "label")
    confutil.write_params(params, out_dir)
    out_file = Path(out_dir, f"{segmentation.stem}_labelled.mrc")
    # Resolve name conflicts
    if out_file.exists():
        counter = 1
        while True:
            out_file = Path(out_dir, f"{segmentation.stem}_labelled-{counter}.mrc")
            if not out_file.exists():
                break
            counter += 1

    # Write labelled MRC
    lg.debug(f"label | Writing labelled MRC to {out_file.name}...")
    mrcutil.writeMRCFile(labelled.astype(numpy.float32), voxel_size_nm, out_file)
    lg.info(f"label | Finished labelling.")

    # Write per-file exclusion tally (visible at warning for non-interactive batch runs)
    tally = (
        f"components identified: {n_initial}\n"
        f"merge groups merged (>1 component): {n_merge_groups_merged}\n"
        f"components after merge: {n_after_merge}\n"
        f"excluded by arc-coverage filter: {n_excluded_arc_coverage}\n"
        f"excluded by size/extent filter: {n_excluded_size}\n"
        f"components retained: {n_components}\n"
    )
    tally_file = out_file.with_name(f"{out_file.stem}_exclusions.txt")
    tally_file.write_text(tally)
    lg.warning(
        f"label | {segmentation.name}: {n_initial} identified -> {n_components} retained; "
        f"{n_excluded_arc_coverage} excluded by arc-coverage filter ({n_excluded_arc_coverage_size_floor} too small to reach threshold), "
        f"{n_excluded_size} excluded by size filter; "
        f"tally written to {tally_file.name}."
    )
