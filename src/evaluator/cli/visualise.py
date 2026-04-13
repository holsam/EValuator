'''
=======================================
EValuator: TOMOGRAM VISUALISER
=======================================
'''
# ====================
# Import external dependencies
# ====================
import matplotlib, numpy, typer
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
from rich import print
from scipy import ndimage
from skimage import measure
from typing import Annotated, Literal
matplotlib.use("Agg")

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import config, lg
from evaluator.utils import mrc as mrcutil
from evaluator.utils import paths as pathutil
from evaluator.utils import display as displayutil
from evaluator.commands import visualise as visualiseFuncs

# ====================
# Initialise typer as evaluatorVisualise
# ====================
evaluatorVisualise = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Define subcommand: visualise
# ====================
@evaluatorVisualise.command(name="view", rich_help_panel="Commands")
def visualise(
    # Define input argument: single MRC file or directory of MRC files
    input: Annotated[
        Path,
        typer.Argument(
            help="Path to either a single MRC file or a directory containing multiple MRC files.",
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
        )
    ],
    # Define output option: output directory, defaults to current working directory
    output: Annotated[
        Path | None,
        typer.Option(
            "-o", "--out-dir",
            help="Path to output directory. Output files will be written under '.../evaluator/results/visualise/'.",
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path("."),
    # Define fps option: frame rate for Z-stack movie
    fps: Annotated[
        int,
        typer.Option("--fps", help="Frame rate for Z-stack movie.", min=0)
    ] = config['visualisation']['fps'],
    # Define downsample option: downsampling factor for isometric render
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
        typer.Option("--no-iso", help="Skip isometric view generation (only applies if input is a segmentation mask).")
    ] = False,
):
    '''
    Generate a Z-stack movie and/or isometric surface render from an MRC file.
    '''
    visualiseFuncs.visualise()

@evaluatorVisualise.command(name="overlay", rich_help_panel="Commands")
def overlay(
    # Define tomogram argument: unsegmented tomogram MRC
    tomogram: Annotated[
        Path,
        typer.Argument(
            help="Path to unsegmented tomogram MRC.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        )
    ],
    # Define labelled argument: labelled component MRC (output of `label`)
    labelled: Annotated[
        Path,
        typer.Argument(
            help="Path to labelled component MRC (output of [bold]label[/bold]).",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        )
    ],
    # Define csv option: EValuator analyse CSV to filter displayed labels
    csv: Annotated[
        Path,
        typer.Option(
            "-c", "--csv",
            help="Path to EValuator analyse output CSV. Only labels present in this CSV will be overlaid.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        )
    ],
    # Define output option: output directory, defaults to current working directory
    output: Annotated[
        Path | None,
        typer.Option(
            "-o", "--out-dir",
            help="Path to output directory. Output files will be written under '.../evaluator/results/visualise/'.",
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path("."),
    # Define out_format option: image file format
    out_format: Annotated[
        Literal["png", "jpg", "tiff"],
        typer.Option("-f", "--out-format", help="File format for output image.")
    ] = "png",
    # Define style option: overlay rendering style
    style: Annotated[
        Literal["both", "filled", "outlined"],
        typer.Option("-s", "--style", help="Overlay style for labelled output image.")
    ] = "both",
    # Define slice option: render a single Z-slice instead of a tiled panel
    slice: Annotated[
        int | None,
        typer.Option("--slice", help="Render a single Z-slice at this index instead of a tiled panel.", min=0)
    ] = None,
    # Define n_slices option: number of tiles in the panel
    n_slices: Annotated[
        int,
        typer.Option("--n-slices", help="Number of evenly-spaced slices in the tiled panel.", min=0)
    ] = config['label']['n_slices'],
    # Define export_mp4 option: export a Z-stack overlay movie
    export_mp4: Annotated[
        bool,
        typer.Option("--export-mp4", help="Export a Z-stack MP4 (or GIF fallback) overlay movie alongside the static image.")
    ] = False,
):
    '''
    Overlay labelled EV components onto a tomogram and save as an image.
    '''
    visualiseFuncs.overlay(tomogram, labelled, csv, output, out_format, style, slice, n_slices, export_mp4)