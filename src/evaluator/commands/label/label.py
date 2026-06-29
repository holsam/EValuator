'''
=======================================
EValuator: SEGMENTATION EV LABELLING
=======================================
'''
# ====================
# Import external dependencies
# ====================
import numpy
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import config as confutil
from evaluator.utils.settings import lg
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil

# ====================
# Define command: label
# ====================
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
    lg.info(f"label | {n_components} components identified.")
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
    print(f"\n{n_components} components labelled.")
    print(f"Labelled MRC saved to: {out_file}\n")