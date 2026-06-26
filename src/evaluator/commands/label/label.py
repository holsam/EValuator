'''
=======================================
EValuator: SEGMENTATION EV LABELLING
=======================================
'''
# ====================
# Import external dependencies
# ====================
import numpy, typer
from pathlib import Path
from typing import Annotated

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import config, lg
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil

# ====================
# Define command: label
# ====================
def label_components(
    segmentation,
    output
):
    '''
    Label connected components in a binary segmentation MRC and write a labelled MRC.

    Reads a binary segmentation (e.g. from MemBrain-seg), assigns a unique integer
    label to each connected component using 6-connectivity, and saves the result as
    an MRC file. The output can be passed directly to [bold]analyse[/bold] or
    [bold]visualise overlay[/bold].
    '''
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
    out_dir = pathutil.generateOutputFileStructure(output, "label")
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