'''
=======================================
EValuator: TOMOGRAM VISUALISER
=======================================
'''
# ====================
# Import external dependencies
# ====================
import matplotlib, typer
from pathlib import Path
from typing import Annotated, Literal, Optional
matplotlib.use("Agg")

# ====================
# Import EValuator utilities
# ====================
from evaluator.commands.visualise import visualise as visualiseFuncs

# ====================
# Initialise typer as evaluatorVisualise
# ====================
evaluatorVisualise = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Define subcommand: isoview
# ====================
@evaluatorVisualise.command(name="isoview", rich_help_panel="Visualise Commands")
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
    # Define downsample option: downsampling factor for isometric render
    downsample: Annotated[
        Optional[int],
        typer.Option("--downsample", help="Downsampling factor for isometric render.", min=1)
    ] = None,
    jobs: Annotated[
        Optional[int],
        typer.Option('-j', '--jobs', help='Maximum parallel worker processes (default: CPU count)', min=1, rich_help_panel='Batch Options')
    ] = None,
):
    '''
    Generate an isometric surface render from an MRC file
    '''
    visualiseFuncs.generate_isometric_view(input, output, downsample=downsample, max_workers=jobs)

# ====================
# Define subcommand: movie
# ====================
@evaluatorVisualise.command(rich_help_panel="Visualise Commands")
def movie(
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
        Optional[int],
        typer.Option("--fps", help="Frame rate for Z-stack movie.", min=0)
    ] = None,
    jobs: Annotated[
        Optional[int],
        typer.Option('-j', '--jobs', help='Maximum parallel worker processes (default: CPU count)', min=1, rich_help_panel='Batch Options')
    ] = None,
):
    '''
    Generate a Z-stack movie from an MRC file
    '''
    visualiseFuncs.generate_movie(input, output, fps=fps, max_workers=jobs)



@evaluatorVisualise.command(name="overlay", rich_help_panel="Visualise Commands")
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
    # Define slice option: render a single Z-slice instead of a tiled panel
    slice: Annotated[
        Optional[int],
        typer.Option("--slice", help="Render a single Z-slice at this index instead of a tiled panel.", min=0)
    ] = None,
    # Define export_mp4 option: export a Z-stack overlay movie
    export_mp4: Annotated[
        bool,
        typer.Option("--export-mp4", help="Export a Z-stack MP4 (or GIF fallback) overlay movie alongside the static image.")
    ] = False,
    # CLI overrides
    # Define style option: overlay rendering style
    overlay_style: Annotated[
        Optional[Literal["both", "filled", "outlined"]],
        typer.Option("-s", "--style", help="Overlay style for labelled output image.")
    ] = None,
    # Define n_slices option: number of tiles in the panel
    n_slices: Annotated[
        Optional[int],
        typer.Option("--n-slices", help="Number of evenly-spaced slices in the tiled panel.", min=0)
    ] = None,
):
    '''
    Overlay labelled EV components onto a tomogram and save as an image
    '''
    visualiseFuncs.overlay(tomogram, labelled, csv, output, out_format, slice, export_mp4, overlay_style=overlay_style, n_slices=n_slices)