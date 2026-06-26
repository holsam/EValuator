'''
=======================================
EValuator: PRINT LICENSE
=======================================
'''
# ====================
# Import external dependencies
# ====================
import typer
from rich import print

# ====================
# Import internal dependencies
# ====================
import evaluator.commands.license.license as licenseFuncs

# ====================
# Initialise typer as evaluatorLicense
# ====================
evaluatorLicense = typer.Typer(
    add_completion=False,
    add_help_option=False,
)

# ====================
# Define command: license
# ====================
@evaluatorLicense.command(help='Print EValuator license', rich_help_panel='Utilities')
def license():
    '''
    Print the EValuator license to terminal and exit.
    '''
    licenseFuncs.printLicense()