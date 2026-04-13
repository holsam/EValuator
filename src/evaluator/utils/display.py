'''
=======================================
EValuator: DISPLAY & OVERLAY UTILITIES
=======================================
Functions for array normalisation, colour assignment, and rendering
labelled EV segmentation overlays onto tomogram slices.
Used by the `visualise overlay` subcommand.
'''

# ====================
# Import external dependencies
# ====================
import matplotlib, numpy, pandas
import matplotlib.pyplot as plt
import matplotlib.patches as mpatch
import matplotlib.animation as animation
from pathlib import Path
from skimage import measure
from typing import Optional
matplotlib.use("Agg")

# ====================
# Import internal dependencies
# ====================
from .settings import config, lg

# =========================
# DEFINE FUNCTION: normaliseArray
# =========================
def normaliseArray(data: numpy.ndarray) -> numpy.ndarray:
    '''
    Linearly normalises a 2D array to [0.0, 1.0] for greyscale display.
    Clips to the 1st/99th percentile to avoid outlier-driven contrast collapse.
    Returns a zero array if the slice is constant to avoid division by zero.
    '''
    data = data.astype(float)
    lo = numpy.percentile(data, 1)
    hi = numpy.percentile(data, 99)
    if hi == lo:
        return numpy.zeros_like(data)
    return numpy.clip((data - lo) / (hi - lo), 0.0, 1.0)

# =========================
# DEFINE FUNCTION: getValidLabelsFromCSV
# =========================
def getValidLabelsFromCSV(csv_path: Path, seg_filename: str) -> Optional[set]:
    '''
    Reads the EValuator analyse output CSV and returns the set of integer
    component labels that passed the pipeline for the given segmentation filename.
    Returns None if the CSV cannot be read or contains no matching rows.
    '''
    try:
        results = pandas.read_csv(csv_path)
    except Exception as e:
        lg.warning(f"Could not read CSV '{csv_path}': {e}.")
        return None
    if "tomogram" not in results.columns or "label" not in results.columns:
        lg.warning(f"CSV '{csv_path}' is not in compatible format.")
        return None
    matches = results[results["tomogram"] == seg_filename]
    if matches.empty:
        lg.warning(f"No entries for '{seg_filename}' found in CSV '{csv_path}'.")
        return None
    return set(matches["label"].astype(int).tolist())

# =========================
# DEFINE FUNCTION: assignLabelColours
# =========================
def assignLabelColours(valid_labels: set) -> dict:
    '''
    Assigns a unique RGBA colour to each valid label using the configured colourmap.
    Colours cycle if there are more labels than colours in the map.
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
    Returns the (row, col) centroid of a given label within a 2D segmentation slice,
    or None if the label is absent from the slice.
    '''
    mask = seg_slice == label
    if not numpy.any(mask):
        return None
    rows, cols = numpy.where(mask)
    return int(rows.mean()), int(cols.mean())

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
# DEFINE FUNCTION: overlayFilled
# =========================
def overlayFilled(ax, seg_slice: numpy.ndarray, valid_labels: set, label_colours: dict):
    '''
    Overlays semi-transparent filled regions for each valid label.
    '''
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
        centroid = getLabelCentroid2D(seg_slice, label)
        if centroid is not None:
            ax.text(centroid[1], centroid[0], str(label), color=colour, fontsize=config['mplstyle']['label_fontsize'], ha="center", va="center", fontweight="bold")

# =========================
# DEFINE FUNCTION: overlayBoth
# =========================
def overlayBoth(ax, seg_slice: numpy.ndarray, valid_labels: set, label_colours: dict):
    '''
    Overlays both semi-transparent filled regions and contour outlines.
    Calls overlayFilled then overlayOutlined so annotations appear on top of fills.
    '''
    overlayFilled(ax, seg_slice, valid_labels, label_colours)
    overlayOutlined(ax, seg_slice, valid_labels, label_colours)

# =========================
# DEFINE FUNCTION: renderTiled
# =========================
def renderTiled(tomo_data, seg_labelled, valid_labels, label_colours, n_slices, overlay_fn, output_path: Path, seg_name: str):
    '''
    Renders a tiled panel of evenly-spaced Z-slices with segmentation overlay.
    Slices are selected by numpy.linspace across the full Z range, giving an
    overview of the whole tomogram.
    '''
    n_z = tomo_data.shape[0]
    slice_indices = numpy.linspace(0, n_z - 1, n_slices, dtype=int)
    n_cols = int(numpy.ceil(numpy.sqrt(n_slices)))
    n_rows = int(numpy.ceil(n_slices / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3 * n_cols, 3 * n_rows), facecolor="black")
    axes = numpy.array(axes).flatten()
    for i, z in enumerate(slice_indices):
        ax = axes[i]
        ax.set_facecolor("black")
        tomo_slice = normaliseArray(tomo_data[z])
        seg_slice = seg_labelled[z]
        ax.imshow(tomo_slice, cmap="gray", interpolation="nearest", vmin=0, vmax=1)
        overlayBoth(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "both" else None
        overlayFilled(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "filled" else None
        overlayOutlined(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "outlined" else None
        ax.text(4, 4, f"z={z}", color="yellow", fontsize=6, va="top", ha="left")
        ax.axis("off")
    for j in range(i + 1, len(axes)):
        axes[j].axis("off")
        axes[j].set_facecolor("black")
    patches = buildLegendPatches(valid_labels, label_colours)
    if patches:
        fig.legend(handles=patches, loc="lower center", ncol=min(len(patches), 10), fontsize=6, framealpha=0.5, facecolor="black", labelcolor="white", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(seg_name, color="white", fontsize=9, y=1.005)
    plt.tight_layout(pad=0.3)
    fig.savefig(output_path, dpi=config['mplstyle']['figure_dpi'], bbox_inches="tight", facecolor="black")
    plt.close(fig)
    lg.info(f"overlay | Finished rendering tiled overlay.")
    print(f"Tiled panel ({n_slices} slices) saved to: {output_path}\n")

# =========================
# DEFINE FUNCTION: renderSingleSlice
# =========================
def renderSingleSlice(tomo_data, seg_labelled, valid_labels, label_colours, slice_idx: int, overlay_fn, output_path: Path, seg_name: str):
    '''
    Renders a single Z-slice with segmentation overlay.
    '''
    n_z = tomo_data.shape[0]
    if not (0 <= slice_idx < n_z):
        raise ValueError(f"Slice index {slice_idx} is out of range for tomogram with {n_z} Z-slices (0–{n_z - 1}).")
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), facecolor="black")
    ax.set_facecolor("black")
    tomo_slice = normaliseArray(tomo_data[slice_idx])
    seg_slice = seg_labelled[slice_idx]
    ax.imshow(tomo_slice, cmap="gray", interpolation="nearest", vmin=0, vmax=1)
    overlayBoth(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "both" else None
    overlayFilled(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "filled" else None
    overlayOutlined(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "outlined" else None
    ax.text(4, 4, f"z={slice_idx}", color="yellow", fontsize=8, va="top", ha="left")
    ax.axis("off")
    patches = buildLegendPatches(valid_labels, label_colours)
    if patches:
        ax.legend(handles=patches, loc="lower right", fontsize=7, framealpha=0.5, facecolor="black", labelcolor="white")
    ax.set_title(f"{seg_name}  |  z={slice_idx}", color="white", fontsize=9)
    plt.tight_layout(pad=0.3)
    fig.savefig(output_path, dpi=config['mplstyle']['figure_dpi'], bbox_inches="tight", facecolor="black")
    plt.close(fig)
    lg.info(f"overlay | Finished rendering single slice overlay.")
    print(f"Single-slice image (z={slice_idx}) saved to: {output_path}\n")

# =========================
# DEFINE FUNCTION: renderOverlayMovie
# =========================
def renderOverlayMovie(tomo_data, seg_labelled, valid_labels, label_colours, overlay_fn: str, output_path: Path, seg_name: str):
    '''
    Renders a Z-stack movie scrolling through all XY slices with the EV
    segmentation overlay. Saved as MP4 if FFMpeg is available, else GIF.
    '''
    n_z = tomo_data.shape[0]
    fig, ax = plt.subplots(figsize=(6, 6.5), facecolor="black")
    ax.set_facecolor("black")
    ax.axis("off")
    tomo_slice_0 = normaliseArray(tomo_data[0])
    im = ax.imshow(tomo_slice_0, cmap="gray", interpolation="nearest", vmin=0, vmax=1)
    z_text = ax.text(4, 4, "z=0", color="white", fontsize=8, va="top", ha="left")
    patches = buildLegendPatches(valid_labels, label_colours)
    if patches:
        fig.legend(handles=patches, loc="lower center", fontsize=7,
                   framealpha=0.5, facecolor="black", labelcolor="white",
                   bbox_to_anchor=(0.5, -0.02), ncol=min(len(patches), 10))
        plt.tight_layout(pad=0.3)
    overlay_artists = []
    def update(z):
        nonlocal overlay_artists
        for artist in overlay_artists:
            artist.remove()
        overlay_artists = []
        im.set_data(normaliseArray(tomo_data[z]))
        z_text.set_text(f"z={z}")
        seg_slice = seg_labelled[z]
        overlayBoth(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "both" else None
        overlayFilled(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "filled" else None
        overlayOutlined(ax, seg_slice, valid_labels, label_colours) if overlay_fn == "outlined" else None
        all_artists = ax.images[1:] + ax.lines[:] + ax.texts[2:]
        overlay_artists = list(all_artists)
        return [im, z_text] + overlay_artists
    anim = animation.FuncAnimation(fig, update, frames=n_z, interval=1000.0 / config['visualisation']['fps'], blit=False)
    if output_path.suffix == ".mp4":
        try:
            writer = animation.FFMpegWriter(fps=config['visualisation']['fps'], metadata={"title": output_path.stem}, bitrate=1800)
            anim.save(str(output_path), writer=writer, dpi=150)
        except Exception as e:
            raise RuntimeError(f"Error writing '{output_path.name}' using FFMpeg: {e}.")
    else:
        try:
            writer = animation.PillowWriter(fps=config['visualisation']['fps'])
            anim.save(str(output_path), writer=writer, dpi=100)
        except Exception as e:
            raise RuntimeError(f"Error writing '{output_path.name}' using Pillow: {e}.")
    plt.close(fig)
    lg.info(f"overlay | Finished rendering overlay movie.")
    print(f"Overlay movie saved to: {output_path}\n")