# EValuator - analyse

## Overview
The `analyse` command runs a morphological analysis pipeline on one or more labelled MRC files produced by [`evaluator label`](label.md), extracting quantitative morphological measurements for each identified EV, and writing these to a CSV file.

The command accepts either a single labelled MRC file or a directory containing multiple labelled MRC files, making it suitable for both single-tomogram analysis and batch HPC workflows. It also accepts binary segmentation masks directly (the volume type is detected automatically), though passing a pre-labelled MRC from `label` is the recommended workflow, as this guarantees consistent integer labels across the `analyse` and `visualise overlay` steps.

The pipeline was developed for analysis of isolated EV preparations imaged by cryo-ET, but may be applicable to other membrane-bound structures of comparable scale (10s-100s nm).


## Pipeline description
For each input file, the pipeline:
1. Reads the MRC volume and voxel size from the file header (if present, see [Note on voxel size](#note-on-voxel-size) below). Detects automatically whether the input is a pre-labelled MRC (from `evaluator label`) or a binary segmentation, and labels components on the fly if needed.
2. Measures each component (see [Output CSV columns](#output-csv-columns) below). For each component, this includes applying a per-component morphological dilation before the enclosure check, to account for small gaps in MemBrain-seg segmentations.
3. Saves results to a CSV file.

#### Note on voxel size
If the MRC file header contains a valid voxel size (i.e. the value is non-zero), all measurements are scaled to physical units (nm, nm³, nm²). If no voxel size is found, measurements are reported in voxels, with a warning printed to the terminal.

## Usage
```
Usage: evaluator analyse [OPTIONS] INPUT

Arguments:
  INPUT   Path to either a single labelled MRC file (output of label) or a
          directory containing multiple labelled MRC files.  [required]

Options:
  -o, --out-dir PATH              Path to output directory. Results will be written under '.../evaluator/analyse/'. [default: .]
  --fill-threshold FLOAT  [0-1]   Override configuration fill threshold parameter for this run.
  -h, --help                      Show this message and exit.

Batch Options:
  -j, --jobs INTEGER      [x>=1]  Maximum parallel worker processes (default: CPU count).

Vesicle QC:
  --qc-max-sphere-rmse-rel FLOAT  [x>=0]  Max best-fit-sphere relative RMSE for a vesicle-like component.
  --qc-max-aspect-ratio FLOAT     [x>=1]  Max major/minor axis ratio for a vesicle-like component.
  --qc-min-solidity FLOAT         [0-1]   Min voxel-count/convex-hull-volume ratio for a vesicle-like component.
  --qc-min-arc-coverage FLOAT     [0-1]   Min fitted-sphere surface coverage for a non-enclosed component to still count as vesicle-like.
  --qc-max-fit-points INTEGER     [x>=4]  Random-subsample size of component voxels used for the QC sphere fit/convex hull/arc grid.
```

Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `analyse` subcommand:

```sh
evaluator -v analyse evaluator/label/
evaluator -vv analyse evaluator/label/tomo_seg_labelled.mrc
```

### Options
#### `--fill-threshold`

This threshold controls how the pipeline determines whether a membrane component forms a closed, enclosed structure. It is defined as the fraction of the filled volume (i.e. the original component plus any enclosed interior cavity) that can be attributed to the interior:

```
fill_ratio = (filled_volume - original_volume) / filled_volume
```

A component is classified as enclosed (`is_enclosed = True`) if `fill_ratio > fill_threshold`. The default of `0.05` is deliberately permissive, to accommodate incomplete segmentations where a small fraction of the membrane may not have been captured. Decreasing this threshold includes more components as enclosed; increasing it requires a larger enclosed cavity relative to the membrane.

#### `--qc-max-sphere-rmse-rel`, `--qc-max-aspect-ratio`, `--qc-min-solidity`, `--qc-min-arc-coverage`
These four thresholds underpin the vesicle-vs-debris QC flag included in results (`is_vesicle_like` / `qc_flags`, see [Output CSV columns](#output-csv-columns)). 

This is explicitly designed as a non-destructive check: no components are dropped and each component row remains in the output CSV. Instead it reports whether a component resembles a vesicle, or may be 'debris' (e.g. irregular clumps, elongated sheets, crescent fragments). Each value can be configured using the CLI or `config.toml` file, however default values are relatively permissive so components can be manually checked rather than excluding all but spherical membrane components.

For `is_vesicle_like` to be `True`, all of the below checks must pass. If any fail, `is_vesicle_like` is flipped to `False`, and `qc_flags` has the failing test(s) added. Any components that have fewer than four voxels will not be checked, with `is_vesicle_like=False` and `qc_flags=too_small` (each metric column will show `NaN`).

Check | Fails when | Default | `config.toml` key | CLI flag
--|--|--|--
best-fit-sphere relative RMSE | `sphere_rmse_rel > qc_max_sphere_rmse_rel` | `0.25` | `qc_max_sphere_rmse_rel` | `--qc-max-sphere-rmse-rel`
axis aspect ratio | `aspect_ratio > qc_max_aspect_ratio` | `2.5` | `qc_max_aspect_ratio` | `--qc-max-aspect-ratio`
solidity | `solidity < qc_min_solidity` | `0.10` | `qc_min_solidity` | `--qc-min-solidity`
open shell | not `is_enclosed` **and** `arc_coverage < qc_min_arc_coverage` | `0.50` | `qc_min_arc_coverage` | `--qc-min-arc-coverage`

Each metric is computed on a random subsample of each component's voxels, set by the CLI flag `--qc-max-fit-points`/`config.toml` key `qc_max_fit_points`. This defaults to `4000` for performance, but can be raised if a metric appears noisy. The subsampling used is deterministic with a fixed seed, to allow reproducible selections across different configurations.

## Output

Results are written to `evaluator-analyse_results.csv` in the output directory (default: current working directory) under `evaluator/analyse/`. If the pipeline is run several times in the same output directory, subsequent result files are named `evaluator-analyse_results-1.csv`, `evaluator-analyse_results-2.csv`, and so on.

### Output CSV columns

The output CSV file contains one row per membrane component (assumed to represent an EV). The following table lists the measurements reported; please see the accompanying footnotes for further information.

Column | Description | Units[^units]
--|--|--
`tomogram` | Filename of the input MRC file from which the EV was identified |
`label` | Unique integer identifier for the EV within its file |
`equiv_diameter_nm`[^equivdiameter] | Diameter of a sphere with the same volume as the membrane component | nm (rounded to 2 d.p.)
`major_axis_diameter`[^diameters] | Length of the longest axis of the best-fit ellipsoid | nm (rounded to 2 d.p.)
`minor_axis_diameter`[^diameters] | Length of the shortest axis of the best-fit ellipsoid | nm (rounded to 2 d.p.)
`aspect_ratio`[^aspectratio] | Ratio of `major_axis_diameter` to `minor_axis_diameter` | unitless (rounded to 2 d.p.)
`eccentricity`[^eccentricity] | Degree of deviation from a perfect sphere | unitless (0 ≤ e ≤ 1; 0 = perfect sphere; rounded to 2 d.p.)
`membrane_volume` | Volume of the membrane | nm³ (rounded to 2 d.p.)
`lumen_volume`[^lumenvol] | Volume of the enclosed interior of the EV | nm³ (rounded to 2 d.p.)
`surface_area`[^surfacearea] | Estimated membrane surface area | nm² (rounded to 2 d.p.)
`is_enclosed` | Whether the component forms a closed membrane structure | boolean (True/False)
`closure_fill_ratio` | Fill ratio used to determine `is_enclosed`. Values closer to 1.0 indicate a more completely enclosed membrane | unitless (0 < r ≤ 1; rounded to 4 d.p.)
`sphere_rmse_rel` | Best-fit-sphere RMSE ÷ fitted radius over the component's voxels. Low for round shells, high for sheets/crescents/blobs | unitless (rounded to 4 d.p.; `NaN` if < 4 voxels)
`solidity` | Voxel count ÷ convex-hull volume (QuickHull over the component's voxels; ~1 for a solid convex blob, low for sprawling/concave debris) | unitless (0 < s ≲ 1; rounded to 4 d.p.)
`arc_coverage` | Fraction of the fitted sphere's surface (18×36 grid) occupied by the component | unitless (0 ≤ c ≤ 1; rounded to 4 d.p.; `NaN` if < 4 voxels)
`bbox_extent` | Bounding-box fill ratio (`skimage` `regionprops.extent`) | unitless (0 < e ≤ 1; rounded to 4 d.p.)
`is_vesicle_like` | Composite QC flag — `True` unless a vesicle-vs-debris check fails (see [`--qc-*` options](#--qc-max-sphere-rmse-rel---qc-max-aspect-ratio---qc-min-solidity---qc-min-arc-coverage)) | boolean (True/False)
`qc_flags` | Comma-joined names of failed QC checks (`sphere_rmse`, `aspect_ratio`, `solidity`, `open_shell`, `too_small`); empty when clean | string
`voxel_size_nm` | Voxel size in nanometres as read from MRC file header, or None if not present | nm (rounded to 4 d.p.)
`measurement_units` | Units used for measurements | nm if voxel size was available, otherwise vox


### Terminal summary output

Once the pipeline has completed, a short summary is printed to the terminal:

```
Pipeline run summary
- Runtime: 0:06:12.4
- Segmentation files processed: 10
- Segmentation files with EVs: 9 (90.0%)
- EVs processed: 87
- Number of enclosed EVs: 71 (81.6%)
- Equivalent diameters: 112.4 ± 48.3 nm (mean ± SD)
- Vesicle-like components: 63 / 87 (72.4%)
Results saved to: .../evaluator/analyse/evaluator-analyse_results.csv
```

<br>

---
<p align="right"><a href="#evaluator---analyse">^ Back to top</a></p>

<br>

[^units]: Units given here assume the voxel size in nanometres was read from the MRC file header. If this is not the case, units will not be scaled to physical units and will be in voxels/voxels³.

[^equivdiameter]: `equiv_diameter_nm` is not the measured diameter of an EV. Given the volume of all membrane voxels (Vm), the equivalent diameter is calculated as `(6Vm/π)**(1/3)`, which assumes the shape of the component is a perfect sphere. This is likely not a valid assumption for biological EVs, and `equiv_diameter_nm` is therefore only used as a rough proxy during size filtering and for subsequent axis scaling.

[^diameters]: `major/minor_axis_diameter` are the more accurate measurements of EV size, calculated from the best-fit ellipsoid that matches the EV morphology. Both measurements are derived from the eigenvalues of the component's inertia tensor, which are scaled using `equiv_diameter_nm`.

[^aspectratio]: A perfect sphere would have an `aspect_ratio` of 1.0. An EV with `aspect_ratio` greater than 1.0 can be described as a prolate ellipsoid (i.e. elongated), whereas an EV with `aspect_ratio` less than 1.0 can be described as an oblate ellipsoid (i.e. flattened).

[^eccentricity]: Eccentricity is calculated as `sqrt(1 - (c/a)^2)` where `a` and `c` are the semi-major and semi-minor axes respectively. A perfect sphere would have `eccentricity` approaching 0, whereas an infinitely elongated ellipsoid would have `eccentricity` approaching 1.

[^lumenvol]: This volume is calculated by filling the membrane mask and subtracting all membrane voxels. Non-enclosed components will have `lumen_volume` of 0.

[^surfacearea]: Surface area is computed using the marching cubes algorithm as implemented by `skimage.measure.marching_cubes`. If the marching cubes algorithm fails (e.g. for very small or degenerate components), `NaN` will be returned.