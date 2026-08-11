'''
=======================================
EValuator: EV MODELLING FROM LABELLED SEGMENTATION
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import config as confutil
from evaluator.utils import io as ioutil
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil
from evaluator.utils.settings import lg

# ====================
# Import EValuator model utilities
# ====================
from evaluator.commands.model.utils.least_squares_fit import fit_vesicle
from evaluator.commands.model.utils.reconstruction import build_fitted_mrc

# ====================
# model_evs: orchestration logic for model command
# ====================
def model_evs(
    input_file,
    output_dir,
    **overrides,
) -> None:
    # Load configuration file
    config, evaluator_dir = confutil.load_config(output)
    updates = {k: v for k, v in overrides.items() if v is not None}
    params = config.model.model_copy(update=updates)
    # Read labelled MRC file
    lg.debug(f"model | Reading input labelled MRC file...")
    labelled_data, voxel_size_nm = mrcutil.readMRCFile(input_file)
    labels = np.unique(labelled_data)
    labels = labels[labels != 0]
    records: list[dict] = []
    # Fit each labelled vesicle
    lg.info(f"model | Fitting {len(labels)} labelled components..." )
    for label_id in labels:
        points = np.argwhere(labelled == label_id).astype(float)
        try:
            result = fit_vesicle(points, voxel_size_nm=voxel_size_nm)
        except ValueError as exc:
            lg.warning(f"model | Fit failed for label {int(label_id)}: {exc}")
            continue
        result["source_file"] = str(input_mrc)
        result["label_id"] = int(label_id)
        records.append(result)
    lg.info(f"model | {len(records)}/{len(labels)} component(s) fitted" )
    # Create output directory
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, "model")
    confutil.write_params(params, out_dir)
    lg.debug(f"model | Saving results file...")
    provenance = {
        "command": "model",
        "source_file": str(input_mrc),
        "n_vesicles_fitted": len(records),
        "config": config.model_dump(),
    }
    write_result = write_results(
        records=records,
        provenance=provenance,
        output_path=out_dir / "model",
        output_format=config.output.format,
    )

    # Build the fitted MRC file for visualisation
    lg.debug(f"model | Building fitted MRC file...")
    fitted_volume = build_fitted_mrc(
        shape=labelled.shape,
        fit_records=records,
        voxel_size_nm=voxel_size_nm,
    )
    mrc_out_file = out_dir / "model_fitted.mrc"
    mrcutil.writeMRCFile(fitted_volume.astype(np.uint16), voxel_size_nm, mrc_out_file)
    lg.debug(f"model | Wrote fitted MRC file")
