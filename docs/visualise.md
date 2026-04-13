# EValuator - visualise

## Overview
The `visualise` command generates visual outputs from MRC data. It has three subcommands, each serving a distinct purpose:

| Subcommand | Input | Output |
|---|---|---|
| [`movie`](#movie) | Any MRC file (tomogram or segmentation mask) | Z-stack movie (`.mp4` or `.gif`) |
| [`isoview`](#isoview) | Binary segmentation mask MRC | Isometric 3D surface render (`.png`) |
| [`overlay`](#overlay) | Tomogram MRC + labelled MRC + analyse CSV | Colour-coded EV overlay image |

`movie` and `isoview` are standalone tools for quick data inspection and can be used independently at any point. `overlay` is the final step of the EValuator workflow, intended for visual validation of the `analyse` pipeline results.


## `movie`

### Overview

Generates a Z-stack movie where each frame is one XY slice of the input MRC volume, with Z advancing over time. Works with both greyscale tomograms and binary segmentation masks.

The movie is saved as `.mp4` if [FFmpeg](https://ffmpeg.org) is available on the system (`ffmpeg` must be on the `PATH`). If FFmpeg is not available, EValuator falls back to saving a `.gif` using [Pillow](https://pillow.readthedocs.io).

### Usage

```
Usage: evaluator visualise movie [OPTIONS] INPUT

Arguments:
  INPUT       Path to an MRC file.  [required]

Options:
  -o, --out-dir PATH  Path to output directory. Results will be written under
                      '.../evaluator/results/visualise/'.  [default: .]
  --fps INTEGER       Frame rate for the Z-stack movie.  [default: 45; ≥0]
  -h, --help          Show this message and exit.
```

### Input

`movie` accepts a single MRC file. The file type is detected automatically:

- **Greyscale tomogram**: contrast is normalised to [0, 1] by clipping to the 1st-99th percentile before display, to avoid contrast collapse from outlier voxels.
- **Segmentation mask**: displayed as a binary (`binary_r`) colourmap.

### Options

#### `--fps`

Frame rate (frames per second) for the Z-stack movie. The default of 45 fps gives a smooth preview for typical cryo-ET tomograms with a few hundred Z-slices.

### Output

```sh
# Output naming convention
{input filename stem}_Zstack-movie.{mp4|gif}

# Example
Z-stack movie saved to: .../evaluator/results/visualise/tomo_1_Zstack-movie.mp4
```

If a file with this name already exists, a numeric suffix is appended. Each frame's title shows the current Z position in nm (if voxel size is available from the MRC header) or in voxels otherwise.

---

## `isoview`

### Overview

Generates a static isometric 3D surface render of a binary segmentation mask using the marching cubes algorithm. Only available for binary segmentation masks; the command will not produce meaningful output for greyscale tomograms.

The membrane surface mesh is rendered as a `Poly3DCollection` in `matplotlib` using a light-blue colour, viewed from the standard isometric camera angle (45° azimuth, ~35.3° elevation). Axis labels show physical dimensions in nm if voxel size is available, otherwise in voxels.

### Usage

```
Usage: evaluator visualise isoview [OPTIONS] INPUT

Arguments:
  INPUT            Path to a binary segmentation mask MRC file.  [required]

Options:
  -o, --out-dir PATH    Path to output directory. Results will be written under
                        '.../evaluator/results/visualise/'.  [default: .]
  --downsample INTEGER  Downsampling factor applied before isometric surface
                        rendering.  [default: 2; ≥1]
  -h, --help            Show this message and exit.
```

### Options

#### `--downsample`

Integer downsampling factor applied to the volume before computing the isometric surface render. Marching cubes is computationally expensive on large volumes; downsampling reduces this at the cost of surface smoothness. The default factor of 2 subsamples every other voxel in each dimension. Set to `1` to disable downsampling (not recommended for large volumes).

### Output

```sh
# Output naming convention
{input filename stem}_isometric-view.png

# Example
Isometric render saved to: .../evaluator/results/visualise/tomo_seg_isometric-view.png
```

If a file with this name already exists, a numeric suffix is appended.

---

## `overlay`

### Overview

Overlays colour-coded EV segmentations onto slices of the corresponding cryo-ET tomogram and saves the result as an image. It is intended as a quick visual check that the `analyse` pipeline has correctly identified and measured the EVs in a given tomogram.

`overlay` requires the labelled MRC produced by [`evaluator label`](label.md) and the CSV produced by [`evaluator analyse`](analyse.md). Only components whose `label` value appears in the CSV (matched by filename) are rendered — components that were filtered out during `analyse` are not shown.

By default, `overlay` renders a tiled panel of evenly-spaced Z-slices spanning the full depth of the tomogram. A single Z-slice can be requested using `--slice`. The overlay style (filled regions, contour outlines, or both) can also be controlled.

### Usage

```
Usage: evaluator visualise overlay [OPTIONS] TOMOGRAM LABELLED

Arguments:
  TOMOGRAM  Path to the unsegmented tomogram as an MRC file.  [required]
  LABELLED  Path to the corresponding labelled component MRC (output of
            label).  [required]

Options:
  -c, --csv PATH              Path to the corresponding EValuator analyse
                              output CSV. Only EV components listed in this
                              CSV will be overlaid.  [required]
  -o, --out-dir PATH          Path to output directory. Results will be written
                              under '.../evaluator/results/visualise/'.
                              [default: .]
  -f, --out-format [png|jpg|tiff]
                              File format to save the output image as.
                              [default: png]
  -s, --style [both|filled|outlined]
                              Overlay style.  [default: both]
  --slice INTEGER             Render a single Z-slice at this index instead of
                              a tiled panel.  [≥0]
  --n-slices INTEGER          Number of evenly-spaced slices in the tiled panel.
                              [default: 9; ≥0]
  --export-mp4                Export a Z-stack MP4 (or GIF fallback) of the
                              overlay alongside the static image.
  -h, --help                  Show this message and exit.
```

### Input

`overlay` requires three inputs:

- **`TOMOGRAM`**: the original greyscale cryo-ET tomogram (`.mrc`), used as the background image in all panels.
- **`LABELLED`**: the labelled component MRC produced by `evaluator label`. This must have the same shape as the tomogram.
- **`--csv`**: the `evaluator-analyse_results.csv` file produced by `evaluator analyse`. The CSV is used to determine which connected components should be rendered as EVs. Only components whose `tomogram` field matches the labelled MRC filename and whose `label` value is present in the CSV are overlaid.

The tomogram and labelled MRC files must have identical dimensions. If they do not, `overlay` will exit with an error.

### Options

#### `--style`

Controls the appearance of the overlay:

| Style | Description |
|---|---|
| `both` | Semi-transparent filled regions and contour outlines, with component label numbers at centroids. This is the default. |
| `filled` | Semi-transparent filled regions only, with label numbers at centroids. |
| `outlined` | Contour outlines only (using `skimage.measure.find_contours`), with label numbers at contours. |

Each EV component is assigned a unique colour from the `tab20` matplotlib colourmap. Colours cycle if there are more than 20 components.

#### `--n-slices`

Controls how many Z-slices appear in the tiled panel. Slices are selected by `numpy.linspace` across the full Z range of the tomogram, giving an evenly-spaced overview of the full depth. Slices are arranged in a roughly square grid. The default of 9 slices fits a 3×3 grid. This option has no effect if `--slice` is used.

#### `--slice`

Renders a single Z-slice at the given index instead of the tiled panel. The index must be within the valid Z range of the tomogram (`0` to `n_z - 1`). If the index is out of range, `overlay` exits with an error.

#### `--export-mp4`

When supplied, renders an additional Z-stack movie of the overlay (saved as `.mp4` if FFMpeg is available, otherwise `.gif`). The movie scrolls through all XY slices with the EV overlay applied.

### Output

Image files are written in the output directory (default: current working directory) under `evaluator/results/visualise/`, following the naming convention below:

```sh
# Output naming convention
{tomogram filename stem}_overlay-{overlay style}.{image format}

# Example: overlaying tomo_denoised_1.mrc with options: -f png -s both
Image saved to: evaluator/results/visualise/tomo_denoised_1_overlay-both.png
```

If a file with this name already exists, a numeric suffix is appended (`tomo_denoised_1_overlay-both-1.png`, and so on).

### Tiled panel output

The tiled panel shows each selected Z-slice as a greyscale background with the EV overlay applied. Each tile is annotated with its Z-index in the top-left corner. A shared legend listing each EV label and its assigned colour is placed below the panel.

### Single-slice output

The single-slice image shows the full XY extent of the tomogram at the selected Z-index, with the overlay and a legend placed in the lower-right corner.

### Image settings

Default image settings are as follows:

- Image resolution: 300 dpi
- Overlay fill opacity: 0.35
- Outline (contour) line width: 1.0
- Label font size: 6

<br>

---
<p align="right"><a href="#evaluator---visualise">^ Back to top</a></p>
