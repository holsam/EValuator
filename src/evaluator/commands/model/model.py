'''
=======================================
EValuator: EV MODELLING FROM LABELLED SEGMENTATION
=======================================
'''

# ====================
# Import external dependencies
# ====================

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import config as confutil
from evaluator.utils.settings import lg

# ====================
# model_evs: orchestration logic for model command
# ====================
def model_evs(input_file, output_dir):
    # Load configuration file
    config, evaluator_dir = confutil.load_config(output)
    # Read labelled MRC file
    lg.debug(f"model | Reading input labelled MRC file...")
    labelled_data, voxel_size_nm = mrcutil.readMRCFile(input_file)
    labels = np.unique(labelled_data)
    labels = labels[labels != 0]
    records: list[dict] = []
    for label_id in labels:
        points = np.argwhere(labelled == label_id).astype(float)
        try:
            result = fit_vesicle(points, voxel_size_nm=voxel_size_nm)
        except ValueError as exc:
            lg.warning(f"model | Fit failed for label {label_id}: {exc}")
            continue
        result["source_file"] = str(input_mrc)
        result["label_id"] = int(label_id)
        records.append(result)

    output.mkdir(parents=True, exist_ok=True)
    provenance = {
        "command": "model",
        "source_file": str(input_mrc),
        "n_vesicles_fitted": len(records),
        "include_unreliable": include_unreliable,
        "config": config.model_dump(),
    }
    write_result = write_results(
        records=records,
        provenance=provenance,
        output_path=output / "model_results",
        output_format=fmt,
    )
    typer.echo(f"[model] wrote results to {write_result.primary_path}")

    fitted_volume = build_fitted_mrc(
        shape=labelled.shape,
        fit_records=records,
        voxel_size_nm=voxel_size_nm,
        include_unreliable=include_unreliable,
    )
    mrc_out_file = output / "model_fitted.mrc"
    with mrcfile.new(mrc_out_file, overwrite=True) as mrc:
        mrc.set_data(fitted_volume.astype(np.uint16))

    print(f"Results file saved to {results_out_file}\n")
    print(f"Fitted MRC saved to {mrc_out_file}\n")