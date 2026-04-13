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
from typing import Annotated

# ====================
# Import EValuator utilities
# ====================
from evaluator.commands import analyse as analyseFuncs
from evaluator.utils.settings import config, lg

# ====================
# Initialise typer as evaluatorAnalyse
# ====================
evaluatorAnalyse = typer.Typer(
    add_completion=False,
)

@evaluatorAnalyse.command(rich_help_panel="Commands")
def analyse(
    # Define input argument: path to a single labelled MRC or a directory of labelled MRC files
    input: Annotated[
        Path,
        typer.Argument(
            help="Path to either a single labelled MRC file (output of [bold]label[/bold]) or a directory of labelled MRC files.",
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
            help="Path to output directory. Output files will be written under '.../evaluator/results/analyse/'.",
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path("."),
    # Define mindiam option: minimum EV equivalent diameter filter
    mindiam: Annotated[
        float,
        typer.Option("--min-diam", help="Minimum EV equivalent diameter in nm to use for filtering.", min=0)
    ] = config['filter']['min_diameter_nm'],
    # Define maxdiam option: maximum EV equivalent diameter filter
    maxdiam: Annotated[
        float,
        typer.Option("--max-diam", help="Maximum EV equivalent diameter in nm to use for filtering.", min=0)
    ] = config['filter']['max_diameter_nm'],
    # Define fillthreshold option: closure fill threshold for enclosure detection
    fillthreshold: Annotated[
        float,
        typer.Option("--fill-threshold", help="Closure fill threshold to use for determining enclosed EVs.", min=0.0, max=1.0)
    ] = config['filter']['closure_fill_threshold'],
):
    '''
    Run post-processing pipeline on labelled EV segmentation files.
    '''
    analyseFuncs.run_pipeline(input, output, mindiam, maxdiam, fillthreshold)