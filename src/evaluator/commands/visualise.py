'''
=======================================
EValuator: TOMOGRAM VISUALISER
=======================================
'''
# ====================
# Import external dependencies
# ====================
import matplotlib, numpy, pandas, typer
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
from rich import print
from scipy import ndimage
from skimage import measure
from typing import Annotated
matplotlib.use("Agg")

# ====================
# Import EValuator functions and variables
# ====================
from ..main import config, lg
from .. import utils as evalutil

# ====================
# Initialise typer as evaluatorVisualise
# ====================
evaluatorVisualise = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False
)

# ====================
# Define command: visualise
# ====================
# TODO: add logging
@evaluatorVisualise.command(rich_help_panel="Commands")
def visualise(
    # --------------------
    # Define CLI arguments
    # --------------------
    # Define input argument: should be a path which exists and is readable, and can be a file or directory 
    input: Annotated[
        Path, 
        typer.Argument(help="Path to either a single .MRC segmentation file or a directory containing multiple .MRC segmentation files.", exists=True,file_okay=True,dir_okay=True,readable=True)
    ],
    # --------------------
    # Define CLI options
    # --------------------
    # Define output option: should be a path which can not exist or is a writeable directory if it exists, and defaults to current working directory
    output: Annotated[
        Path | None, 
        typer.Option("-o", "--out-dir", help="Path to output directory. Output files will be written to this directory under '.../evaluator/results/analyse/'.", file_okay=False,dir_okay=True,writable=True)
        ] = Path("."),
    # Define fps argument: should be an integer greater than 0, and defaults to 'fps' value specified in config.toml
    fps: Annotated[
        int, 
        typer.Option("--fps", help="Frame rate for Z-stack movie.", min=0)
    ] = config['visualisation']['fps'],
    # Define downsample argument: should be an integer greater than 1, and defaults to 'downsample' value specified in config.toml
    downsample: Annotated[
        int,
        typer.Option("--downsample", help="Downsampling factor for isometric render.", min=1)
    ] = config['visualisation']['downsample'],
    no_movie: Annotated[
        bool, 
        typer.Option("--no-movie", help="Skip Z-stack movie generation.")
    ] = False,
    no_iso: Annotated[
        bool,
        typer.Option("--no-iso", help="Skip isometric view generation (only applies if input file is a segmentation mask).")
    ] = False
):
    # Set help text for 'visualise' command using docstring
    '''
    Generate visualisations of tomography data.
    '''
    # Check input MRC file is valid
    lg.debug(f"visualise | Validating input MRC file...")
    if not evalutil.validateMRCFile(input):
        # Raise error if not
        raise ValueError(f"{input.name} is not a valid MRC file and will not be processed.")
    else:
        # Otherwise read file
        lg.debug(f"label | Reading input MRC file...")
        mrc_data, voxel_size_nm = evalutil.readMRCFile(input)
    # Create output directory structure
    lg.debug(f"visualise | Creating output directory structure...")
    out_dir = evalutil.generateOutputFileStructure(output, "visualise")
    is_mask = isMask(mrc_data)
    # If --no-movie option wasn't supplied
    if not no_movie:
        # Check if ffmpeg is available to use for writing mp4 files
        writers = animation.writers.list()
        if "ffmpeg" in writers:
            # Define movie output file path using mp4
            lg.debug(f"visualise | Defining output file for Z-stack movie...")
            out_file_mov = evalutil.checkUniqueFileName(out_dir=out_dir, command="visualise", orig_name=input.stem, vis_out = "Zstack-movie", fmt="mp4")
        else:
            # Define movie output file path using gif
            lg.debug(f"visualise | Defining output file for Z-stack movie...")
            out_file_mov = evalutil.checkUniqueFileName(out_dir=out_dir, command="visualise", orig_name=input.stem, vis_out = "Zstack-movie", fmt="gif")
        createMovie(data=mrc_data, out_path=out_file_mov, fps=fps, is_mask=is_mask, voxel_size_nm=voxel_size_nm)
    else:
        lg.info(f"visualise | --no-movie option supplied - skipping Z-stack movie generation.")
        out_file_mov = None

    if not is_mask:
        lg.info(f"visualise | Input MRC file is not a mask - skipping isometric view generation.")
        out_file_iso = None
    else:
        # If --no-iso option wasn't supplied
        if not no_iso:
            # Define isometric view output file path
            lg.debug(f"visualise | Defining output file for isometric view...")
            out_file_iso = evalutil.checkUniqueFileName(out_dir=out_dir, command="visualise", orig_name=input.stem, vis_out = "isometric-view")
            createIsometricView(data=mrc_data, out_path=out_file_iso, downsample=downsample, voxel_size_nm=voxel_size_nm)
        else:
            lg.info(f"visualise | --no-iso option supplied - skipping isometric view generation.")
            out_file_iso = None
    # Print summary message
    printSummaryMessage(mrc_data, is_mask, voxel_size_nm, out_file_mov, out_file_iso)

# =========================
# DEFINE FUNCTION: isMask
# =========================
def isMask(data: numpy.ndarray) -> bool:
    '''
    Heuristically determine whether the data is a binary segmentation mask.
    A volume is treated as a mask if it contains only two unique values (e.g. 0 and 1).
    '''
    is_mask = len(numpy.unique(data)) <= 2
    return is_mask

# =========================
# DEFINE FUNCTION: saveGif
# =========================
def saveGif(anim, out_path: Path, fps: float):
    '''
    Save an animation as a GIF using Pillow.
    '''
    try:
        writer = animation.PillowWriter(fps=fps)
        anim.save(str(out_path), writer=writer, dpi=100)
    except Exception as e:
        raise RuntimeError(f"Error writing '{out_path.name}' using Pillow: {e}.")


# =========================
# DEFINE FUNCTION: createMovie
# =========================
# TODO: add logging
def createMovie(data: numpy.ndarray, out_path: Path, fps: float, is_mask: bool, voxel_size_nm):
    '''
    Generate a Z-stack movie where each frame is one XY slice, with Z advancing as time. Saved as MP4 if FFMpeg is available, otherwise falls back to GIF.
    '''
    n_z = data.shape[0]
    scale_label = "nm" if voxel_size_nm is not None else "vox"
    # Check if file is a mask
    if is_mask:
        display = data.astype(numpy.float32)
        cmap = "binary_r"
        vmin, vmax = 0.0, 1.0
    else:
        display = evalutil.normaliseArray(data)
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
    anim = animation.FuncAnimation(fig, update, frames=n_z, interval=1000.0/fps, blit=True)
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
# DEFINE FUNCTION: rotateIsometric
# =========================
def rotateIsometric(vol: numpy.ndarray) -> numpy.ndarray:
    '''
    Rotate a 3D volume to produce an isometric viewing angle. Applies a 45° azimuthal rotation (around Z) followed by a 35.264° elevation
    tilt (around the new Y axis) — the standard isometric projection angles. Uses linear interpolation (order=1) for speed; mask volumes should be pre-cast to float before calling this and thresholded afterwards if needed.
    '''
    # Rotate 45° in the YX plane (around Z axis)
    vol = ndimage.rotate(vol, 45.0, axes=(1, 2), reshape=True, order=1, cval=0.0)
    # Tilt by arctan(1/sqrt(2)) ≈ 35.264° in the ZX plane (around Y axis)
    vol = ndimage.rotate(vol, 35.264, axes=(0, 2), reshape=True, order=1, cval=0.0)
    return vol

# =========================
# DEFINE FUNCTION: createIsometricView
# =========================
# TODO: add logging
def createIsometricView(data: numpy.ndarray, out_path: Path, downsample: int, voxel_size_nm):
    '''
    For a binary segmentation mask, render an isometric 3D surface view using marching cubes. Voxels with value 0 are fully invisible; only the membrane surface is shown. The view is set to the standard isometric camera angle.
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
    mesh.set_facecolor([0.3, 0.7, 1.0])  # light blue membrane colour
    mesh.set_edgecolor("none")
    fig = plt.figure(figsize=(7, 7))
    fig.patch.set_facecolor("black")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("black")
    ax.add_collection3d(mesh)
    # Axis limits from vertex extents
    for dim, (getter, setter) in enumerate(zip([verts[:, 0], verts[:, 1], verts[:, 2]],[ax.set_xlim, ax.set_ylim, ax.set_zlim])):
        pad = (getter.max() - getter.min()) * 0.05
        setter(getter.min() - pad, getter.max() + pad)
    ax.set_xlabel(f"X ({axis_unit})", color="white", labelpad=6)
    ax.set_ylabel(f"Y ({axis_unit})", color="white", labelpad=6)
    ax.set_zlabel(f"Z ({axis_unit})", color="white", labelpad=6)
    ax.tick_params(colors="white")
    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor("none")
    # Isometric camera angle
    ax.view_init(elev=35.264, azim=45)
    ax.set_title("Isometric mask render", color="white", pad=10)
    fig.savefig(str(out_path), dpi=200, bbox_inches="tight", facecolor="black")
    plt.close(fig)

# =========================
# DEFINE FUNCTION: printSummaryMessage
# =========================
def printSummaryMessage(data: numpy.ndarray, is_mask: bool, voxel_size_nm, out_path_mov, out_path_iso):
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
        print(f"- Isometric view image saved as: {out_path_iso.name}")
    if not out_path_mov and out_path_iso:
        print(f"No results to save.\n")
    else:
        if out_path_mov: 
            print(f"Result(s) saved to: {out_path_mov.parent}\n")
        elif out_path_iso:
            print(f"Result(s) saved to: {out_path_iso.parent}\n")