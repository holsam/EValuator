'''
CLI command: config
'''

# ====================
# Import external dependencies
# ====================
import typer
from pathlib import Path
from typing import Annotated

# ====================
# Import internal command utilities
# ====================
from evaluator.commands.config import config as configFuncs

# ====================
# Initialise Typer class for config command
# ====================
evaluatorConfig = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False,
)

# ====================
# Define config command
# ====================
@evaluatorConfig.command()
def config(
    path: Annotated[
        Path,
        typer.Argument(help='Path to directory or configuration file path')
    ],
    stepwise: Annotated[
        bool,
        typer.Option('-s', '--stepwise', is_flag=True, help='Edit values through stepwise terminal prompting instead of in editor')
    ],
):
    '''Create or edit an EValuator configuration file'''
    configFuncs.run_config(path, stepwise=stepwise)
