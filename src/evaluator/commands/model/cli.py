'''
=======================================
EValuator: EV MODELLING FROM LABELLED SEGMENTATION
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer
from pathlib import Path
from typing import Annotated

# ====================
# Import command functions
# ====================
from evaluator.commands.model import model as modelFuncs

# ====================
# Initialise typer as evaluatorModel
# ====================
evaluatorModel = typer.Typer(
    add_completion=False,
)

# ====================
# Define command: model
# ====================
@evaluatorModel.command(help='Model labelled EVs using a least squares fit approach', rich_help_panel='Component Modelling')
def model(
    # Define segmentation argument: path to a binary segmentation MRC file
    input_file: Annotated[
        Path,
        typer.Argument(
            help='Path to either a single labelled segmentation MRC (i.e. EValuator label output) or a directory of labelled MRC files',
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
            help="Path to output directory (results will be written under '.../evaluator/model/')",
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path('.'),
):
    '''
    Use a least squares fit model to reconstruct EVs from labelled MRC files
    '''
    modelFuncs.model_batch(input_file, output)