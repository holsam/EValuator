# EValuator - viewer

## Overview
The `viewer` command launches an interactive browser-based viewer for inspecting EValuator outputs. `viewer` can be used at any point in the EValuator analysis pipeline, and does not write to `evaluator/config.toml`. Its only output is an optional filtered CSV (see [Output](#output)).

Using `viewer` requires additional dependencies defined in the `viewer` dependency group, which can be installed by appending the flag `--extra viewer` (or `--all-extras`) to the EValuator installation command.

## Usage
```
Usage: evaluator viewer [OPTIONS] [ROOT]

Arguments:
  [ROOT]  Root directory to scan for evaluator output (label/model/analyse); can also be chosen from within the viewer.  [default: current working directory]

Options:
  --port INTEGER          Local port for the Streamlit server. [default: 0 (resolved by the OS)]
  --streamlit-bin PATH    Path to the streamlit binary. [default: resolved from PATH]
  -h, --help              Show this message and exit.
```
The Streamlit server hosting the viewer will run in the foreground, and can be stopped using `Ctrl+C`.

Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `viewer` subcommand:

```sh
evaluator -v viewer     # includes Streamlit startup log
evaluator -vv viewer    # includes per-request logs
```

### Input

`viewer` accepts a single argument, `ROOT`, which specifies the directory to search for EValuator outputs. It can also be set/changed from within the Gallery page of the viewer.

### Options

#### `--port`
The local port to use for accessing the Streamlit server/viewer. The default (`0`) lets the OS pick any free port. If a non-zero port is provided but already in use, a warning will be logged and the server started on an OS-assigned port.

#### `--streamlit-bin`
Path to the `streamlit` executable. It should not be necessary to use this option as `streamlit` should be resolved from `PATH`, but can be used if viewer dependencies are installed in a non-`PATH` environment.

## Resolved directories
`viewer` resolves each tomogram's related files from common sub-folder names under `ROOT`:

| Stage | Looked for under `ROOT` | Provides |
|---|---|---|
| `raw` | `raw/`, `raw_tomograms/`, `tomograms/` | Raw greyscale tomogram MRC |
| `segmentations` | `segmentations/`, `segmented/`, `segment/`, `seg/` | Binary segmentation mask MRC |
| `labelled` | `labelled/`, `evaluator/label/`, `label/` | Labelled component MRC (output of `label`) |
| `model` | `model/`, `evaluator/model/` | Fitted MRC and results JSON (output of `model`) |
| `analyse` | `analyse/`, `evaluator/analyse/`, `analysis/` | `evaluator-analyse_results.csv` (output of `analyse`) |

Any directory that is not found can be set manually on the Gallery page.

Results are resolved per tomogram stem: raw/segmentation/labelled MRCs are matched by filename (with `_seg`/ `_segmented` and `_labelled` suffixes stripped) and model/analyse rows are matched by their `source_file`/`tomogram` field. If a tomogram has any associated outputs, it will appear in Gallery, with missing stages left blank.

## Pages
### Gallery
This is `viewer`'s main landing page, where resolved directories can be configured and results previewed.

A results table provides an overview of each tomogram: number of vesicles identified, number/percentage of reliable fits (if `model` output available), which outputs were identified. A thumbnail gallery shows the mid-Z slice for each tomogram volume.

Selecting a row or thumbnail will open that tomogram's [Tomogram](#tomogram) page for further information.

### Tomogram
This is `viewer`'s per-tomogram detail page. It contains the following sections:
- **Metadata:** resolved file paths for the tomogram, with option to add any missing paths.
- **Viewer:** an interactive 3D pane showing the selected volume, alongside smaller non-interactive panes showing the other volumes in the same orientation.
- **Results:** the outputs of `analyse` and `model` (if available) joined by each vesicle's label ID.
- **Plots:** several tabs containing interactive plots showing concordance, reliability, distributions and features.
- **Export:** utility buttons to export filtered selections (see [below](#output))

#### Selecting vesicles
Individual vesicles can be selected in three ways:
1. Clicking on the vesicle in the interactive 3D viewer.
2. Selecting the vesicle's row in either the `analyse` or `model` results tables.
3. Box/lasso-selecting points in a plot.

## Output
`viewer` typically does not write any output files, but does include a feature to export filtered tomogram data:
- Download CSV: download the joined analyse/model rows for currently selected vesicles.
- Export CSV to `evaluator/analyse/` (if analyse results were found): write a filtered copy of analyse results (selected vesicles only) next to the source CSV with the suffix `_filtered`. If a file with this name already exists, a numeric suffix is appended as well.

## Customising viewer appearance
A **Customise theme** popover is pinned to the bottom-right of every page. This provides several named palettes (Okabe-Ito [default], Brewer Set2, Viridis, Grayscale and Neon) and a **Custom** option that allows each colour used in the viewer to be customised.

<br>

---
<p align="right"><a href="#evaluator---viewer">^ Back to top</a></p>
