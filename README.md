<div align="right">

[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]

</div>

# CryoET EV Post-Processing Pipeline
A Python pipeline for automated segmentation and morphological analysis of extracellular vesicles (EVs) in cryo-electron tomography (cryo-ET) data.

## Overview
This pipeline takes membrane segmentation masks produced by [MemBrain-seg](https://github.com/teamtomo/membrain-seg) and extracts quantitative morphological measurements for each EV identified in a tomogram. It is designed for use with denoised, CTF-corrected tomograms in `.mrc` format, and supports both single-tomogram and batch (HPC) workflows.

The pipeline was developed for analysis of isolated EV preparations imaged by cryo-ET, but may be applicable to other membrane-bound structures of comparable scale (10s-100s nm).


## Installation
This pipeline can be installed by downloading the source code from the GitHub repository, or by using `git clone` in a terminal. It requires no additional set-up, but please note the following advice before installation:
- This pipeline was developed using Python 3.9.6, but should be compatible with Python versions 3.9+.
- The pipeline requires several Python modules, most of which should be installed already, however it is recommended to install all dependencies via `pip` using the `requirements.txt` file:
    ```sh
    # Install Python module dependencies using requirements.txt
    pip install -r requirements.txt
    ```
- Generating the required membrane segmentation masks will require MemBrain-seg to be run prior to this pipeline. See the [MemBrain-seg documentation](https://membrain-seg.readthedocs.io) for installation and usage instructions as required.

## Usage
```sh
usage: ev-post-processing.py [-h] -i INPUT [-o OUTPUT] [--min-diam MIN_DIAM] [--max-diam MAX_DIAM] [--fill-threshold FILL_THRESHOLD] [-v]

Post-processing pipeline of membrain-seg EV segmentations.
required arguments:
  -i INPUT, --input INPUT           path to either a single segmented .mrc file, or a directory containing segmented .mrc files

optional arguments:
  -o OUTPUT, --output OUTPUT        path to output directory (default: '.')
  --min-diam MIN_DIAM               minimum EV equivalent diameter in nm to use for filtering (default: 20.0)
  --max-diam MAX_DIAM               maximum EV equivalent diameter in nm to use for filtering (default: 500.0)
  --fill-threshold FILL_THRESHOLD   closure fill threshold to use for determining enclosed EVs (default: 0.05)
  -v, --verbosity                   increase verbosity (-v: show info messages; -vv show detailed info messages)
  -h, --help                        show this help message and exit
```

## Outputs

Results are written to a `cryoet-ev_results.csv` file with one row per detected EV. If the pipeline is run several times in the same output directory, subsequent result files will be written to `cryoet-ev_results-{n}.csv` where `{n}` increases by 1 per pipeline run. The following measurements are reported for each EV in all results files:

Column | Description | Units<sup>1</sup>
--|--|--
`tomogram` | File from which EV was identified |
`label` | Unique identifier for EV in the file given by `tomogram` |
`equiv_diameter_nm` | Calculated diameter of a sphere with equivalent volume | nm (rounded to 2 d.p.)
`major_axis_diameter` | Length of longest axis of the best-fit ellipsoid | nm (rounded to 2 d.p.)
`minor_axis_diameter` | Length of shortest axis of the best-fit ellipsoid | nm (rounded to 2 d.p.)
`aspect_ratio` | Ratio of major to minor axis diameters | unitless (rounded to 2 d.p.)
`eccentricity` | Degree of deviation from a sphere | unitless (0 ≤ e ≤ 1; 0 = perfect sphere; rounded to 2 d.p.)
`membrane_volume` | Volume of the segmented membrane | nm<sup>3</sup> (rounded to 2 d.p.)
`lumen_volume` | Volume of the EV lumen | nm<sup>3</sup> (rounded to 2 d.p.)
`surface_area` | Estimated membrane surface area | nm<sup>2</sup> (rounded to 2 d.p.)
`is_enclosed` | Boolean encoding whether EV is fully enclosed |
`closure_fill_ratio` | Measure of membrane closure completeness | unitless (0 < r ≤ 1; rounded to 4 d.p.)
`voxel_size_nm` | Size of voxel in nanometres (as read from MRC file header) |
`measurements_unit` | Units of measurements (nm or vox) |

<sup>1</sup> Units given here assume the voxel size in nanometres was read from the MRC file header. If this is not the case, units will not be scaled to physical units and will be in voxels/voxels<sup>3</sup>.

## Getting Help & Contributing
If you using this project and come across any bugs/issues, or if you have a feature request, please open an issue [here][issues-url]. 

Any contributions to this project are also very welcome! To contribute, please fork the repo, commit any changes, and then create a pull request.

## License

This repository is distributed under the GPL-3.0 license. See [LICENSE][license-url] for more information.

<br>

---
<p align="right"><a href="#cryoet-ev-post-processing-pipeline">^ Back to top</a></p>



<!-- MARKDOWN LINKS & IMAGES -->
[issues-shield]: https://img.shields.io/github/issues/holsam/cryoet-ev-post-processing.svg?style=for-the-badge&color=red
[issues-url]: https://github.com/holsam/cryoet-ev-post-processing/issues
[license-shield]: https://img.shields.io/github/license/holsam/cryoet-ev-post-processing.svg?style=for-the-badge&color=lightgray
[license-url]: https://github.com/holsam/cryoet-ev-post-processing/blob/main/LICENSE