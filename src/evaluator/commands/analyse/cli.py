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
    fill_threshold: Annotated[
        Optional[float],
        typer.Option('--fill-threshold', help='Override configuration fill threshold parameter for this run', min=0, max=1)
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
        output,,
        fill_threshold=fill_threshold,
        max_workers=jobs,
    )