# EValuator - label

## Overview
The `label` command assigns a unique integer label to each connected membrane component in a binary segmentation mask and writes the result as a labelled MRC file. It is the first step in the EValuator workflow and should be run before [`analyse`](analyse.md).

Labelling is performed using face-only (6-connectivity) 3D connected-component labelling, which is less prone to merging spatially adjacent but structurally separate components than the full 26-connectivity alternative.

The output labelled MRC can be passed directly to `analyse` for morphological measurements, and to `visualise overlay` for visual inspection of the results.


## Usage

```
Usage: evaluator label [OPTIONS] SEGMENTATION

Arguments:
  SEGMENTATION  Path to a binary segmentation MRC file (e.g. output of
                MemBrain-seg).  [required]

Options:
  -o, --out-dir PATH  Path to output directory. The labelled MRC will be
                      written under '.../evaluator/results/label/'.
                      [default: .]
  -h, --help          Show this message and exit.
```

Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `label` subcommand:

```sh
evaluator -v label segmentation.mrc
evaluator -vv label segmentation.mrc

```
### Input

`label` requires a single binary segmentation MRC file as input. This is expected to be the output of [MemBrain-seg](https://github.com/teamtomo/membrain-seg), and should contain only two unique values (typically `0` and `1`). The file is read in permissive mode to accommodate minor header inconsistencies common in cryo-ET data.

## Output

The labelled MRC is written in the output directory (default: current working directory) under `evaluator/results/label/`, following the naming convention below:

```sh
# Output naming convention
{input filename stem}_labelled.mrc

# Example: labelling tomo_seg.mrc
Labelled MRC saved to: evaluator/results/label/tomo_seg_labelled.mrc
```

If a file with this name already exists, a numeric suffix is appended (`tomo_seg_labelled-1.mrc`, and so on).

### Labelled MRC format

The output MRC contains one integer value per voxel: `0` for background, and a unique positive integer for each connected membrane component. The voxel size from the input MRC header is preserved in the output header.

The integer label assigned to each component in the labelled MRC corresponds directly to the `label` column in the `analyse` CSV output, and to the label values used by `visualise overlay`. This is only guaranteeed where the labelled MRC is used as the input to `analyse` and/or `visualise overlay`.

### Terminal summary output

Once `label` has completed, a short summary is printed to the terminal:

```
87 components labelled.
Labelled MRC saved to: .../evaluator/results/label/tomo_seg_labelled.mrc
```


<br>

---
<p align="right"><a href="#evaluator---label">^ Back to top</a></p>
