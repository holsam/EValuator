# EValuator - label

## Overview
The `label` command overlays EV segmentations onto slices of the corresponding cryo-ET tomogram and saves the result as an image. It is intended as a quick visual check that the `analyse` pipeline has correctly identified and measured the EVs in a given tomogram, and as a means of inspecting which components have been accepted or rejected.

By default, `label` renders a tiled panel of evenly-spaced Z-slices spanning the full depth of the tomogram. A single Z-slice can instead be requested using `--slice`. The overlay style (filled regions, contour outlines, or both) can also be controlled.

## Usage
```
Usage: evaluator label [OPTIONS] TOMOGRAM SEGMENTATION

Arguments:
  TOMOGRAM      Path to the unsegmented tomogram as an MRC file.  [required]
  SEGMENTATION  Path to the corresponding segmented tomogram as an MRC file.
                [required]

Options:
  -c, --csv PATH              Path to the corresponding EValuator analyse
                              output CSV. Only EV components listed in this
                              CSV (for the given segmentation filename) will be
                              overlaid.  [required]
  -o, --out-dir PATH          Path to output directory. Results will be written
                              under '.../evaluator/results/label/'.
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
  -h, --help                  Show this message and exit.
```

### Input
`label` requires three inputs:

- **`TOMOGRAM`**: the original greyscale cryo-ET tomogram (`.mrc`), used as the background image in all panels.
- **`SEGMENTATION`**: the MemBrain-seg binary segmentation mask (`.mrc`) corresponding to the tomogram. This must have the same shape as the tomogram.
- **`--csv`**: the `evaluator-analyse_results.csv` file produced by `evaluator analyse`. The CSV is used to determine which connected components in the segmentation should be considered EVs — only components whose `tomogram` field matches the segmentation filename and whose `label` value is present in the CSV are overlaid. Components that were filtered out during `analyse` are not shown.

The tomogram and segmentation files must have identical dimensions. If they do not, `label` will exit with an error.

### Options
#### `--style`
Controls the appearance of the overlay:
| Style | Description |
|---|---|
| `both` | Semi-transparent filled regions and contour outlines, with component label numbers at centroids. This is the default. |
| `filled` | Shows semi-transparent filled regions only, with label numbers at centroids. |
| `outlined` | Contour outlines only (using `skimage.measure.find_contours`), with label numbers at contours. |


Each EV component is assigned a unique colour from the `tab20` matplotlib colormap. Colours cycle if there are more than 20 components.

#### `--n-slices`
Controls how many Z-slices appear in the tiled panel. Slices are selected by `numpy.linspace` across the full Z range of the tomogram, so the panel gives an evenly-spaced overview of the full depth. Slices are arranged in a roughly square grid. The default of 9 slices fits a 3×3 grid. This option has no effect if `--slice` is used.

#### `--slice`
Renders a single Z-slice at the given index instead of the tiled panel. The index must be within the valid Z range of the tomogram (`0` to `n_z - 1`). If the index is out of range, `label` exits with an error.

## Output
Image files are written in the output directory (default: current working directory) under `evaluator/results/label`, following the naming convention below:
```sh
# Output naming convention
{tomogram filename}_overlay-{overlay style}.{image format}

# Example: labelling file tomo_denoised_1.mrc with options: -f png -s both
Image saved to: evaluator/results/label/tomo_denoised_1_overlay-both.png
```
If a file with this name already exists, a numeric suffix is appended (`tomo_denoised_1_overlay-both-1.png`, and so on).

### Tiled panel output
The tiled panel shows each selected Z-slice as a greyscale background with the EV overlay applied. Each tile is annotated with its Z-index in the top-left corner. A shared legend listing each EV label and its assigned colour is placed below the panel.
### Single-slice output
The single-slice image shows the full XY extent of the tomogram at the selected Z-index, with the overlay and a legend in the lower-right corner.
### Image settings
Default image settings are as follows:
- Image resolution: 300 dpi
- Overlay fill opacity: 0.35
- Outline (contour) line width: 1.0
- Label font size: 6
<br>

---
<p align="right"><a href="#evaluator---label">^ Back to top</a></p>
