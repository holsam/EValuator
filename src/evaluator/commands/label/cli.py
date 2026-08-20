'''
=======================================
EValuator: SEGMENTATION EV LABELLING
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
from evaluator.commands.label import label as labelFuncs

# ====================
# Initialise typer as evaluatorLabel
# ====================
evaluatorLabel = typer.Typer(
    add_completion=False,
)

# ====================
# Define command: label
# ====================
@evaluatorLabel.command(help='Label connected components in a segmentation MRC',rich_help_panel='Component Identification')
def label(
    # Define segmentation argument: path to a binary segmentation MRC file
    segmentation: Annotated[
        Path,
        typer.Argument(
            help='Path to either a single binary segmentation MRC (e.g. MemBrain-seg output) or a directory of segmentation MRC files',
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
        )
    ],
    # Define output option: output directory, defaults to current working directory
    output: Annotated[
        Optional[Path],
        typer.Option(
            '-o', '--out-dir',
            help='Path to output directory, outputs will be written under ".../evaluator/label/"',
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path('.'),
):
    '''
    Label connected components in a binary segmentation MRC and write a labelled MRC
    '''
    labelFuncs.label_batch(
        segmentation,
        output,
    )