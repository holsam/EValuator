'''
=======================================
EValuator: SEGMENTATION ANALYSIS PIPELINE
=======================================
'''
# ====================
# Import external dependencies
# ====================
import typer
from pathlib import Path
from typing import Annotated, Optional

# ====================
# Import EValuator utilities
# ====================
from evaluator.commands.analyse import analyse as analyseFuncs

# ====================
# Initialise typer as evaluatorAnalyse
# ====================
evaluatorAnalyse = typer.Typer(
    add_completion=False,
)

@evaluatorAnalyse.command(help='Run morphological analysis pipeline on labelled MRC files', rich_help_panel='Component Analysis')
def analyse(
    # Define input argument: path to a single labelled MRC or a directory of labelled MRC files
    input: Annotated[
        Path,
        typer.Argument(
            help="Path to either a single labelled MRC file (output of [bold]label[/bold]) or a directory of labelled MRC files",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        )
    ],
    # Define output option: output directory, defaults to current working directory
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o", "--out-dir",
            help='Path to output directory, outputs will be written under ".../evaluator/analyse/"',
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path("."),
    # Define optional configuration overrides
    minimum_diameter_nm: Annotated[
        Optional[float],
        typer.Option('--min-diameter', help='Override configuration minimum diameter parameter for this run')
    ] = None,
    maximum_diameter_nm: Annotated[
        Optional[float],
        typer.Option('--max-diameter', help='Override configuration maximum diameter parameter for this run')
    ] = None,
    fill_threshold: Annotated[
        Optional[float],
        typer.Option('--fill-threshold', help='Override configuration fill threshold parameter for this run')
    ] = None,
    membrane_thickness_nm: Annotated[
        Optional[float],
        typer.Option('--membrane-thickness', help='Override configuration membrane thickness parameter for this run')
    ] = None,
    jobs: Annotated[
        Optional[int],
        typer.Option('-j', '--jobs', help='Maximum parallel worker processes (default: CPU count)', min=1, rich_help_panel='Batch Options')
    ] = None,
):
    '''
    Run post-processing pipeline on labelled EV segmentation files.
    '''
    analyseFuncs.analyse(
        input,
        output,
        minimum_diameter_nm=minimum_diameter_nm,
        maximum_diameter_nm=maximum_diameter_nm,
        fill_threshold=fill_threshold,
        membrane_thickness_nm=membrane_thickness_nm,
        max_workers=jobs,
    )