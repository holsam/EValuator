'''
=======================================
EValuator: SEGMENTATION EV LABELLING
=======================================
'''
# ====================
# Import external dependencies
# ====================
import matplotlib, numpy,pandas, typer
import matplotlib.pyplot as plt
import matplotlib.patches as mpatch
from pathlib import Path
from skimage import measure
from typing import Annotated, Literal
matplotlib.use("Agg")

# ====================
# Import EValuator functions and variables
# ====================
from ..main import config, lg
from .. import utils as evalutil

# ====================
# Initialise typer as evaluatorLabel
# ====================
evaluatorLabel = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False
)

# ====================
# Define command: label
# ====================
@evaluatorLabel.command(rich_help_panel="Commands")
def label(
    # --------------------
    # Define CLI arguments
    # --------------------
    # Define tomogram argument: should be a path to a file which exists and is readable
    tomogram: Annotated[
        Path, 
        typer.Argument(help="Path to unsegmented tomogram as MRC.", exists=True,
        file_okay=True,dir_okay=False,readable=True)
    ],
    # Define segmentation argument: should be a path to a file which exists and is readable
    segmentation: Annotated[
        Path, 
        typer.Argument(help="Path to segmented tomogram as MRC.", exists=True,
        file_okay=True,dir_okay=False,readable=True)
    ],
    # --------------------
    # Define CLI options
    # --------------------
    # Define csv option: should be a path to a file which is exists and is readable which, or should be None
    csv: Annotated[
        Path,
        typer.Option("-c", "--csv", help="Path to corresponding EValuator analyse output CSV.", exists=True, file_okay=True, dir_okay=False, readable=True)
    ],
    # Define output option: should be a path which can not exist or is a writeable directory if it exists, and defaults to current working directory
    output: Annotated[
        Path | None, 
        typer.Option("-o", "--out-dir", help="Path to output directory. Output files will be written to this directory under '.../evaluator/results/analyse/'.", file_okay=False,dir_okay=True,writable=True)
    ] = Path("."),
    # Define out_format option: should be either "png" (default), "jpg", or "tiff"
    out_format: Annotated[
        Literal["png", "jpg", "tiff"],
        typer.Option("-f", "--out-format", help="File format to save output image as.")
    ] = "png",
    # Define style option: should be either "both" (default), "filled", or "outlined"
    style: Annotated[
        Literal["both", "filled", "outlined"],
        typer.Option("-s", "--style", help="Overlay style to use in labelled output image.")
    ] = "both",
    # Define slice option: should be an integer which is greater than 0, or None, and defaults to None
    slice: Annotated[
        int | None,
        typer.Option("--slice", help="Render a single Z-slice at this index instead of a tiled panel.", min=0)
    ] = None,
    # Define nslices option: should be an integer which is greater than 0, and defaults to the 'n_slices' value specified in config.toml
    n_slices: Annotated[
        int,
        typer.Option("--n-slices", help="Number of evenly-spaced slices in the tiled panel.", min=0)
    ] = config['label']['n_slices'],
):
    '''
    Labels a cryo-ET tomogram with EV segmentations using ouptut of EValuator analyse.
    '''
    # Check input tomogram MRC file is valid
    lg.debug(f"label | Validating input tomogram file...")
    if not evalutil.validateMRCFile(tomogram):
        # Raise error if not
        raise ValueError(f"{tomogram.name} is not a valid MRC file and will not be processed.")
    else:
        # Otherwise read file
        lg.debug(f"label | Reading input tomogram file...")
        tomo_data, _ = evalutil.readMRCFile(tomogram)
    lg.debug(f"label | Validating input segmentation file...")
    # Check input segmentation MRC file is valid
    if not evalutil.validateMRCFile(segmentation):
        # Raise error if not
        raise ValueError(f"{segmentation.name} is not a valid MRC file and will not be processed.")
    else:
        lg.debug(f"label | Reading input segmentation file...")
        # Otherwise read file
        seg_data, voxel_size_nm = evalutil.readMRCFile(segmentation)
        # Convert seg_data to type boolean
        seg_data = seg_data.astype(bool)
    # Check tomogram and segmentation file are the same size
    lg.debug(f"label | Checking tomogram and segmentation shapes match...")
    if not tomo_data.shape == seg_data.shape:
        raise ValueError(f"Tomogram shape {tomo_data.shape} and segmentation shape {seg_data.shape} do not match.")
    # Extract labels from csv file
    lg.debug(f"label | Reading CSV file...")
    valid_labels = getValidLabelsFromCSV(csv, segmentation.name)
    if not valid_labels:
        raise ValueError(f"No valid EV components identified in {csv.name}.")
    # Label components
    lg.info(f"label | Starting tomogram labelling.")
    lg.debug(f"label | Labelling components...")
    seg_labelled, n_components = evalutil.labelComponents(seg_data)
    lg.info(f"{n_components} total components found in segmentation. {len(valid_labels)} EV components will be overlaid using style: '{style}'.")
    # Assign colours to labels
    lg.debug(f"label | Assigning label colours...")
    label_colours = assignLabelColours(valid_labels)
    # Create output directory structure
    lg.debug(f"label | Creating output directory structure...")
    out_dir = evalutil.generateOutputFileStructure(output, "label")
    # Define output file path
    lg.debug(f"label | Defining output file...")
    out_file = evalutil.checkUniqueFileName(out_dir=out_dir, command="label", orig_name=tomogram.stem, overlay_style=style, fmt=out_format)
    # Render labelled image
    if slice is not None:
        lg.debug(f"label | Rendering and saving single slice image...")
        renderSingleSlice(tomo_data, seg_labelled, valid_labels, label_colours, slice, style, out_file, segmentation.name)
    else:
        lg.debug(f"label | Rendering and saving tiled image...")
        renderTiled(tomo_data, seg_labelled, valid_labels, label_colours, n_slices, style, out_file, segmentation.name)
    

# =========================
# DEFINE FUNCTION: getValidLabelsFromCSV
# =========================
def getValidLabelsFromCSV(csv_path: Path, seg_filename:str):
    '''
    Reads the EValuator analyse output CSV and returns the set of integer component labels that passed the pipeline for the given segmentation filename. If no CSV can be read or no rows have the same filename, returns None.
    '''
    try:
        results = pandas.read_csv(csv_path)
    except Exception as e:
        lg.warning(f"Could not read CSV '{csv_path}': e{e}.")
        return None
    if "tomogram" not in results.columns or "label" not in results.columns:
        lg.warning(f"CSV '{csv_path}' is not in compatible format.")
        return None
    matches = results[results["tomogram"] == seg_filename]
    if matches.empty:
        lg.warning(f"No entries for '{seg_filename}' found in CSV '{csv_path}'.")
        return None
    valid_labels = set(matches["label"].astype(int).tolist())
    return valid_labels

# =========================
# DEFINE FUNCTION: assignLabelColours
# =========================
def assignLabelColours(valid_labels:set) -> dict:
    '''
    Assigns a unique RGBA colour to each valid label using COLORMAP, returning a dictionary mapping labels to RGBA tuples. Colours will cycle if there are more labels than colours.
    '''
    cmap = plt.get_cmap(config['mplstyle']['colourmap'])
    n_colours = cmap.N if hasattr(cmap, "N") else 256
    sorted_labels = sorted(valid_labels)
    return {label: cmap(i % n_colours) for i, label in enumerate(sorted_labels)}

# =========================
# DEFINE FUNCTION: getLabelCentroid2D
# =========================
def getLabelCentroid2D(seg_slice: numpy.ndarray, label: int):
    '''
    Returns the (row, col) centroid of a given label within a 2D segmentation slice, or None if the label is absent from the slice.
    '''
    mask = seg_slice == label
    if not numpy.any(mask):
        return None
    rows, cols = numpy.where(mask)
    return int(rows.mean()), int(cols.mean())

# =========================
# DEFINE FUNCTION: overlayFilled
# =========================
def overlayFilled(ax, seg_slice: numpy.ndarray, valid_labels: set, label_colours: dict):
    '''
    Overlays semi-transparent filled regions for each valid label.
    '''
    # Build an RGBA overlay array and fill each label's pixels
    overlay = numpy.zeros((*seg_slice.shape, 4), dtype=float)
    for label in valid_labels:
        mask = seg_slice == label
        if not numpy.any(mask):
            continue
        colour = label_colours[label]
        overlay[mask, 0] = colour[0]
        overlay[mask, 1] = colour[1]
        overlay[mask, 2] = colour[2]
        overlay[mask, 3] = config['mplstyle']['alpha_fill']
    ax.imshow(overlay, interpolation="nearest")
    # Annotate each visible label with its number at the centroid
    for label in valid_labels:
        centroid = getLabelCentroid2D(seg_slice, label)
        if centroid is not None:
            ax.text(centroid[1], centroid[0], str(label), color="white", fontsize=config['mplstyle']['label_fontsize'], ha="center", va="center", fontweight="bold")

# =========================
# DEFINE FUNCTION: overlayOutlined
# =========================
def overlayOutlined(ax, seg_slice: numpy.ndarray, valid_labels: set, label_colours: dict):
    '''
    Overlays contour outlines for each valid label using skimage.measure.find_contours.
    '''
    for label in valid_labels:
        mask = (seg_slice == label).astype(numpy.uint8)
        if not numpy.any(mask):
            continue
        colour = label_colours[label]
        contours = measure.find_contours(mask, level=0.5)
        for contour in contours:
            ax.plot(contour[:, 1], contour[:, 0], color=colour, linewidth=config['mplstyle']['contour_linewidth'], alpha=0.9)
        # Annotate each visible label at its centroid
        centroid = getLabelCentroid2D(seg_slice, label)
        if centroid is not None:
            ax.text(centroid[1], centroid[0], str(label),color=colour, fontsize=config['mplstyle']['label_fontsize'],ha="center", va="center", fontweight="bold")

# =========================
# DEFINE FUNCTION: overlayBoth
# =========================
def overlayBoth(ax, seg_slice: numpy.ndarray, valid_labels: set, label_colours: dict):
    '''
    Overlays both semi-transparent filled regions and contour outlines (default style). Calls overlay_filled then overlay_contours, so annotations appear on top of fills.
    '''
    overlayFilled(ax, seg_slice, valid_labels, label_colours)
    overlayOutlined(ax, seg_slice, valid_labels, label_colours)

# =========================
# DEFINE FUNCTION: buildLegendPatches
# =========================
def buildLegendPatches(valid_labels: set, label_colours: dict) -> list:
    '''
    Builds a list of matplotlib Patch objects for use in a figure legend,
    one per valid EV label.
    '''
    return [mpatch.Patch(color=label_colours[l], label=f"EV {l}") for l in sorted(valid_labels)]

# =========================
# DEFINE FUNCTION: renderTiled
# =========================
def renderTiled(tomo_data, seg_labelled, valid_labels, label_colours, n_slices, overlay_fn, output_path: Path, seg_name: str):
    '''
    Renders a tiled panel of evenly-spaced Z-slices with segmentation overlay.
    Slices are selected by numpy.linspace across the full Z range, so the panel
    gives an overview of the whole tomogram. Each tile shows:
      - greyscale tomogram slice as background
      - EV overlay (style controlled by OVERLAY_STYLE)
      - Z-index label in the top-left corner
    A shared legend is placed below the panel.
    '''
    n_z = tomo_data.shape[0]
    slice_indices = numpy.linspace(0, n_z - 1, n_slices, dtype=int)
    # Arrange tiles in a roughly square grid
    n_cols = int(numpy.ceil(numpy.sqrt(n_slices)))
    n_rows = int(numpy.ceil(n_slices / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3 * n_cols, 3 * n_rows), facecolor="black")
    axes = numpy.array(axes).flatten()
    for i, z in enumerate(slice_indices):
        ax = axes[i]
        ax.set_facecolor("black")
        tomo_slice = evalutil.normaliseArray(tomo_data[z])
        seg_slice = seg_labelled[z]
        ax.imshow(tomo_slice, cmap="gray", interpolation="nearest", vmin=0, vmax=1)
        overlayBoth(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "both" else None
        overlayFilled(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "filled" else None
        overlayOutlined(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "outlined" else None
        ax.text(4, 4, f"z={z}", color="yellow", fontsize=6, va="top", ha="left")
        ax.axis("off")
    # Hide any unused subplot axes
    for j in range(i + 1, len(axes)):
        axes[j].axis("off")
        axes[j].set_facecolor("black")
    # Shared legend below the panel
    patches = buildLegendPatches(valid_labels, label_colours)
    if patches:
        fig.legend(handles=patches, loc="lower center", ncol=min(len(patches), 10), fontsize=6, framealpha=0.5, facecolor="black", labelcolor="white", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(seg_name, color="white", fontsize=9, y=1.005)
    plt.tight_layout(pad=0.3)
    fig.savefig(output_path, dpi=config['mplstyle']['figure_dpi'], bbox_inches="tight", facecolor="black")
    plt.close(fig)
    lg.info(f"label | Finished labelling tomogram.")
    print(f"Tiled panel ({n_slices} slices) saved to: {output_path}\n")

# =========================
# DEFINE FUNCTION: renderSingleSlice
# =========================
def renderSingleSlice(tomo_data, seg_labelled, valid_labels, label_colours,slice_idx: int, overlay_fn, output_path: Path, seg_name: str):
    '''
    Renders a single Z-slice with segmentation overlay.
    '''
    n_z = tomo_data.shape[0]
    if not (0 <= slice_idx < n_z):
        raise ValueError(f"Slice index {slice_idx} is out of range for tomogram with {n_z} Z-slices (0–{n_z - 1}).")
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), facecolor="black")
    ax.set_facecolor("black")
    tomo_slice = evalutil.normaliseArray(tomo_data[slice_idx])
    seg_slice = seg_labelled[slice_idx]
    ax.imshow(tomo_slice, cmap="gray", interpolation="nearest", vmin=0, vmax=1)
    overlay_fn(ax, seg_slice, valid_labels, label_colours)
    ax.text(4, 4, f"z={slice_idx}", color="yellow", fontsize=8, va="top", ha="left")
    ax.axis("off")
    patches = buildLegendPatches(valid_labels, label_colours)
    if patches:
        ax.legend(handles=patches, loc="lower right", fontsize=7, framealpha=0.5, facecolor="black", labelcolor="white")
    ax.set_title(f"{seg_name}  |  z={slice_idx}", color="white", fontsize=9)
    plt.tight_layout(pad=0.3)
    fig.savefig(output_path, dpi=config['mplstyle']['figure_dpi'], bbox_inches="tight", facecolor="black")
    plt.close(fig)
    lg.info(f"label | Finished labelling tomogram.")
    print(f"Single-slice image (z={slice_idx}) saved to: {output_path}\n")