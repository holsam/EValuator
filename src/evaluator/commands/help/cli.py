'''
=======================================
EValuator: VIEW DOCUMENTATION
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer
from typing import Annotated

# ====================
# Import internal dependencies
# ====================
import evaluator.commands.help.help as helpFuncs

# ====================
# Initialise typer as evaluatorHelp
# ====================
evaluatorHelp = typer.Typer(
    add_completion=False,
    add_help_option=False,
)

# ====================
# Define command: help
# ====================
@evaluatorHelp.command(help='View EValuator documentation', rich_help_panel='Utilities')
def help(
    topic: Annotated[
        str | None,
        typer.Argument(help='Documentation tab to launch into. Defaults to README if excluded.')
    ] = None,
):
    '''
    View EValuator documentation.
    '''
    helpFuncs.showHelp(topic)