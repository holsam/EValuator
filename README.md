<div align="right">

![Version][version-shield]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]

</div>

# EValuator
A command line tool for automated morphological analysis and visualisation of extracellular vesicles (EVs) from cryo-electron tomography (cryo-ET) data.

## Overview
EValuator takes membrane segmentation masks produced by [MemBrain-seg](https://github.com/teamtomo/membrain-seg) and extracts quantitative morphological measurements for each EV identified in a tomogram. It was developed for the analysis of isolated EV preparations imaged by cryo-ET, but may be applicable to other membrane-bound structures of comparable scale (tens to hundreds of nm).

EValuator provides three main commands:

| Command | Description |
|---|---|
| [`analyse`](docs/analyse.md) | Run the morphological analysis pipeline on one or more segmentation files and write results to a CSV. |
| [`label`](docs/label.md) | Overlay an EV segmentation onto the corresponding tomogram slices and save as an image. |
| [`visualise`](docs/visualise.md) | Generate a Z-stack movie and/or an isometric 3D surface render of a tomogram or segmentation mask. |

## Prerequisites
EValuator requires membrane segmentation masks in `.mrc` format as an input to the commands `analyse` and `label`. These are produced by [MemBrain-seg](https://github.com/teamtomo/membrain-seg), which should be run separately on denoised and CTF-corrected tomograms prior to using EValuator. See the [MemBrain-seg documentation](https://membrain-seg.readthedocs.io) for installation and usage instructions.

## Installation
EValuator requires Python 3.14 or later, and uses [uv](https://docs.astral.sh/uv/) as its package manager. If `uv` is not already installed, follow the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/). 

EValuator can be installed as a `uv` tool after cloning the repository as below. Once installed, it will be available in your terminal by using the `evaluator` command.
```sh
# Install EValuator using uv
git clone https://github.com/holsam/EValuator.git
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

Commands:
  analyse     Run post-processing pipeline on MemBrain-seg EV segmentation files.
  label       Label a cryo-ET tomogram with EV segmentations.
  visualise   Generate visualisations of tomogram data.

Utility Commands:
  version     Print current EValuator version to terminal and exit.
  license     Print EValuator license to terminal and exit.
```

Use `evaluator COMMAND --help` for detailed usage information for each command or see the full documentation for each command, including all options and output file descriptions, in the [`docs/`](docs/) directory:
- [`docs/analyse.md`](docs/analyse.md)
- [`docs/label.md`](docs/label.md)
- [`docs/visualise.md`](docs/visualise.md)

### Quick start examples
#### Analyse a directory of segmentation files:
```sh
evaluator analyse /path/to/segmentations/ -o /path/to/output/
```

#### Label the corresponding tomogram slices:
```sh
evaluator label tomogram.mrc segmentation.mrc -c evaluator-analyse_results.csv -o /path/to/output/
```

#### Generate a Z-stack movie of a tomogram:
```sh
evaluator visualise tomogram.mrc -o /path/to/output/
```

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
