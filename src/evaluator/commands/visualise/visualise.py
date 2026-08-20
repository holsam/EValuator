'''
=======================================
EValuator: TOMOGRAM VISUALISER
=======================================
'''
# ====================
# Import external dependencies
# ====================
import matplotlib, numpy
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from functools import partial
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
from rich import print
from skimage import measure
matplotlib.use("Agg")

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import batch as batchutil
from evaluator.utils import config as confutil
from evaluator.utils.settings import lg
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil
from evaluator.commands.visualise.utils import display as displayutil


def generate_movie(input, output, **overrides):
    '''
    Generate a Z-stack movie from an MRC file or directory of MRC files
    '''
    # Load configuration file
    lg.debug(f"visualise movie | Loading configuration file...")
    config, evaluator_dir = confutil.load_config(output)
    # If CLI overrides provided:
    lg.debug(f"visualise movie | Setting run parameters...")
    updates = {k: v for k, v in overrides.items() if v is not None}
    params = config.visualise.model_copy(update=updates)
    # Validate input files
    lg.debug(f"visualise movie | Resolving input MRC file(s)...")
    mrc_files = batchutil.resolve_mrc_inputs(input)
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, "visualise")
    confutil.write_params(params, out_dir)
    worker = partial(_movie_worker, out_dir=out_dir, params=params)
    batchutil.run_batch(mrc_files, worker=worker, desc="MRC files processed")

def _movie_worker(mrc_path: Path, out_dir: Path, params) -> None:
    mrc_data, voxel_size_nm = mrcutil.readMRCFile(mrc_path)
    is_mask = isMask(mrc_data)
    writers = animation.writers.list()
    fmt = "mp4" if "ffmpeg" in writers else "gif"
    out_file_mov = pathutil.checkUniqueFileName(out_dir=out_dir, command="visualise", orig_name=mrc_path.stem, vis_out="Zstack-movie", fmt=fmt)
    createMovie(data=mrc_data, out_path=out_file_mov, fps=params.fps, is_mask=is_mask, voxel_size_nm=voxel_size_nm)
    printVisualiseSummary(mrc_data, is_mask, voxel_size_nm, out_path_mov=out_file_mov, out_path_iso=None)

def generate_isometric_view(input, output, **overrides):
    '''
    Generate an isometric surface render from an MRC file
    '''
    # Load configuration file
    lg.debug(f"visualise isoview | Loading configuration file...")
    config, evaluator_dir = confutil.load_config(output)
    # If CLI overrides provided:
    lg.debug(f"visualise isoview | Setting run parameters...")
    updates = {k: v for k, v in overrides.items() if v is not None}
    params = config.visualise.model_copy(update=updates)
    # Validate input files
    lg.debug(f"visualise isoview | Resolving input MRC file(s)...")
    mrc_files = batchutil.resolve_mrc_inputs(input)
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, "visualise")
    confutil.write_params(params, out_dir)
    worker = partial(_isoview_worker, out_dir=out_dir, params=params)
    batchutil.run_batch(mrc_files, worker=worker, desc="MRC files processed")


def _isoview_worker(mrc_path: Path, out_dir: Path, params) -> None:
    mrc_data, voxel_size_nm = mrcutil.readMRCFile(mrc_path)
    is_mask = isMask(mrc_data)
    out_file_iso = pathutil.checkUniqueFileName(out_dir=out_dir, command="visualise", orig_name=mrc_path.stem, vis_out="isometric-view", fmt="png")
    createIsometricView(data=mrc_data, out_path=out_file_iso, downsample=params.downsample, voxel_size_nm=voxel_size_nm)
    printVisualiseSummary(mrc_data, is_mask, voxel_size_nm, out_path_mov=None, out_path_iso=out_file_iso)

# ====================
# Define subcommand: overlay
# ====================
def overlay(
        tomogram,
        labelled,
        csv,
        output,
        out_format,
        slice,
        export_mp4,
        **overrides,
):
    '''
    Overlay labelled EV components onto a tomogram and save as an image.

    Reads a tomogram MRC and a labelled component MRC (from [bold]label[/bold]),
    filters displayed labels using an [bold]analyse[/bold] CSV, and renders a
    colour-coded overlay. Outputs a tiled Z-slice panel by default, or a single
    slice with [bold]--slice[/bold].
    '''
    # Load configuration file
    lg.debug(f"visualise isoview | Loading configuration file...")
    config, evaluator_dir = confutil.load_config(output)
    # If CLI overrides provided:
    lg.debug(f"visualise isoview | Setting run parameters...")
    updates = {k: v for k, v in overrides.items() if v is not None}
    params = config.visualise.model_copy(update=updates)
    # Validate and read tomogram
    lg.debug(f"overlay | Validating input tomogram file...")
    if not mrcutil.validateMRCFile(tomogram):
        raise ValueError(f"{tomogram.name} is not a valid MRC file and will not be processed.")
    lg.debug(f"overlay | Reading input tomogram file...")
    tomo_data, _ = mrcutil.readMRCFile(tomogram)
    # Validate and read labelled MRC
    lg.debug(f"overlay | Validating labelled component file...")
    if not mrcutil.validateMRCFile(labelled):
        raise ValueError(f"{labelled.name} is not a valid MRC file and will not be processed.")
    lg.debug(f"overlay | Reading labelled component file...")
    seg_data, voxel_size_nm = mrcutil.readMRCFile(labelled)
    seg_labelled = seg_data.astype(numpy.int32)
    # Check shapes match
    lg.debug(f"overlay | Checking tomogram and labelled volume shapes match...")
    if tomo_data.shape != seg_labelled.shape:
        raise ValueError(f"Tomogram shape {tomo_data.shape} and labelled volume shape {seg_labelled.shape} do not match.")
    # Get valid labels from CSV
    lg.debug(f"overlay | Reading CSV file...")
    valid_labels = displayutil.getValidLabelsFromCSV(csv, labelled.name)
    if not valid_labels:
        raise ValueError(f"No valid EV components identified in {csv.name}.")
    n_components = int(seg_labelled.max())
    lg.info(f"overlay | {n_components} total components in labelled volume. {len(valid_labels)} EV components will be overlaid using style: '{params.overlay_style}'.")
    # Assign colours
    lg.debug(f"overlay | Assigning label colours...")
    label_colours = displayutil.assignLabelColours(valid_labels, params)
    # Create output directory and file path
    lg.debug(f"overlay | Creating output directory structure...")
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, "visualise")
    confutil.write_params(params, out_dir)
    lg.debug(f"overlay | Defining output file...")
    out_file = pathutil.checkUniqueFileName(out_dir=out_dir, command="overlay", orig_name=tomogram.stem, overlay_style=params.overlay_style, fmt=out_format)

    # Render static image
    if slice is not None:
        lg.debug(f"overlay | Rendering single-slice image...")
        displayutil.renderSingleSlice(tomo_data, seg_labelled, valid_labels, label_colours, slice, params.overlay_style, out_file, labelled.name, params)
    else:
        lg.debug(f"overlay | Rendering tiled image...")
        displayutil.renderTiled(tomo_data, seg_labelled, valid_labels, label_colours, params.n_slices, params.overlay_style, out_file, labelled.name, params)

    # Optionally render movie
    if export_mp4:
        writers = animation.writers.list()
        fmt = "mp4" if "ffmpeg" in writers else "gif"
        lg.debug(f"overlay | Defining output file for overlay movie...")
        out_file_mov = pathutil.checkUniqueFileName(out_dir=out_dir, command="overlay", orig_name=tomogram.stem, overlay_style=params.overlay_style, fmt=fmt)
        lg.debug(f"overlay | Rendering overlay movie...")
        displayutil.renderOverlayMovie(tomo_data, seg_labelled, valid_labels, label_colours, params.overlay_style, out_file_mov, labelled.name, params)

# =========================
# DEFINE FUNCTION: isMask
# =========================
def isMask(data: numpy.ndarray) -> bool:
    '''
    Heuristically determine whether an MRC volume is a binary segmentation mask.
    A volume is treated as a mask if it contains only two unique values.
    '''
    return len(numpy.unique(data)) <= 2

# =========================
# DEFINE FUNCTION: saveGif
# =========================
def saveGif(anim, out_path: Path, fps: float):
    '''
    Save a matplotlib animation as a GIF using Pillow.
    '''
    try:
        writer = animation.PillowWriter(fps=fps)
        anim.save(str(out_path), writer=writer, dpi=100)
    except Exception as e:
        raise RuntimeError(f"Error writing '{out_path.name}' using Pillow: {e}.")

# =========================
# DEFINE FUNCTION: createMovie
# =========================
def createMovie(data: numpy.ndarray, out_path: Path, fps: float, is_mask: bool, voxel_size_nm):
    '''
    Generate a Z-stack movie where each frame is one XY slice.
    Saved as MP4 if FFMpeg is available, otherwise falls back to GIF.
    '''
    n_z = data.shape[0]
    scale_label = "nm" if voxel_size_nm is not None else "vox"
    if is_mask:
        display = data.astype(numpy.float32)
        cmap = "binary_r"
        vmin, vmax = 0.0, 1.0
    else:
        display = displayutil.normaliseArray(data)
        cmap = "gray"
        vmin, vmax = 0.0, 1.0
    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.axis("off")
    im = ax.imshow(display[0], cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest", origin="upper")
    z_label_val = (0 * voxel_size_nm) if voxel_size_nm is not None else 0
    title = ax.set_title(f"Z = {z_label_val:.1f} {scale_label}  (slice 1 / {n_z})", color="white", fontsize=9, pad=4)
    def update(frame_idx):
        im.set_data(display[frame_idx])
        z_val = (frame_idx * voxel_size_nm) if voxel_size_nm is not None else frame_idx
        title.set_text(f"Z = {z_val:.1f} {scale_label}  (slice {frame_idx + 1} / {n_z})")
        return im, title
    anim = animation.FuncAnimation(fig, update, frames=n_z, interval=1000.0 / fps, blit=True)
    if out_path.suffix == ".mp4":
        try:
            writer = animation.FFMpegWriter(fps=fps, metadata={"title": out_path.stem}, bitrate=1800)
            anim.save(str(out_path), writer=writer, dpi=150)
        except Exception as e:
            raise RuntimeError(f"Error writing '{out_path.name}' using FFMpeg: {e}.")
    else:
        saveGif(anim, out_path, fps)
    plt.close(fig)

# =========================
# DEFINE FUNCTION: createIsometricView
# =========================
def createIsometricView(data: numpy.ndarray, out_path: Path, downsample: int, voxel_size_nm):
    '''
    Render an isometric 3D surface view of a binary segmentation mask using marching cubes.
    '''
    vol = data.astype(numpy.uint8)
    if downsample > 1:
        vol = vol[::downsample, ::downsample, ::downsample]
    if vol.sum() == 0:
        lg.warning("visualise | Segmentation mask is entirely zero after downsampling — skipping isometric render.")
        return
    spacing = (voxel_size_nm * downsample,) * 3 if voxel_size_nm is not None else (float(downsample),) * 3
    axis_unit = "nm" if voxel_size_nm is not None else "vox"
    try:
        verts, faces, _, _ = measure.marching_cubes(vol, level=0.5, spacing=spacing)
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"visualise | Marching cubes failed during isometric view generation: {e}")
    mesh = Poly3DCollection(verts[faces], alpha=0.75, linewidths=0)
    mesh.set_facecolor([0.3, 0.7, 1.0])
    mesh.set_edgecolor("none")
    fig = plt.figure(figsize=(7, 7))
    fig.patch.set_facecolor("black")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("black")
    ax.add_collection3d(mesh)
    for dim, (getter, setter) in enumerate(zip([verts[:, 0], verts[:, 1], verts[:, 2]], [ax.set_xlim, ax.set_ylim, ax.set_zlim])):
        pad = (getter.max() - getter.min()) * 0.05
        setter(getter.min() - pad, getter.max() + pad)
    ax.set_xlabel(f"X ({axis_unit})", color="white", labelpad=6)
    ax.set_ylabel(f"Y ({axis_unit})", color="white", labelpad=6)
    ax.set_zlabel(f"Z ({axis_unit})", color="white", labelpad=6)
    ax.tick_params(colors="white")
    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor("none")
    ax.view_init(elev=35.264, azim=45)
    ax.set_title("Isometric mask render", color="white", pad=10)
    fig.savefig(str(out_path), dpi=200, bbox_inches="tight", facecolor="black")
    plt.close(fig)

# =========================
# DEFINE FUNCTION: printVisualiseSummary
# =========================
def printVisualiseSummary(data: numpy.ndarray, is_mask: bool, voxel_size_nm, out_path_mov, out_path_iso):
    print(f"\n[bold]EValuator visualise summary[/bold]")
    print(f"- Volume shape (Z, Y, X): {data.shape}")
    print(f"- Volume type: {'segmentation mask' if is_mask else 'greyscale tomogram'}")
    if voxel_size_nm:
        print(f"- Voxel size: {voxel_size_nm:.4f} nm")
    else:
        print(f"- Voxel size not found in MRC header. Units will be in voxels.")
    if out_path_mov:
        print(f"- Z-stack movie saved as: {out_path_mov.name}")
    if out_path_iso:
        print(f"- Isometric view saved as: {out_path_iso.name}")
    if not out_path_mov and not out_path_iso:
        print(f"No results to save.\n")
    else:
        if out_path_mov:
            print(f"Result(s) saved to: {out_path_mov.parent}\n")
        elif out_path_iso:
            print(f"Result(s) saved to: {out_path_iso.parent}\n")