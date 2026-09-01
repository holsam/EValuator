<div align="right">

![Version][version-shield]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]

</div>

# EValuator
A command line tool for automated morphological analysis and visualisation of extracellular vesicles (EVs) from cryo-electron tomography (cryo-ET) data.

## Overview
EValuator is a cryo-ET post-processing tool, primarily designed for use in quantitative morphological analysis of EVs from binary segmentation masks produced by [MemBrain-seg](https://github.com/teamtomo/membrain-seg) from denoised, CTF-corrected cryo-ET tomograms. It was developed for the analysis of isolated EV preparations imaged by cryo-ET, but may be applicable to other membrane-bound structures of comparable scale (tens to hundreds of nm).

EValuator provides several commands:

| Group | Command | Description |
|---|---|---|
| Component Identification| [`label`](docs/label.md) | Identified connected components from a tomogram and outputs a labelled MRC file for use with other EValuator commands.|
| Component Modelling | [`model`](docs/model.md) | Fits least-squares sphere/ellipsoid models to labelled EVs and gates each fit on reliability. |
| Component Analysis|  [`analyse`](docs/analyse.md) | Run a morphological analysis pipeline on one or more labelled segmentation files and write results to a CSV. |
| Component Analysis|  [`plot`](docs/plot.md) | Generate plots and summary tables from `analyse` and/or `model` output. |
| Component Visualisation| [`visualise`](docs/visualise.md) | Generate various visualisations of tomograms and/or segmentation masks. |
| Component Visualisation| [`viewer`](docs/viewer.md) | Launch the interactive vesicle viewer. |


## Installation
EValuator requires Python 3.14 or later, and uses [uv](https://docs.astral.sh/uv/) as its package manager. If `uv` is not already installed, follow the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/). 

The EValuator repository should be cloned as below, and then follow the instructions in either [Run using uvx](#run-using-uvx) or [Full installation](#full-installation).
```sh
# Clone EValuator repository
git clone https://github.com/holsam/EValuator.git
```

### Run using uvx
EValuator can now be run as below.
```sh
# Run EValuator using uvx
uvx EValuator --help
```
Note that `uvx` must be prepended before any EValuator command, unless the instructions in [Full installation](#full-installation) are followed.

### Full installation
To fully install EValuator, run the following commands. Once installed, it wil be available in your terminal by using the `evaluator` command.
```sh
# Install 
cd EValuator
uv tool install .
# Use EValuator
evaluator --help
```

## Usage
```
Usage: evaluator [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose   Show progress in terminal.
  -vv, --debug    Show debug messages in terminal (implies --verbose).
  --help          Show this message and exit.

Component Identification:
  label       Label connected components in a segmentation MRC

Component Modelling:
  model       Model labelled EVs using a least squares fit approach

Component Analysis:
  analyse     Run morphological analysis pipeline on labelled MRC files
  plot        Generate plots from evaluator analyse and/or model output

Component Visualisation:
  viewer      Launch the interactive 3D vesicle viewer
  visualise   Generate visualisations from MRC data

Utilities:
  config      Create or edit an EValuator configuration file
  license     Print EValuator license
  tools       Animation, benchmarking and miscellaneous tools
  version     Print current EValuator version
```

Use `evaluator COMMAND --help` for detailed usage information for each command or see the full documentation for each command, including all options and output file descriptions, in the [`docs/`](docs/) directory:
- [`docs/analyse.md`](docs/analyse.md)
- [`docs/config.md`](docs/config.md)
- [`docs/label.md`](docs/label.md)
- [`docs/model.md`](docs/model.md)
- [`docs/plot.md`](docs/plot.md)
- [`docs/viewer.md`](docs/viewer.md)
- [`docs/visualise.md`](docs/visualise.md)

## Workflow
EValuator is structured around a three-step workflow. Each step produces output that feeds into the next:

```
 MemBrain-seg segmentation (.mrc)
           │
           ▼
    evaluator label                                 →  labelled MRC  (<stem>_labelled.mrc)
           │
           ├──▶ evaluator analyse                   →  morphology CSV (evaluator-analyse_results.csv)
           │            │   │
           │            │   └──▶ evaluator plot     →  plots + summary tables (evaluator/plot/)
           │            ▼        ▲
           │            evaluator visualise overlay →  overlay image (<stem>_overlay-<style>.png)
           │                     │       
           │                     │
           └──▶ evaluator model  ┘                  →  fit results + fitted MRC (model_results.json/csv, model_fitted.mrc)
```

**Step 1: `label`**: assigns a unique integer label to each connected membrane component in a binary segmentation mask, merges components that are likely split parts of the same EV, filters out components by arc-coverage and size, and writes the result as a labelled MRC file. This is a required pre-processing step before `analyse` and `model`.

**Step 2a: `model`**: fits a least-squares sphere and, where the data support it, an ellipsoid to each labelled EV, gates the fit on reliability (RMSE, point count, surface coverage), and writes the per-vesicle fit parameters plus a rasterised fitted MRC of the reliable vesicles for visual QC.

**Step 2b: `analyse`**: runs the morphological analysis pipeline on a labelled MRC (or directory of labelled MRCs) and extracts quantitative measurements for each identified EV, writing the results to a CSV file.

**Step 3: `visualise overlay`**: reads the labelled MRC and the `analyse` CSV and renders a colour-coded overlay of the identified EVs onto slices of the original greyscale tomogram, for visual inspection of pipeline results.

In addition, the `visualise movie` and `visualise isoview` subcommands can be used independently at any stage to quickly inspect MRC data, and `viewer` launches an interactive viewer which links `label`, `model` and `analyse` outputs for a directory of results.

**(optional) Step 4: `plot`**: generates plots and summary tables from `analyse` and/or `model` output.

### Batch processing
`label`, `model`, `analyse`, `visualise movie`, and `visualise isoview` all accept individual MRC files or a directory containing multiple MRC files. In the latter case, each valid MRC file is processed independently across worker processes, skipping invalid files (logged to terminal). The number of parallel jobs can be controlled via:
1. `-j`/`--jobs` on the command line (highest priority)
2. `max_workers` under the relevant section (`[label]`, `[model]`, `[analyse]`, `[visualise]`) of `config.toml`
3. If unset or `0`, all available CPU cores are used

```sh
# Cap analysis at 4 worker processes for this run only
evaluator analyse evaluator/label/ -j 4
```

## Quick start examples
```sh
# Step 1: label connected components in a MemBrain-seg segmentation mask
evaluator label tomo_seg.mrc

# Fit least-squares models to the labelled EVs (in parallel with Step 2)
evaluator model evaluator/label/tomo_seg_labelled.mrc

# Step 2: run the morphological analysis pipeline on the labelled MRC
evaluator analyse evaluator/label/tomo_seg_labelled.mrc

# Step 3: overlay identified EVs onto the original tomogram
evaluator visualise overlay tomo.mrc evaluator/label/tomo_seg_labelled.mrc \
    -c evaluator/analyse/evaluator-analyse_results.csv

# Optionally: generate summary plots from analyse (and/or model) output
evaluator plot --analyse evaluator/analyse/evaluator-analyse_results.csv --all

# Optionally: inspect raw MRC data
evaluator visualise movie tomo.mrc
evaluator visualise isoview tomo_seg.mrc
```

Verbosity flags are set on the root `evaluator` command and apply to all subcommands:

```sh
evaluator -v analyse evaluator/label/     # progress messages
evaluator -vv analyse evaluator/label/    # debug messages
```

## Configuration
EValuator runs using options defined in a configuration file `.../evaluator/config.toml`, which can be created and edited using the `evaluator config` command. If command-line options are provided which conflict with the configuration file, EValuator will use the provided options and save these to a `.../evaluator/<command>/params.toml` file but will not edit the `.../evaluator/config.toml` file. See the [`config` documentation](docs/config.md) for full details.


## Getting Help & Contributing
If you come across any bugs/issues while using EValuator, or if you have a feature request, please open an issue [here][issues-url].

Any contributions to this project are also very welcome! To contribute, please fork the repo, commit any changes, and then open a pull request.

To set up a development environment, with all dependencies installed into a local virtual environment:
```sh
git clone https://github.com/holsam/EValuator.git
cd EValuator
uv sync
```

## License

This repository is distributed under the GPL-3.0 license. See [LICENSE][license-url] for more information.

<br>

---
<p align="right"><a href="#evaluator">^ Back to top</a></p>



<!-- MARKDOWN LINKS & IMAGES -->
[version-shield]: https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/holsam/EValuator/refs/heads/main/pyproject.toml&query=$.project.version&style=for-the-badge&label=Current%20version&color=important
[issues-shield]: https://img.shields.io/github/issues/holsam/EValuator.svg?style=for-the-badge&color=critical
[issues-url]: https://github.com/holsam/EValuator/issues
[license-shield]: https://img.shields.io/github/license/holsam/EValuator.svg?style=for-the-badge&color=informational
[license-url]: https://github.com/holsam/EValuator/blob/main/LICENSE
