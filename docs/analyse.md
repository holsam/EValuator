# EValuator - analyse

## Overview
The `analyse` command runs a morphological analysis pipeline on one or more labelled MRC files produced by [`evaluator label`](label.md). It filters components that likely do not represent true EVs, and extracts quantitative morphological measurements for each identified EV, which are written to a CSV file.

The command accepts either a single labelled MRC file or a directory containing multiple labelled MRC files, making it suitable for both single-tomogram analysis and batch HPC workflows. It also accepts binary segmentation masks directly (the volume type is detected automatically), though passing a pre-labelled MRC from `label` is the recommended workflow, as this guarantees consistent integer labels across the `analyse` and `visualise overlay` steps.

The pipeline was developed for analysis of isolated EV preparations imaged by cryo-ET, but may be applicable to other membrane-bound structures of comparable scale (10s-100s nm).


## Pipeline description
For each input file, the pipeline:
1. Reads the MRC volume and voxel size from the file header (if present, see [Note on voxel size](#note-on-voxel-size) below). Detects automatically whether the input is a pre-labelled MRC (from `evaluator label`) or a binary segmentation, and labels components on the fly if needed.
2. Filters components by voxel count (derived from `--min-diam` and `--max-diam`) and by bounding-box extent ratio (a permissive check to remove very sparse artefacts).
3. Measures each remaining component (see [Output CSV columns](#output-csv-columns) below). For each component, this includes applying a per-component morphological closing before the enclosure check, to account for small gaps in MemBrain-seg segmentations.
4. Saves results to a CSV file.

#### Note on voxel size
If the MRC file header contains a valid voxel size (i.e. the value is non-zero), all measurements are scaled to physical units (nm, nm³, nm²). If no voxel size is found, measurements are reported in voxels, with a warning printed to the terminal. In this case, the diameter filters (`--min-diam`, `--max-diam`) are not applied and all components pass the size filter.


## Usage
`
```
Usage: evaluator analyse [OPTIONS] INPUT

Arguments:
  INPUT   Path to either a single labelled MRC file (output of label) or a
          directory containing multiple labelled MRC files.  [required]

Options:
  -o, --out-dir PATH          Path to output directory. Results will be written
                              under '.../evaluator/results/analyse/'.
                              [default: .]
  --min-diam FLOAT            Minimum EV equivalent diameter in nm to use for
                              filtering.  [default: 20.0; ≥0]
  --max-diam FLOAT            Maximum EV equivalent diameter in nm to use for
                              filtering.  [default: 500.0; ≥0]
  --fill-threshold FLOAT      Closure fill threshold to use for determining
                              enclosed EVs.  [default: 0.05; 0-1]
  -h, --help                  Show this message and exit.
```

Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `analyse` subcommand:

```sh
evaluator -v analyse evaluator/results/label/
evaluator -vv analyse evaluator/results/label/tomo_seg_labelled.mrc
```

### Options
#### `--min-diam` and `--max-diam`

These options filter components by their equivalent sphere diameter (the diameter of a sphere with the same membrane volume as the component). The default range of 20-500 nm is appropriate for typical EV preparations, which include small exosomes (~30-150 nm) through to larger MVB-derived vesicles (~200-500 nm). These defaults can be adjusted to match the expected size range of the structures being analysed.

#### `--fill-threshold`

This threshold controls how the pipeline determines whether a membrane component forms a closed, enclosed structure. It is defined as the fraction of the filled volume (i.e. the original component plus any enclosed interior cavity) that can be attributed to the interior:

```
fill_ratio = (filled_volume - original_volume) / filled_volume
```

A component is classified as enclosed (`is_enclosed = True`) if `fill_ratio > fill_threshold`. The default of `0.05` is deliberately permissive, to accommodate incomplete segmentations where a small fraction of the membrane may not have been captured. Decreasing this threshold includes more components as enclosed; increasing it requires a larger enclosed cavity relative to the membrane.

## Output

Results are written to `evaluator-analyse_results.csv` in the output directory (default: current working directory) under `evaluator/results/analyse/`. If the pipeline is run several times in the same output directory, subsequent result files are named `evaluator-analyse_results-1.csv`, `evaluator-analyse_results-2.csv`, and so on.

### Output CSV columns

The output CSV file contains one row per membrane component which has passed all filters (and is therefore assumed to represent an EV). The following table lists the measurements reported for each EV; please see the accompanying footnotes for further information.

Column | Description | Units<sup>**1**</sup>
--|--|--
`tomogram` | Filename of the input MRC file from which the EV was identified |
`label` | Unique integer identifier for the EV within its file |
`equiv_diameter_nm`<sup>**2**</sup> | Diameter of a sphere with the same volume as the membrane component | nm (rounded to 2 d.p.)
`major_axis_diameter`<sup>**3**</sup> | Length of the longest axis of the best-fit ellipsoid | nm (rounded to 2 d.p.)
`minor_axis_diameter`<sup>**3**</sup> | Length of the shortest axis of the best-fit ellipsoid | nm (rounded to 2 d.p.)
`aspect_ratio`<sup>**4**</sup> | Ratio of `major_axis_diameter` to `minor_axis_diameter` | unitless (rounded to 2 d.p.)
`eccentricity`<sup>**5**</sup> | Degree of deviation from a perfect sphere | unitless (0 ≤ e ≤ 1; 0 = perfect sphere; rounded to 2 d.p.)
`membrane_volume` | Volume of the membrane | nm³ (rounded to 2 d.p.)
`lumen_volume`<sup>**6**</sup> | Volume of the enclosed interior of the EV | nm³ (rounded to 2 d.p.)
`surface_area`<sup>**7**</sup> | Estimated membrane surface area | nm² (rounded to 2 d.p.)
`is_enclosed` | Whether the component forms a closed membrane structure | boolean (True/False)
`closure_fill_ratio` | Fill ratio used to determine `is_enclosed`. Values closer to 1.0 indicate a more completely enclosed membrane | unitless (0 < r ≤ 1; rounded to 4 d.p.)
`voxel_size_nm` | Voxel size in nanometres as read from MRC file header, or None if not present | nm (rounded to 4 d.p.)
`measurement_units` | Units used for measurements | nm if voxel size was available, otherwise vox

<sup>**1**</sup> Units given here assume the voxel size in nanometres was read from the MRC file header. If this is not the case, units will not be scaled to physical units and will be in voxels/voxels³.

<sup>**2**</sup> `equiv_diameter_nm` is not the measured diameter of an EV. Given the volume of all membrane voxels (Vm), the equivalent diameter is calculated as `(6Vm/π)**(1/3)`, which assumes the shape of the component is a perfect sphere. This is likely not a valid assumption for biological EVs, and `equiv_diameter_nm` is therefore only used as a rough proxy during size filtering and for subsequent axis scaling.

<sup>**3**</sup> `major/minor_axis_diameter` are the more accurate measurements of EV size, calculated from the best-fit ellipsoid that matches the EV morphology. Both measurements are derived from the eigenvalues of the component's inertia tensor, which are scaled using `equiv_diameter_nm`.

<sup>**4**</sup> A perfect sphere would have an `aspect_ratio` of 1.0. An EV with `aspect_ratio` greater than 1.0 can be described as a prolate ellipsoid (i.e. elongated), whereas an EV with `aspect_ratio` less than 1.0 can be described as an oblate ellipsoid (i.e. flattened).

<sup>**5**</sup> Eccentricity is calculated as `sqrt(1 - (c/a)^2)` where `a` and `c` are the semi-major and semi-minor axes respectively. A perfect sphere would have `eccentricity` approaching 0, whereas an infinitely elongated ellipsoid would have `eccentricity` approaching 1.

<sup>**6**</sup> This volume is calculated by filling the membrane mask and subtracting all membrane voxels. Non-enclosed components will have `lumen_volume` of 0.

<sup>**7**</sup> Surface area is computed using the marching cubes algorithm as implemented by `skimage.measure.marching_cubes`. If the marching cubes algorithm fails (e.g. for very small or degenerate components), `NaN` will be returned.

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
Results saved to: .../evaluator/results/analyse/evaluator-analyse_results.csv
```

<br>

---
<p align="right"><a href="#evaluator---analyse">^ Back to top</a></p>
