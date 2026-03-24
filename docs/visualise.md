# EValuator - visualise

## Overview
The `visualise` command generates quick visual outputs from a single MRC file — either a greyscale tomogram or a binary segmentation mask. It automatically detects which type of input has been provided and adjusts its output accordingly. Two outputs can be produced, a Z-stack movie and an isometric 3D surface render, see [Output](#output) for more information on these.

## Usage
```
Usage: evaluator visualise [OPTIONS] INPUT

Arguments:
  INPUT       Path to an MRC file (either a greyscale tomogram or a binary
              segmentation mask).  [required]

Options:
  -o, --out-dir PATH    Path to output directory. Results will be written under
                        '.../evaluator/results/visualise/'.  [default: .]
  --fps INTEGER         Frame rate for the Z-stack movie.  [default: 45; ≥1]
  --downsample INTEGER  Downsampling factor applied before isometric surface
                        rendering.  [default: 2; ≥1]
  --no-movie            Skip Z-stack movie generation.
  --no-iso              Skip isometric view generation (only has an effect if
                        the input is a segmentation mask).
  -h, --help            Show this message and exit.
```
### Input
`visualise` accepts a single MRC file as input. The file type is detected automatically: a volume is treated as a binary segmentation mask if it contains only two unique values (typically `0` and `1`); otherwise it is treated as a greyscale tomogram.

- **Greyscale tomogram**: contrast is normalised to [0, 1] by clipping to the 1st–99th percentile before display, to avoid contrast collapse from outlier voxels.
- **Segmentation mask**: displayed as a binary (`binary_r`) colourmap in the Z-stack movie. The isometric render is also available (see below).

### Options
#### `--fps`
Frame rate (frames per second) for the Z-stack movie. Higher values produce faster-moving movies. The default of 45 fps gives a smooth preview for typical cryo-ET tomograms with a few hundred Z-slices.

#### `--downsample`
Integer downsampling factor applied to the volume before computing the isometric surface render. Marching cubes is computationally expensive on large volumes; downsampling reduces this at the cost of surface smoothness. The default factor of 2 subsamples every other voxel in each dimension. Set to `1` to disable downsampling (not recommended for large volumes). This option only affects the isometric render, not the Z-stack movie.

#### `--no-movie`
Skip Z-stack movie generation entirely. Useful if only the isometric render is needed.

#### `--no-iso`
Skip isometric render generation. Has no effect if the input is a greyscale tomogram (the isometric render is not available for non-mask inputs regardless).

## Output
Output files are written in the output directory (default: current working directory) under `evaluator/results/visualise`, following the naming convention below:
```sh
# Output naming convention
{input filename}_{output type}.{file format}

# Example: visualising segmentation mask tomo_seg_1.mrc
Z-stack movie saved to: /evaluator/results/visualise/tomo_seg_1_Zstack-movie.mp4
Isometric render saved to: /evaluator/results/visualise/tomo_seg_1_isometric-view.png

# Example: visualising greyscale tomogram tomo_1.mrc
Z-stack movie saved to: /evaluator/results/visualise/tomo_1_Zstack-movie.mp4
```
If a file with this name already exists, a numeric suffix is appended (`{input filename}_{output type}-1.{file format}`, and so on).
### Z-stack movie
This is an animated film where each frame is one XY slice, with Z advancing over time. This is generated for both tomograms and segmentation masks.

The movie is saved as `.mp4` if [FFmpeg](https://ffmpeg.org) is available on the system (`ffmpeg` must be on the `PATH`). If FFmpeg is not available, EValuator falls back to saving a `.gif` using [Pillow](https://pillow.readthedocs.io). The current frame's Z-index (and physical Z position in nm, if voxel size is known) is shown in the title of each frame.
### Isometric 3D surface render
This is a static image of the segmented membranes rendered as a 3D surface mesh, viewed from a standard isometric camera angle. This is only available when the input is a binary segmentation mask.

The render is generated using the marching cubes algorithm (implemented in `skimage.measure.marching_cubes`) which extracts the membrane surface mesh, before being rendered as a 3D `Poly3DCollection` in `matplotlib` using a light-blue colour. The camera is set to the standard isometric viewing angle (45° azimuth, ~35.3° elevation). Axis labels show physical dimensions in nm if voxel size is available, otherwise in voxels.

### Terminal summary output
Once the `visualise` command has completed, a short summary is printed to the terminal:
```
EValuator visualise summary
- Volume shape (Z, Y, X): (450, 1023, 1440)
- Volume type: greyscale tomogram
- Voxel size: 2.0000 nm
- Z-stack movie saved as: tomo_1_Zstack-movie.mp4
Result(s) saved to: .../evaluator/results/visualise/
```
<br>

---
<p align="right"><a href="#evaluator---visualise">^ Back to top</a></p>