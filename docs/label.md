# EValuator - label

## Overview
The `label` command assigns a unique integer label to each connected membrane component in a binary segmentation mask, merges components that are likely split parts of the same EV, filters out unlikely/out-of-range components, and writes the result as a labelled MRC file. It is the first step in the EValuator workflow and should be run before [`analyse`](analyse.md) and [`model`](model.md). The output labelled MRC can be passed directly to `analyse` and `model` for morphological measurements, and to `visualise overlay` for visual inspection of the results.

Labelling is performed using face-only (6-connectivity) 3D connected-component labelling, which is less prone to merging spatially adjacent but structurally separate components than the full 26-connectivity alternative.

`label` accepts either a single segmentation MRC file or a directory of segmentation MRC files (batch mode), with each file processed independently across worker processes in the latter case (see [Batch processing](../README.md#batch-processing)).

## Pipeline description
For each input file, `evaluator label`:
1. Reads the segmentation MRC and voxel size from the file header, and labels connected components.
2. Merges components whose centroid and estimated radius are consistent with being split parts of the same sphere (`--min-arc-coverage`/`--min-diameter`/`--max-diameter` do not affect this step; see [`--min-diameter`/`--max-diameter`](#--min-diameter-and---max-diameter) below for the merge tolerance parameters exposed elsewhere in `config.toml`).
3. Filters out components whose estimated arc coverage of the fitted sphere falls below `--min-arc-coverage`.
4. Filters out components by voxel count (derived from `--min-diameter`/`--max-diameter` and the configured membrane thickness) and by bounding-box extent.
5. Relabels the retained components sequentially (1..N) and writes the result to a labelled MRC.

## Usage

```
Usage: evaluator label [OPTIONS] SEGMENTATION

Arguments:
  SEGMENTATION  Path to either a single binary segmentation MRC (e.g. MemBrain-seg output) or a directory of segmentation MRC files.  [required]

Options:
  -o, --out-dir PATH        Path to output directory. The labelled MRC will be written under '.../evaluator/label/'. [default: .]
  --min-arc-coverage FLOAT  Override configuration minimum arc coverage parameter for this run.
  --min-diameter FLOAT      Override configuration minimum diameter parameter for this run.
  --max-diameter FLOAT      Override configuration maximum diameter parameter for this run.
  -h, --help                Show this message and exit.

Batch Options:
  -j, --jobs INTEGER  Maximum parallel worker processes (default: CPU count).
```

Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `label` subcommand:

```sh
evaluator -v label segmentation.mrc
evaluator -vv label segmentation.mrc
```

### Input

`label` accepts either a single binary segmentation MRC file or a directory containing multiple segmentation files. This is expected to be the output of [MemBrain-seg](https://github.com/teamtomo/membrain-seg), and should contain only two unique values (typically `0` and `1`). The file is read in permissive mode to accommodate minor header inconsistencies.

### Options
#### `--min-arc-coverage`
After merging, each component's coverage of the surface of its best-fit sphere is estimated (via coarse latitude/longitude binning). Components covering less than this fraction of the sphere are excluded. The default (`0.40`) is set in `config.toml` under `[label]`.

#### `--min-diameter` and `--max-diameter`
These options filter components by their equivalent sphere diameter, using the configured membrane thickness to convert diameter to an expected voxel count range. The default range (`20`-`500` nm, set in `config.toml`) is appropriate for typical EV preparations, which include small exosomes (~30-150 nm) through to larger MVB-derived vesicles (~200-500 nm). If no voxel size is present in the input MRC header, this filter is skipped and all components pass.

#### Component merge configuration settings
The merge step (centroid-proximity and radius-agreement tolerances) is controlled separately via `merge_centre_tol_factor` and `merge_radius_tol_pct` in `config.toml` under `[label]`; there is no CLI override for these.

## Output

The labelled MRC is written in the output directory (default: current working directory) under `evaluator/label/`, following the naming convention below:

```sh
# Output naming convention
{input filename stem}_labelled.mrc

# Example: labelling tomo_seg.mrc
Labelled MRC saved to: evaluator/label/tomo_seg_labelled.mrc
```

If a file with this name already exists, a numeric suffix is appended (`tomo_seg_labelled-1.mrc`, and so on).

### Labelled MRC format

The output MRC contains one integer value per voxel: `0` for background, and a unique positive integer for each connected membrane component. The voxel size from the input MRC header is preserved in the output header.

The integer label assigned to each component in the labelled MRC corresponds directly to the `label` column in the `analyse` CSV output, and to the label values used by `visualise overlay`. This is only guaranteed where the labelled MRC is used as the input to `analyse` and/or `visualise overlay`.

### Terminal output

A progress bar ("Segmentation files processed") tracks batch progress. With `-v`/`-vv`, per-file log lines report the number of components identified, merged, and retained after filtering:

```
label | 92 components identified.
label | 74 components retained after merge/filter.
```


<br>

---
<p align="right"><a href="#evaluator---label">^ Back to top</a></p>
